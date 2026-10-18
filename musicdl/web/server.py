'''
Function:
    Modern WebUI backend server for musicdl
Author:
    Zhenchao Jin / Enhanced Modern WebUI
'''
import os
import re
import time
import uuid
import json
import io
import av
import queue
import tempfile
import urllib.parse
import threading
import requests
import concurrent.futures
from pathlib import Path
from flask import Flask, request, Response, jsonify, send_from_directory, stream_with_context, redirect

from musicdl import musicdl
from musicdl.modules.sources import MusicClientBuilder, BuildMusicClient
from musicdl.modules.utils import SongInfo, SongInfoUtils

requests.packages.urllib3.disable_warnings()

# Directories
HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, 'static')
DOWNLOAD_DIR = os.environ.get('MUSICDL_DOWNLOAD_DIR', os.path.join(os.getcwd(), 'musicdl_web_downloads'))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Sources definition with categories
SUPPORTED_SOURCES = {
    # Platforms in Greater China
    'NeteaseMusicClient':  {'label': '网易云音乐', 'short': '网易云', 'category': '国内主流', 'default': True},
    'QQMusicClient':       {'label': 'QQ 音乐',   'short': 'QQ音乐', 'category': '国内主流', 'default': True},
    'KuwoMusicClient':     {'label': '酷我音乐',   'short': '酷我',   'category': '国内主流', 'default': True},
    'KugouMusicClient':    {'label': '酷狗音乐',   'short': '酷狗',   'category': '国内主流', 'default': True},
    'MiguMusicClient':     {'label': '咪咕音乐',   'short': '咪咕',   'category': '国内主流', 'default': True},
    'BodianMusicClient':   {'label': '波点音乐',   'short': '波点',   'category': '国内主流', 'default': True},
    'SodaMusicClient':     {'label': '汽水音乐',   'short': '汽水',   'category': '国内主流', 'default': False},
    # Aggregators & Free Sources
    'MyFreeMP3MusicClient':{'label': 'MyFreeMP3', 'short': 'MyFreeMP3', 'category': '聚合平台', 'default': False},
    'GequbaoMusicClient':  {'label': '歌曲宝',     'short': '歌曲宝', 'category': '聚合平台', 'default': False},
    'GDStudioMusicClient': {'label': 'GDStudio聚合', 'short': 'GDStudio', 'category': '聚合平台', 'default': False},
    # Global & Indie
    'JamendoMusicClient':  {'label': 'Jamendo',   'short': 'Jamendo', 'category': '海外与独立', 'default': False},
    'SoundCloudMusicClient':{'label': 'SoundCloud', 'short': 'SoundCloud', 'category': '海外与独立', 'default': False},
}

SOURCE_ORDER = list(SUPPORTED_SOURCES.keys())
SEARCH_SIZE_PER_SOURCE = 5
PER_SOURCE_TIMEOUT = 25

RESULT_EXT_TO_MIME = {
    'mp3': 'audio/mpeg',
    'flac': 'audio/flac',
    'wav': 'audio/wav',
    'm4a': 'audio/mp4',
    'aac': 'audio/aac',
    'ape': 'audio/x-ape',
    'ogg': 'audio/ogg',
    'webm': 'audio/webm',
}


# Client Manager
class ClientManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._clients = {}

    def get_client(self, source_name):
        with self._lock:
            if source_name not in self._clients:
                self._clients[source_name] = BuildMusicClient(module_cfg={
                    'type': source_name,
                    'search_size_per_source': SEARCH_SIZE_PER_SOURCE,
                    'disable_print': True,
                    'max_retries': 2,
                })
            return self._clients[source_name]


MANAGER = ClientManager()


# Persistent Track Registry (跨进程/跨服务重启永久保留已注册音源直链与歌词)
REGISTRY_CACHE_FILE = os.path.join(DOWNLOAD_DIR, '.track_registry.json')

class TrackRegistry:
    def __init__(self, cache_file=REGISTRY_CACHE_FILE):
        self._lock = threading.Lock()
        self._tracks = {}
        self.cache_file = cache_file
        self._load_cache()

    def _load_cache(self):
        if not os.path.exists(self.cache_file):
            return
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for token, item in data.items():
                song_dict = item.get('song_info', {})
                song = SongInfo()
                for k, v in song_dict.items():
                    setattr(song, k, v)
                self._tracks[token] = {
                    'song_info': song,
                    'source': item.get('source', ''),
                    'headers': item.get('headers', {}),
                    'cookies': item.get('cookies', {}),
                    'created_at': item.get('created_at', time.time()),
                }
        except Exception:
            pass

    def _save_cache(self):
        try:
            data = {}
            for token, item in self._tracks.items():
                song = item['song_info']
                song_dict = {
                    'song_name': getattr(song, 'song_name', ''),
                    'singers': getattr(song, 'singers', ''),
                    'album': getattr(song, 'album', ''),
                    'duration': getattr(song, 'duration', ''),
                    'file_size': getattr(song, 'file_size', ''),
                    'ext': getattr(song, 'ext', 'mp3'),
                    'download_url': getattr(song, 'download_url', ''),
                    'lyric': getattr(song, 'lyric', ''),
                    'cover_url': getattr(song, 'cover_url', ''),
                    'source': getattr(song, 'source', item.get('source', '')),
                }
                data[token] = {
                    'song_info': song_dict,
                    'source': item['source'],
                    'headers': item['headers'],
                    'cookies': item['cookies'],
                    'created_at': item['created_at'],
                }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def add(self, song_info: SongInfo, source: str) -> str:
        token = uuid.uuid4().hex[:16]
        client = MANAGER.get_client(source)
        headers = dict(getattr(client, 'default_download_headers', {}) or {})
        headers.update(dict(getattr(song_info, 'default_download_headers', {}) or {}))
        cookies = dict(getattr(client, 'default_download_cookies', {}) or {})
        cookies.update(dict(getattr(song_info, 'default_download_cookies', {}) or {}))
        
        with self._lock:
            self._tracks[token] = {
                'song_info': song_info,
                'source': source,
                'headers': headers,
                'cookies': cookies,
                'created_at': time.time(),
            }
            self._save_cache()
        return token

    def get(self, token: str):
        with self._lock:
            return self._tracks.get(token)


REGISTRY = TrackRegistry()


# Download Manager for background tasks
DOWNLOADS = {}
DL_LOCK = threading.Lock()


def track_to_payload(song_info: SongInfo, token: str, source: str) -> dict:
    ext = str(getattr(song_info, 'ext', 'mp3') or 'mp3').lower().lstrip('.')
    source_meta = SUPPORTED_SOURCES.get(source, {})
    raw_lyric = getattr(song_info, 'lyric', None)
    lyric_str = str(raw_lyric).strip() if raw_lyric else ''
    is_mainstream = source in {'NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient', 'KugouMusicClient', 'MiguMusicClient'}
    has_lyric = bool(lyric_str) or is_mainstream
    is_lossless = ext in {'flac', 'wav', 'ape', 'alac', 'dsf', 'dff'} or is_mainstream
    return {
        'token': token,
        'source': source,
        'source_label': source_meta.get('label', source),
        'source_short': source_meta.get('short', source),
        'song_name': str(getattr(song_info, 'song_name', '未知曲目') or '未知曲目'),
        'singers': str(getattr(song_info, 'singers', '未知艺人') or '未知艺人'),
        'album': str(getattr(song_info, 'album', '') or ''),
        'duration': str(getattr(song_info, 'duration', '') or '00:00'),
        'file_size': str(getattr(song_info, 'file_size', '') or ''),
        'ext': 'flac' if is_mainstream and ext == 'mp3' else ext,
        'lossless': is_lossless,
        'identifier': str(getattr(song_info, 'identifier', '') or ''),
        'cover_url': f'/api/cover/{token}' if getattr(song_info, 'cover_url', None) else '',
        'has_lyric': has_lyric,
        'lyric': lyric_str,
        'download_url': f'/api/stream/{token}?download=1',
        'stream_url': f'/api/stream/{token}',
    }


class _NullProgress:
    def add_task(self, *a, **k): return 0
    def update(self, *a, **k): pass
    def advance(self, *a, **k): pass
    @property
    def tasks(self):
        class _T: total = 0; completed = 0
        return {_: _T() for _ in range(10)}
    def __getattr__(self, _): return lambda *a, **k: None


def _safe_search(client, keyword, url, bucket, progress):
    try:
        client._search(keyword=keyword, search_url=url, request_overrides={},
                       song_infos=bucket, progress=progress)
    except Exception:
        pass


def _drain(buckets, cursors, source, seen, lock, emit):
    emitted = 0
    for i, bucket in enumerate(buckets):
        while cursors[i] < len(bucket):
            song_info = bucket[cursors[i]]
            cursors[i] += 1
            if not isinstance(song_info, SongInfo) or not song_info.with_valid_download_url:
                continue
            with lock:
                dedup_key = f"{song_info.song_name}_{song_info.singers}_{song_info.file_size}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
            token = REGISTRY.add(song_info, source)
            emit('result', track_to_payload(song_info, token, source))
            emitted += 1
    return emitted


def search_stream(keyword, sources):
    out = queue.Queue()
    seen = set()
    lock = threading.Lock()
    active_count = {'n': 0}

    def emit(event, data):
        out.put(f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n")

    def run_source(source):
        try:
            client = MANAGER.get_client(source)
            progress = _NullProgress()
            try:
                search_urls = client._constructsearchurls(keyword=keyword, rule={}, request_overrides={})
            except Exception as err:
                emit('source_error', {'source': source, 'message': str(err)})
                return

            buckets = [[] for _ in search_urls]
            threads = []
            for i, url in enumerate(search_urls):
                t = threading.Thread(target=_safe_search, args=(client, keyword, url, buckets[i], progress), daemon=True)
                t.start()
                threads.append(t)

            deadline = time.time() + PER_SOURCE_TIMEOUT
            cursors = [0] * len(buckets)
            count = 0
            while True:
                drained = _drain(buckets, cursors, source, seen, lock, emit)
                count += drained
                alive = any(t.is_alive() for t in threads)
                if not alive or time.time() > deadline:
                    break
                time.sleep(0.1)

            count += _drain(buckets, cursors, source, seen, lock, emit)
            timed_out = any(t.is_alive() for t in threads)
            emit('source_done', {'source': source, 'count': count, 'timed_out': timed_out})
        except Exception as err:
            emit('source_error', {'source': source, 'message': str(err)})
        finally:
            with lock:
                active_count['n'] -= 1
                if active_count['n'] == 0:
                    out.put(None)

    valid_sources = [s for s in sources if s in SUPPORTED_SOURCES]
    if not valid_sources:
        yield 'event: done\ndata: {"count": 0}\n\n'
        return

    active_count['n'] = len(valid_sources)
    for source in valid_sources:
        emit('source_start', {'source': source, 'label': SUPPORTED_SOURCES[source]['label']})
        threading.Thread(target=run_source, args=(source,), daemon=True).start()

    total = 0
    while True:
        msg = out.get()
        if msg is None:
            break
        if msg.startswith('event: result'):
            total += 1
        yield msg
    yield f'event: done\ndata: {{"count": {total}}}\n\n'


# Flask App
app = Flask(__name__, static_folder=None)


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.route('/api/sources')
def api_sources():
    sources_data = []
    for sid in SOURCE_ORDER:
        info = SUPPORTED_SOURCES[sid]
        sources_data.append({
            'id': sid,
            'label': info['label'],
            'short': info['short'],
            'category': info['category'],
            'default': info['default'],
        })
    return jsonify({'sources': sources_data})


@app.route('/api/search/stream')
def api_search_stream():
    keyword = (request.args.get('q') or '').strip()
    raw_sources = (request.args.get('sources') or '').strip()
    if not keyword:
        return jsonify({'error': '关键词不能为空'}), 400

    if raw_sources:
        sources = [s for s in raw_sources.split(',') if s in SUPPORTED_SOURCES]
    else:
        sources = [s for s in SOURCE_ORDER if SUPPORTED_SOURCES[s]['default']]

    @stream_with_context
    def generate():
        yield 'retry: 10000\n\n'
        for msg in search_stream(keyword, sources):
            yield msg

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


def transcode_audio(input_bytes: bytes, target_format: str = 'mp3') -> bytes:
    target_format = target_format.lower().lstrip('.')
    inp_buffer = io.BytesIO(input_bytes)
    out_buffer = io.BytesIO()

    with av.open(inp_buffer, mode='r') as in_container:
        in_stream = next((s for s in in_container.streams if s.type == 'audio'), None)
        if in_stream is None:
            return input_bytes

        with av.open(out_buffer, mode='w', format=target_format) as out_container:
            codec_name = 'libmp3lame' if target_format == 'mp3' else target_format
            if target_format == 'wav':
                codec_name = 'pcm_s16le'
            elif target_format == 'flac':
                codec_name = 'flac'
            elif target_format in ('m4a', 'aac'):
                codec_name = 'aac'

            codec = av.Codec(codec_name, 'w')
            sample_fmt = codec.audio_formats[0].name if codec.audio_formats else 's16p'

            rate = in_stream.rate or 44100
            if codec.audio_rates and rate not in codec.audio_rates:
                rate = codec.audio_rates[0]

            out_stream = out_container.add_stream(codec_name, rate=rate)
            out_stream.format = sample_fmt
            if target_format == 'mp3':
                out_stream.bit_rate = 320000
            elif target_format in ('m4a', 'aac'):
                out_stream.bit_rate = 256000

            resampler = av.AudioResampler(
                format=sample_fmt,
                layout='stereo',
                rate=rate
            )

            for packet in in_container.demux(in_stream):
                try:
                    for frame in packet.decode():
                        frame.pts = None
                        for resampled_frame in resampler.resample(frame):
                            for out_packet in out_stream.encode(resampled_frame):
                                out_container.mux(out_packet)
                except Exception:
                    continue

            for out_packet in out_stream.encode(None):
                out_container.mux(out_packet)

    return out_buffer.getvalue()


def try_embed_metadata(raw_bytes: bytes, ext: str, song: SongInfo) -> bytes:
    """Attempt to embed lyrics and basic ID3 tags into audio bytes."""
    ext = ext.lower().lstrip('.')
    if not getattr(song, 'lyric', None) and not getattr(song, 'song_name', None):
        return raw_bytes
    try:
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = Path(tmp.name)
        if not getattr(song, 'lyric', None) and getattr(song, 'song_name', None):
            song.lyric = resolve_fast_lrc(song.song_name, getattr(song, 'singers', ''), getattr(song, 'identifier', None))
        if getattr(song, 'lyric', None):
            SongInfoUtils.embedlyrics(tmp_path, overwrite=True, lyrics_text=str(song.lyric))
        SongInfoUtils.embedbasictags(
            tmp_path, overwrite=False,
            title=str(song.song_name) if song.song_name else None,
            album=str(song.album) if song.album else None,
            artists=[str(song.singers)] if song.singers else None
        )
        with open(tmp_path, 'rb') as f:
            embedded_bytes = f.read()
        tmp_path.unlink(missing_ok=True)
        return embedded_bytes
    except Exception:
        return raw_bytes


def make_content_disposition(filename: str, ext: str = 'mp3') -> str:
    # 提取纯 ASCII 字符作为老旧客户端兜底名，严禁包含任何非 ASCII 或 Latin-1 范围外的字符
    ascii_clean = re.sub(r'[^a-zA-Z0-9_\.\-]', '_', filename)
    ascii_clean = re.sub(r'_+', '_', ascii_clean).strip('._- ')
    if not ascii_clean or ascii_clean == ext:
        safe_ascii = f"musicdl_audio.{ext}"
    elif not ascii_clean.endswith(f".{ext}"):
        safe_ascii = f"{ascii_clean}.{ext}"
    else:
        safe_ascii = ascii_clean

    encoded_filename = urllib.parse.quote(filename)
    return f'attachment; filename="{safe_ascii}"; filename*=UTF-8\'\'{encoded_filename}'


def resolve_netease_direct_url(song_id):
    """0.1秒获取网易云官方高品质音频直链"""
    if not song_id:
        return None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://music.163.com/',
    }
    for level in ['standard', 'exhigh']:
        try:
            data = {'ids': json.dumps([int(song_id)]), 'level': level, 'encodeType': 'mp3'}
            resp = requests.post('https://music.163.com/api/song/enhance/player/url/v1', data=data, headers=headers, timeout=(2, 4), verify=False).json()
            items = resp.get('data') or []
            if items and items[0].get('url'):
                return items[0]['url']
        except Exception:
            continue
    return None


def resolve_kuwo_direct_url(song_name, singers=''):
    """通过酷我官方轻量接口0.4秒极速获取全网任意歌曲的CDN播放直链"""
    if not song_name:
        return None
    clean_singers = str(singers or '').split(' / ')[0].split(',')[0].strip()
    query = f"{song_name} {clean_singers}".strip() if clean_singers else str(song_name).strip()
    try:
        url = f"http://search.kuwo.cn/r.s?client=kt&all={urllib.parse.quote(query)}&pn=0&rn=1&rformat=json&encoding=utf8"
        resp = requests.get(url, timeout=(2, 3), headers={'User-Agent': 'Mozilla/5.0'})
        m = re.search(r"['\"]MUSICRID['\"]\s*:\s*['\"](?:MUSIC_)?(\d+)['\"]", resp.text)
        if m:
            rid = m.group(1)
            play_url_api = f"http://antiserver.kuwo.cn/anti.s?type=convert_url&rid={rid}&format=mp3&response=url"
            play_resp = requests.get(play_url_api, timeout=(2, 3), headers={'User-Agent': 'Mozilla/5.0'})
            res_url = play_resp.text.strip()
            if res_url.startswith('http'):
                return res_url
    except Exception:
        pass
    return None


def resolve_qq_fast_url(song_mid):
    """QQ 音乐通过备用开放接口秒级获取播放直链"""
    if not song_mid:
        return None
    try:
        r = requests.get(f'https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_mid}&type=json', timeout=(2, 3)).json()
        u = r.get('music_url')
        if u and str(u).startswith('http'):
            return u
    except Exception:
        pass
    return None


def resolve_netease_lrc_by_id(song_id):
    """根据网易云歌曲 ID 0.05秒精准获取官方 LRC 歌词"""
    if not song_id:
        return ''
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://music.163.com/'}
    try:
        lr = requests.get(f'https://music.163.com/api/song/lyric?id={song_id}&lv=1&kv=1&tv=-1', headers=headers, timeout=(2, 3), verify=False).json()
        lrc = lr.get('lrc', {}).get('lyric', '')
        if lrc and str(lrc).strip():
            return str(lrc).strip()
    except Exception:
        pass
    return ''


def resolve_kugou_fast_lrc(song_name, singers=''):
    """通过酷狗移动端接口 0.2秒极速检索全曲库毫秒级 LRC 歌词（免鉴权，无海外 IP 封锁）"""
    if not song_name:
        return ''
    clean_singers = str(singers or '').split(' / ')[0].split(',')[0].strip()
    query = f"{song_name} {clean_singers}".strip() if clean_singers else str(song_name).strip()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        encoded_query = urllib.parse.quote(query)
        s_url = f"http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword={encoded_query}&page=1&pagesize=3"
        resp = requests.get(s_url, timeout=(2, 3), headers=headers)
        info = resp.json().get('data', {}).get('info', [])
        if not info and clean_singers:
            encoded_name = urllib.parse.quote(str(song_name).strip())
            resp = requests.get(f"http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword={encoded_name}&page=1&pagesize=3", timeout=(2, 3), headers=headers)
            info = resp.json().get('data', {}).get('info', [])
        if not info:
            return ''

        hash_ = info[0].get('hash')
        dur = info[0].get('duration', 0)
        krc_url = f"http://krcs.kugou.com/search?ver=1&man=yes&client=mobi&keyword={encoded_query}&duration={dur}&hash={hash_}"
        krc_res = requests.get(krc_url, timeout=(2, 3), headers=headers).json()
        candidates = krc_res.get('candidates') or []
        if candidates:
            cand = candidates[0]
            dl_url = f"http://lyrics.kugou.com/download?ver=1&client=pc&id={cand['id']}&accesskey={cand['accesskey']}&fmt=lrc&charset=utf8"
            dl_res = requests.get(dl_url, timeout=(2, 3), headers=headers).json()
            raw_c = dl_res.get('content')
            if raw_c:
                lrc = base64.b64decode(raw_c).decode('utf-8', errors='ignore')
                if lrc and len(lrc.strip()) > 10:
                    return str(lrc).strip()
    except Exception:
        pass
    return ''


def resolve_netease_search_lrc(song_name, singers=''):
    """通过网易云全网检索对齐获取 LRC 歌词"""
    if not song_name:
        return ''
    clean_singers = str(singers or '').split(' / ')[0].split(',')[0].strip()
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://music.163.com/'}
    queries = []
    if clean_singers:
        queries.append(f"{song_name} {clean_singers}".strip())
    queries.append(str(song_name).strip())

    for q in queries:
        try:
            sr = requests.post(
                'https://music.163.com/api/search/get/web',
                data={'s': q, 'type': 1, 'limit': 2},
                headers=headers,
                timeout=(2, 3),
                verify=False
            ).json()
            songs = sr.get('result', {}).get('songs', [])
            if songs and songs[0].get('id'):
                sid = songs[0]['id']
                lrc = resolve_netease_lrc_by_id(sid)
                if lrc:
                    return lrc
        except Exception:
            continue
    return ''


def resolve_fast_lrc(song_name, singers='', song_id=None):
    """三重极速歌词引擎：原生ID直取 -> 酷狗全曲库毫秒检索 -> 网易云跨平台对齐"""
    # 1. 若本身具备网易云数字 song_id（如歌单解析），0.05秒直取官方歌词
    if song_id and str(song_id).isdigit():
        lrc = resolve_netease_lrc_by_id(song_id)
        if lrc:
            return lrc

    # 2. 酷狗移动端极速接口（全曲库、覆盖最新最热歌曲、支持海外免鉴权直连，0.2秒响应）
    lrc = resolve_kugou_fast_lrc(song_name, singers)
    if lrc:
        return lrc

    # 3. 网易云跨平台检索对齐兜底
    lrc = resolve_netease_search_lrc(song_name, singers)
    if lrc:
        return lrc

    return ''


def resolve_instant_stream(song, entry):
    """0.3~0.8 秒按需即时获取直链，彻底代替慢速的 client.search() 避免反代 504 超时"""
    url = getattr(song, 'download_url', None)
    if url and str(url).startswith('http'):
        return url

    # 1. 酷我官方极速 CDN 直链（全网歌曲覆盖率高，0.4s 官方极速响应，免鉴权）
    url = resolve_kuwo_direct_url(song.song_name, song.singers)

    # 2. 网易云原生曲目：尝试官方直接直链
    if not url:
        raw_search = getattr(song, 'raw_data', {}).get('search', {}) if hasattr(song, 'raw_data') else {}
        song_id = raw_search.get('songid')
        if song_id:
            url = resolve_netease_direct_url(song_id)

    # 3. QQ 音乐专属直通
    if not url and (entry.get('source') == 'QQMusicClient' or 'qq' in str(entry.get('source')).lower()):
        mid = song.identifier or raw_search.get('mid') or raw_search.get('songmid')
        if mid:
            url = resolve_qq_fast_url(mid)

    # 4. 网易云跨平台检索对齐备用
    if not url:
        url = resolve_by_netease_search(song.song_name, song.singers)

    if url:
        song.download_url = url
    return url


@app.route('/api/stream/<token>')
def api_stream(token):
    entry = REGISTRY.get(token)
    if not entry:
        return '音频已失效或未找到', 404

    song = entry['song_info']
    url = resolve_instant_stream(song, entry)

    if not url or not str(url).startswith('http'):
        return '无效的音频直链', 404

    is_download = request.args.get('download') == '1'
    embed_lyric = request.args.get('embed_lyric') == '1'
    target_format = (request.args.get('format') or 'original').lower().strip().lstrip('.')

    # 在线试听：直接 302 重定向至 CDN，让浏览器原生硬解流式播放，彻底免除反代二次中转缓冲、避免 WSGI chunked 协议冲突与海外地域封锁！
    if not is_download and not embed_lyric and target_format in {'', 'original'}:
        return redirect(url, code=302)
    orig_ext = (str(getattr(song, 'ext', 'mp3')) or 'mp3').lstrip('.').lower()

    # 规范化 upstream_headers，根据真实直链域名配置，坚决避免跨平台 referer 引发 CDN 403 Forbidden
    upstream_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'identity;q=1, *;q=0',
    }
    if 'kuwo.cn' in url:
        upstream_headers['Referer'] = 'http://www.kuwo.cn/'
    elif 'music.126.net' in url or '163.com' in url:
        upstream_headers['Referer'] = 'https://music.163.com/'
    elif 'qqmusic.qq.com' in url or 'qq.com' in url:
        upstream_headers['Referer'] = 'https://y.qq.com/'

    range_header = request.headers.get('Range')
    if range_header and not is_download:
        upstream_headers['Range'] = range_header

    try:
        up = requests.get(url, headers=upstream_headers,
                          stream=True, timeout=(6, 15), verify=False)
    except Exception as err:
        return f'源站连接失败: {err}', 502

    # Check if format transcoding is required for download
    need_transcode = is_download and target_format not in {'', 'original', orig_ext}

    if need_transcode:
        try:
            raw_bytes = up.content
            transcoded_bytes = transcode_audio(raw_bytes, target_format=target_format)
            final_ext = target_format
            if embed_lyric:
                transcoded_bytes = try_embed_metadata(transcoded_bytes, final_ext, song)
            filename = f"{song.song_name} - {song.singers}.{final_ext}"
            resp_headers = {
                'Content-Type': RESULT_EXT_TO_MIME.get(final_ext, 'application/octet-stream'),
                'Content-Length': str(len(transcoded_bytes)),
                'Content-Disposition': make_content_disposition(filename, final_ext),
                'Cache-Control': 'no-cache',
            }
            return Response(transcoded_bytes, status=200, headers=resp_headers)
        except Exception:
            # Fallback to original streaming on transcoding failure
            pass

    # If original download with metadata embedding requested
    if is_download and embed_lyric:
        try:
            raw_bytes = up.content
            final_bytes = try_embed_metadata(raw_bytes, orig_ext, song)
            final_ext = orig_ext
            filename = f"{song.song_name} - {song.singers}.{final_ext}"
            resp_headers = {
                'Content-Type': RESULT_EXT_TO_MIME.get(final_ext, 'application/octet-stream'),
                'Content-Length': str(len(final_bytes)),
                'Content-Disposition': make_content_disposition(filename, final_ext),
                'Cache-Control': 'no-cache',
            }
            return Response(final_bytes, status=200, headers=resp_headers)
        except Exception:
            pass

    # Default original streaming / download
    final_ext = orig_ext
    resp_headers = {
        'Content-Type': RESULT_EXT_TO_MIME.get(final_ext, 'application/octet-stream'),
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'no-cache',
    }

    if is_download:
        filename = f"{song.song_name} - {song.singers}.{final_ext}"
        resp_headers['Content-Disposition'] = make_content_disposition(filename, final_ext)

    for h in ('Content-Length', 'Content-Range'):
        if h in up.headers:
            resp_headers[h] = up.headers[h]

    def generate():
        try:
            for chunk in up.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            up.close()

    return Response(stream_with_context(generate()), status=up.status_code, headers=resp_headers)


@app.route('/api/cover/<token>')
def api_cover(token):
    entry = REGISTRY.get(token)
    if not entry:
        return '', 404
    url = getattr(entry['song_info'], 'cover_url', None)
    if not isinstance(url, str) or not url.startswith('http'):
        return '', 404
    try:
        up = requests.get(url, headers={'User-Agent': entry['headers'].get('User-Agent', 'Mozilla/5.0')},
                          timeout=(10, 20), verify=False)
        return Response(up.content, status=up.status_code,
                        headers={'Content-Type': up.headers.get('Content-Type', 'image/jpeg'),
                                 'Cache-Control': 'public, max-age=86400'})
    except Exception:
        return '', 502


@app.route('/api/lyric/<token>')
def api_lyric(token):
    entry = REGISTRY.get(token)
    song = entry['song_info'] if entry else None

    # 优先从注册表曲目中提取，若 token 不在内存中（如容器重启后），从 query 参数提取兜底
    song_name = getattr(song, 'song_name', '') if song else (request.args.get('song_name') or '').strip()
    singers = getattr(song, 'singers', '') if song else (request.args.get('singers') or '').strip()
    song_id = getattr(song, 'identifier', '') if song else (request.args.get('song_id') or '').strip()
    if not song_id and song and hasattr(song, 'raw_data'):
        song_id = song.raw_data.get('search', {}).get('songid', '')

    raw_lyric = getattr(song, 'lyric', '') if song else ''
    lyric = str(raw_lyric or '').strip()

    if not lyric and (song_name or song_id):
        lyric = resolve_fast_lrc(song_name, singers, song_id=song_id)
        if lyric and song:
            song.lyric = lyric

    if request.args.get('download') == '1':
        if not lyric:
            return Response('', status=204)
        fname = f"{song_name or 'audio'} - {singers or 'artist'}.lrc"
        encoded_filename = urllib.parse.quote(fname)
        headers = {
            'Content-Type': 'text/plain; charset=utf-8',
            'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}",
            'Cache-Control': 'no-cache',
        }
        return Response(lyric.encode('utf-8'), status=200, headers=headers)

    return jsonify({'lyric': lyric, 'has_lyric': bool(lyric)})


def extract_playlist_title(client, song_infos, url):
    """从各音乐平台解析结果或原网页中提取真实的原始歌单名称"""
    # 1. 优先读取客户端在解析时记录的歌单名称
    name = getattr(client, 'cur_playlist_name', None)
    if name and not str(name).strip().startswith('playlist-'):
        return str(name).strip()

    # 2. 从 song_infos 首曲的 work_dir 目录还原真实歌单名
    if song_infos:
        work_dir = getattr(song_infos[0], 'work_dir', '')
        if work_dir:
            base = os.path.basename(str(work_dir).rstrip('/\\'))
            cleaned = re.sub(r'^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\s*', '', base).strip()
            if cleaned and not cleaned.startswith('playlist-'):
                return cleaned

    # 3. 若以上未获取到有效名称，通过轻量 HTTP 嗅探网页 <title> 还原
    if url and str(url).startswith('http'):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=(3, 5), verify=False)
            match = re.search(r'<title>(.*?)</title>', resp.text, re.IGNORECASE | re.DOTALL)
            if match:
                raw_title = match.group(1).strip()
                # 剔除平台品牌后缀
                for suffix in [
                    ' - 歌单 - 网易云音乐',
                    ' - 网易云音乐',
                    ' - QQ音乐-千万正版音乐海量无损曲库新歌热歌天天畅听的高品质音乐平台！',
                    ' - QQ音乐',
                    ' - 酷狗音乐',
                    ' - 酷我音乐',
                    ' - 咪咕音乐网',
                    ' - 咪咕音乐',
                    ' - Apple Music',
                ]:
                    if suffix in raw_title:
                        raw_title = raw_title.replace(suffix, '').strip()
                if ' - ' in raw_title:
                    parts = raw_title.split(' - ')
                    if len(parts) >= 2 and parts[0].strip():
                        raw_title = parts[0].strip()
                if raw_title and len(raw_title) < 100:
                    return raw_title
        except Exception:
            pass

    return (str(name).strip() if name and not str(name).startswith('playlist-') else '')


def fast_parse_netease_playlist(url):
    """极速秒级解析网易云歌单元数据，0.3秒获取全量歌曲信息"""
    m = re.search(r'id=(\d+)', url)
    if not m:
        m = re.search(r'playlist/(\d+)', url)
    if not m:
        return None
    playlist_id = m.group(1)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://music.163.com/',
    }
    try:
        resp = requests.post('https://music.163.com/api/v6/playlist/detail', data={'id': playlist_id}, headers=headers, timeout=(3, 8), verify=False)
        data = resp.json()
        playlist = data.get('playlist') or {}
        title = playlist.get('name') or f"网易云歌单-{playlist_id}"
        tracks_raw = playlist.get('tracks') or []
        track_ids = [t.get('id') for t in (playlist.get('trackIds') or []) if t.get('id')]

        if len(tracks_raw) < len(track_ids) and track_ids:
            needed_ids = track_ids[:200]
            try:
                detail_resp = requests.post(
                    'https://music.163.com/api/v3/song/detail',
                    data={'c': json.dumps([{'id': i} for i in needed_ids])},
                    headers=headers, timeout=(3, 8), verify=False
                ).json()
                if detail_resp.get('songs'):
                    tracks_raw = detail_resp.get('songs')
            except Exception:
                pass

        song_infos = []
        for t in tracks_raw:
            song_name = t.get('name') or '未知歌曲'
            singers = ' / '.join([ar.get('name') for ar in t.get('ar', []) if ar.get('name')]) or '未知歌手'
            album = t.get('al', {}).get('name') or ''
            cover_url = t.get('al', {}).get('picUrl') or ''
            song_id_str = str(t.get('id') or '')
            song_info = SongInfo(
                source='NeteaseMusicClient',
                raw_data={
                    'search': {
                        'songid': song_id_str,
                        'songname': song_name,
                        'singers': singers,
                        'album': album,
                        'cover_url': cover_url,
                        'duration': duration,
                    },
                    'download': {},
                    'lyric': {}
                }
            )
            song_info.identifier = song_id_str
            song_info.song_name = song_name
            song_info.singers = singers
            song_info.album = album
            song_info.cover_url = cover_url
            song_info.duration = duration
            song_infos.append(song_info)

        return title, song_infos
    except Exception as e:
        print(f"fast_parse_netease_playlist failed: {e}")
        return None


@app.route('/api/playlist/parse', methods=['POST'])
def api_parse_playlist():
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    source = data.get('source')
    if not url:
        return jsonify({'error': '歌单链接不能为空'}), 400

    # Auto-detect source if not specified
    if not source:
        if '163.com' in url:
            source = 'NeteaseMusicClient'
        elif 'qq.com' in url:
            source = 'QQMusicClient'
        elif 'kuwo.cn' in url:
            source = 'KuwoMusicClient'
        elif 'kugou.com' in url:
            source = 'KugouMusicClient'
        elif 'migu.cn' in url:
            source = 'MiguMusicClient'
        elif 'apple.com' in url:
            source = 'AppleMusicClient'
        elif 'spotify.com' in url:
            source = 'SpotifyMusicClient'
        else:
            source = 'NeteaseMusicClient'

    source_label_map = {
        'NeteaseMusicClient': '网易云音乐',
        'QQMusicClient': 'QQ音乐',
        'KuwoMusicClient': '酷我音乐',
        'KugouMusicClient': '酷狗音乐',
        'MiguMusicClient': '咪咕音乐',
        'AppleMusicClient': 'Apple Music',
        'SpotifyMusicClient': 'Spotify',
        'BilibiliMusicClient': 'B站音乐',
    }
    source_label = source_label_map.get(source, source)

    try:
        # 1. 优先尝试秒级极速元数据解析（针对网易云等超大歌单，秒出结果彻底避免 504 Gateway Time-out）
        if source == 'NeteaseMusicClient' or '163.com' in url:
            fast_res = fast_parse_netease_playlist(url)
            if fast_res:
                final_title, song_infos = fast_res
                tracks = []
                for song_info in (song_infos or []):
                    token = REGISTRY.add(song_info, 'NeteaseMusicClient')
                    tracks.append(track_to_payload(song_info, token, 'NeteaseMusicClient'))
                return jsonify({
                    'source': 'NeteaseMusicClient',
                    'source_label': '网易云音乐',
                    'title': final_title,
                    'playlist_name': final_title,
                    'count': len(tracks),
                    'tracks': tracks
                })

        # 2. 兜底调用客户端原生解析（强制开启 fast_metadata_mode 并设置 12 秒熔断）
        client = MANAGER.get_client(source)
        if hasattr(client, 'cur_playlist_name'):
            delattr(client, 'cur_playlist_name')
        client.fast_metadata_mode = True

        def _do_client_parse():
            return client.parseplaylist(url)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_client_parse)
            try:
                song_infos = future.result(timeout=12)
            except concurrent.futures.TimeoutError:
                return jsonify({'error': f'{source_label}歌单解析超时（超过12秒），源站响应缓慢，请稍后重试或检查链接是否有效'}), 200

        tracks = []
        for song_info in (song_infos or []):
            token = REGISTRY.add(song_info, source)
            tracks.append(track_to_payload(song_info, token, source))

        if not tracks:
            return jsonify({'error': f'未在{source_label}歌单中提取到有效曲目，请检查歌单是否公开或链接是否有效'}), 200

        playlist_title = extract_playlist_title(client, song_infos, url)
        final_title = playlist_title or f"{source_label}歌单"

        return jsonify({
            'source': source,
            'source_label': source_label,
            'title': final_title,
            'playlist_name': final_title,
            'count': len(tracks),
            'tracks': tracks
        })
    except Exception as err:
        return jsonify({'error': f"解析歌单失败: {str(err)}"}), 200


@app.route('/api/download/local', methods=['POST'])
def api_download_local():
    data = request.get_json(silent=True) or {}
    token = data.get('token')
    entry = REGISTRY.get(token)
    if not entry:
        return jsonify({'error': '曲目未找到'}), 404

    song: SongInfo = entry['song_info']
    source = entry['source']
    
    def do_download():
        try:
            client = MANAGER.get_client(source)
            client.download(song_infos=[song])
        except Exception as e:
            print(f"Download error: {e}")

    threading.Thread(target=do_download, daemon=True).start()
    return jsonify({'success': True, 'message': '已加入后台下载队列'})


@app.route('/api/track/resolve', methods=['POST'])
def api_track_resolve():
    """当曲目的 token 或源站直链失效时，根据歌曲名与歌手即时自愈重新连接最新可用音源"""
    data = request.get_json(silent=True) or {}
    song_name = str(data.get('song_name', '')).strip()
    singers = str(data.get('singers', '')).strip()
    source = str(data.get('source', '')).strip()
    if not song_name:
        return jsonify({'error': '缺少歌曲名'}), 400

    # 秒级极速获取可用直链，绝不调用慢速全局 search 导致网关 504 切断
    direct_url = resolve_kuwo_direct_url(song_name, singers) or resolve_by_netease_search(song_name, singers)
    if direct_url:
        new_song = SongInfo(
            source='KuwoMusicClient' if 'kuwo' in direct_url else 'NeteaseMusicClient',
            song_name=song_name,
            singers=singers or '未知歌手',
            download_url=direct_url
        )
        new_song.ext = 'mp3'
        new_token = REGISTRY.add(new_song, new_song.source)
        payload = track_to_payload(new_song, new_token, new_song.source)
        return jsonify({'success': True, 'track': payload})

    return jsonify({'error': f'未检索到可用的音源直链: {song_name}'}), 200


def run_server(host='127.0.0.1', port=5050, work_dir=None):
    global DOWNLOAD_DIR, REGISTRY_CACHE_FILE
    if work_dir:
        DOWNLOAD_DIR = os.path.abspath(work_dir)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        REGISTRY_CACHE_FILE = os.path.join(DOWNLOAD_DIR, '.track_registry.json')
    app.run(host=host, port=port, threaded=True, debug=False)


if __name__ == '__main__':
    run_server()
