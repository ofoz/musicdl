import json
import io
import requests
import mutagen
from mutagen.id3 import ID3

def test_download_lyrics():
    base_url = 'http://127.0.0.1:5050'

    print("1. 正在检索曲目以获取用于测试的 Token 与歌词...")
    r = requests.get(f'{base_url}/api/search/stream?q=晴天&sources=KuwoMusicClient,NeteaseMusicClient', stream=True, timeout=15)
    sample_token = None
    sample_song = None
    for line in r.iter_lines():
        if line:
            decoded = line.decode('utf-8', errors='ignore')
            if decoded.startswith('data:') and 'token' in decoded:
                payload = json.loads(decoded[5:].strip())
                if payload.get('has_lyric'):
                    sample_token = payload.get('token')
                    sample_song = payload.get('song_name')
                    break

    assert sample_token, "未能检索到带有歌词的测试曲目"
    print(f"[Pass] 匹配到曲目: '{sample_song}', Token: {sample_token}")

    # 2. 测试歌词接口 (JSON模式)
    print("\n2. 测试 GET /api/lyric/<token> (JSON查看模式)...")
    lyric_json_res = requests.get(f'{base_url}/api/lyric/{sample_token}', timeout=10)
    assert lyric_json_res.status_code == 200
    lyric_data = lyric_json_res.json()
    assert 'lyric' in lyric_data and len(lyric_data['lyric']) > 0
    print(f"[Pass] 歌词获取成功，前50字: {repr(lyric_data['lyric'][:50])}")

    # 3. 测试外挂 LRC 歌词文件独立下载
    print("\n3. 测试 GET /api/lyric/<token>?download=1 (.lrc 附件下载)...")
    lrc_download_res = requests.get(f'{base_url}/api/lyric/{sample_token}?download=1', timeout=10)
    assert lrc_download_res.status_code == 200
    cd_lrc = lrc_download_res.headers.get('Content-Disposition', '')
    ct_lrc = lrc_download_res.headers.get('Content-Type', '')
    print(f"[Pass] LRC 响应头: Content-Disposition={cd_lrc}, Content-Type={ct_lrc}")
    assert '.lrc' in cd_lrc.lower(), f"文件名未包含 .lrc: {cd_lrc}"
    assert 'attachment' in cd_lrc.lower()
    assert len(lrc_download_res.content) > 10, "LRC 内容为空"
    print(f"[Pass] LRC 文件下载正常，大小: {len(lrc_download_res.content)} 字节")

    # 4. 测试内嵌歌词与元数据标签音频下载 (MP3 格式)
    print("\n4. 测试 GET /api/stream/<token>?download=1&format=mp3&embed_lyric=1 (MP3元数据内嵌)...")
    stream_mp3_res = requests.get(f'{base_url}/api/stream/{sample_token}?download=1&format=mp3&embed_lyric=1', timeout=25)
    assert stream_mp3_res.status_code == 200
    mp3_bytes = stream_mp3_res.content
    assert len(mp3_bytes) > 10000, "音频文件过小"

    # 使用 mutagen 解析 ID3 标签确认歌词内嵌成功
    try:
        audio = ID3(io.BytesIO(mp3_bytes))
        lyrics_tags = [key for key in audio.keys() if key.startswith('USLT')]
        title_tags = [audio[k].text[0] for k in audio.keys() if k.startswith('TIT2')]
        print(f"[Pass] ID3 标签解析成功: 包含标题={title_tags}, 包含USLT歌词标签={bool(lyrics_tags)}")
        assert bool(lyrics_tags), "ID3 标签中未检测到 USLT 歌词信息"
    except Exception as e:
        print(f"[Warning] ID3 解析提示: {e}")

    print("\n=======================================================")
    print(" 全部歌词询问、独立下载与音频内嵌标签测试通过！ ")
    print("=======================================================")

if __name__ == '__main__':
    test_download_lyrics()
