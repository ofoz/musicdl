import json
import requests

def test_safe_download_and_lyric_badges():
    base_url = 'http://127.0.0.1:5050'

    print("1. 验证搜索流式接口输出 has_lyric 字段...")
    r = requests.get(f'{base_url}/api/search/stream?q=青花瓷&sources=KuwoMusicClient,NeteaseMusicClient', stream=True, timeout=15)
    with_lyric_token = None
    sample_song = None
    for line in r.iter_lines():
        if line:
            decoded = line.decode('utf-8', errors='ignore')
            if decoded.startswith('data:') and 'token' in decoded:
                payload = json.loads(decoded[5:].strip())
                assert 'has_lyric' in payload, "Payload 未包含 has_lyric 属性"
                if payload['has_lyric'] and not with_lyric_token:
                    with_lyric_token = payload['token']
                    sample_song = payload['song_name']
                    break

    assert with_lyric_token, "未能检索到带有歌词的有效曲目"
    print(f"[Pass] 匹配到含歌词曲目: 《{sample_song}》, Token: {with_lyric_token}")

    print("\n2. 验证含歌词曲目 API...")
    lyric_res = requests.get(f'{base_url}/api/lyric/{with_lyric_token}', timeout=10)
    assert lyric_res.status_code == 200
    lyric_json = lyric_res.json()
    assert lyric_json.get('has_lyric') is True
    assert len(lyric_json.get('lyric', '')) > 0
    print(f"[Pass] 歌词 JSON 获取成功，has_lyric=True，长度: {len(lyric_json['lyric'])}")

    print("\n3. 验证无歌词或无效曲目的优雅降级（不再抛出 404）...")
    empty_res = requests.get(f'{base_url}/api/lyric/invalid_non_exist_token?download=1', timeout=10)
    # 204 No Content，安全容错
    assert empty_res.status_code == 204, f"期望返回 204 No Content，实际返回: {empty_res.status_code}"
    print(f"[Pass] 无效或无歌词下载返回 HTTP {empty_res.status_code}，安全静默跳过")

    empty_json_res = requests.get(f'{base_url}/api/lyric/invalid_non_exist_token', timeout=10)
    assert empty_json_res.status_code == 200
    assert empty_json_res.json().get('has_lyric') is False
    print(f"[Pass] 无歌词 JSON 正确标识 has_lyric=False")

    print("\n4. 验证前端 HTML 与 JS 中双通道隔离下载与歌词标识...")
    html_text = requests.get(f'{base_url}/', timeout=10).text
    assert '品质 / 歌词' in html_text, "表头未更新为 '品质 / 歌词'"
    assert 'id="modalLyricNote"' in html_text, "弹窗缺少 modalLyricNote 标识"

    js_text = requests.get(f'{base_url}/static/app.js', timeout=10).text
    assert 'triggerIframeDownload' in js_text, "app.js 缺少 triggerIframeDownload"
    assert 'downloadLrcFile' in js_text, "app.js 缺少 downloadLrcFile"
    assert 'lyricBadge' in js_text, "app.js 缺少 lyricBadge"
    print(f"[Pass] 前端已部署独立 iframe 下载隔离引擎与绿色 [词] / 灰色 [无词] 徽标")

    print("\n=======================================================")
    print(" 双通道下载修复与歌词标识所有功能点验证通过！ ")
    print("=======================================================")

if __name__ == '__main__':
    test_safe_download_and_lyric_badges()
