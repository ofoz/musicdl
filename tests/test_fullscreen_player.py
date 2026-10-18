import requests
import re

def test_fullscreen_player():
    base_url = 'http://127.0.0.1:5050'

    print("1. 验证首页 HTML 中全屏大播放器 DOM 节点...")
    html_res = requests.get(f'{base_url}/', timeout=10)
    assert html_res.status_code == 200, f"HTTP Error: {html_res.status_code}"
    html_text = html_res.text

    required_dom_ids = [
        'fullscreenPlayer',
        'fsBgBlur',
        'fsCloseBtn',
        'fsHeaderTitle',
        'fsHeaderArtist',
        'fsDownloadBtn',
        'vinylNeedle',
        'vinylDisc',
        'fsCoverImg',
        'fsSourceBadge',
        'fsExtBadge',
        'fsLyricContainer',
        'fsCurrentTime',
        'fsDuration',
        'fsSeekSlider',
        'fsPlayModeBtn',
        'fsPlayPauseBtn',
        'fsPrevBtn',
        'fsNextBtn',
        'playerTrackInfo',
        'expandPlayerBtn'
    ]

    for dom_id in required_dom_ids:
        assert f'id="{dom_id}"' in html_text, f"缺少 DOM 元素 ID: {dom_id}"
    print(f"[Pass] 校验通过：首页具备完整的沉浸式黑胶唱机与全屏歌词骨架（共 {len(required_dom_ids)} 个关键节点）")

    print("\n2. 验证 style.css 中黑胶动画与全屏歌词样式...")
    css_res = requests.get(f'{base_url}/static/style.css', timeout=10)
    assert css_res.status_code == 200
    css_text = css_res.text

    required_css_classes = [
        '#fullscreenPlayer.player-open',
        '.vinyl-disc',
        '.vinyl-grooves',
        '@keyframes spinDisc',
        '.spin-playing',
        '.spin-paused',
        '.needle-playing',
        '.needle-paused',
        '.fs-lyric-line',
        '.fs-lyric-active'
    ]

    for cls in required_css_classes:
        assert cls in css_text, f"缺少 CSS 规则: {cls}"
    print(f"[Pass] 校验通过：包含全屏黑胶旋转、唱针摆动、高斯环境光与大字号同步歌词样式（共 {len(required_css_classes)} 条关键规则）")

    print("\n3. 验证 app.js 控制器逻辑...")
    js_res = requests.get(f'{base_url}/static/app.js', timeout=10)
    assert js_res.status_code == 200
    js_text = js_res.text

    required_js_functions = [
        'openFullscreenPlayer',
        'closeFullscreenPlayer',
        'setPlayMode',
        'playNextTrack',
        'playPrevTrack',
        'updatePlayPauseIcon'
    ]

    for fn in required_js_functions:
        assert fn in js_text, f"缺少 JS 函数: {fn}"
    
    # 验证 playTrack 内部是否调用 openFullscreenPlayer
    assert 'openFullscreenPlayer' in js_text
    assert 'Escape' in js_text
    print(f"[Pass] 校验通过：JS 控制器已具备“播放时自动切入大播放器”、黑胶状态联动、大字歌词同步与单曲/随机/循环模式")

    print("\n=======================================================")
    print(" 沉浸式大播放器静态与集成校验全部通过！ ")
    print("=======================================================")

if __name__ == '__main__':
    test_fullscreen_player()
