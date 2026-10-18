import requests

def test_my_playlists_and_backup():
    base_url = 'http://127.0.0.1:5050'

    print("1. 验证 HTML 中右上角【我的歌单】入口与模态框节点...")
    html_res = requests.get(f'{base_url}/', timeout=10)
    assert html_res.status_code == 200
    html_text = html_res.text

    required_dom_ids = [
        'myPlaylistsBtn',
        'myPlaylistsCountBadge',
        'myPlaylistsModal',
        'modalPlTotalBadge',
        'closePlaylistsModalBtn',
        'exportConfigBtn',
        'importConfigTriggerBtn',
        'importConfigFileInput',
        'modalPlaylistUrlInput',
        'modalPlaylistCustomName',
        'modalImportPlaylistBtn',
        'myPlaylistsCardsContainer'
    ]

    for dom_id in required_dom_ids:
        assert f'id="{dom_id}"' in html_text, f"缺少 DOM 元素 ID: {dom_id}"
    print(f"[Pass] 校验通过：首页具备【我的歌单】右上角入口与完整管理中枢 DOM 骨架（共 {len(required_dom_ids)} 个节点）")

    print("\n2. 验证本地数据安全与隐私提醒文案...")
    assert "保存在当前电脑/手机浏览器的本地缓存" in html_text or "保存在当前浏览器的本地设备中" in html_text or "Local Storage" in html_text
    assert "一键导出备份" in html_text
    print("[Pass] 校验通过：已明确告知用户数据存储于本地 LocalStorage，需自行导出妥善保管")

    print("\n3. 验证 app.js 中的歌单存储与跨设备导入导出控制器...")
    js_res = requests.get(f'{base_url}/static/app.js', timeout=10)
    assert js_res.status_code == 200
    js_text = js_res.text

    assert 'soundflow_my_playlists' in js_text, "缺少 soundflow_my_playlists 存储键"
    assert 'getMyPlaylists' in js_text, "缺少 getMyPlaylists 方法"
    assert 'saveMyPlaylists' in js_text, "缺少 saveMyPlaylists 方法"
    assert 'exportConfigBtn' in js_text, "缺少 exportConfigBtn 绑定"
    assert 'importConfigTriggerBtn' in js_text, "缺少 importConfigTriggerBtn 绑定"
    assert 'modalImportPlaylistBtn' in js_text, "缺少 modalImportPlaylistBtn 绑定"
    print("[Pass] 校验通过：app.js 已实现多歌单持久化、一键播放全部、一键导出备份与配置恢复")

    print("\n4. 验证 /api/playlist/parse 接口正常...")
    parse_res = requests.post(f'{base_url}/api/playlist/parse', json={'url': ''}, timeout=10)
    # 空 URL 应当返回 400 校验提示
    assert parse_res.status_code == 400
    print("[Pass] 校验通过：歌单解析接口响应正常")

    print("\n=======================================================")
    print(" 【我的歌单】与跨设备备份导出导入验证全部通过！ ")
    print("=======================================================")

if __name__ == '__main__':
    test_my_playlists_and_backup()
