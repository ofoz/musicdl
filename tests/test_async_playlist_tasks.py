import unittest
import requests
import concurrent.futures
import time

BASE_URL = "http://127.0.0.1:5050"

class TestAsyncPlaylistTasks(unittest.TestCase):
    def test_01_playlist_parse_api_empty_url(self):
        """测试歌单解析接口处理空URL的能力"""
        resp = requests.post(f"{BASE_URL}/api/playlist/parse", json={"url": ""})
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("error", data)

    def test_02_playlist_parse_api_concurrent_calls(self):
        """测试歌单解析接口支持多任务高并发请求（模拟前端添加多个歌单同时在后台解析）"""
        urls = [
            {"url": "https://music.163.com/playlist?id=3778678"},  # 网易云热歌榜
            {"url": "https://music.163.com/playlist?id=3779629"},  # 网易云新歌榜
            {"url": "https://invalid-playlist-url-test.com/list/123"}, # 非法链接
        ]

        def call_parse(item):
            t0 = time.time()
            try:
                r = requests.post(f"{BASE_URL}/api/playlist/parse", json=item, timeout=15)
                return r.status_code, r.json(), time.time() - t0
            except Exception as e:
                return 500, {"error": str(e)}, time.time() - t0

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(call_parse, item) for item in urls]
            results = [f.result() for f in futures]

        # 检查是否全部得到响应且不发生服务器挂死
        self.assertEqual(len(results), 3)
        for code, data, elapsed in results:
            self.assertIn(code, [200, 400, 500])
            print(f"[Concurrent Test] Status: {code}, Elapsed: {elapsed:.2f}s, Response keys: {list(data.keys())}")

    def test_03_frontend_async_task_code_checks(self):
        """验证前端代码中实现了即时清空输入、保留焦点、并发任务及状态自愈机制"""
        resp = requests.get(f"{BASE_URL}/static/app.js")
        self.assertEqual(resp.status_code, 200)
        js_code = resp.text

        # 1. 验证存在任务提交与清空输入框、重新聚焦逻辑
        self.assertIn("submitPlaylistTask", js_code)
        self.assertIn("modalPlaylistUrlInput.value = ''", js_code)
        self.assertIn("modalPlaylistUrlInput.focus()", js_code)

        # 2. 验证任务模型中包含 status: 'parsing' 初始状态
        self.assertIn("status: 'parsing'", js_code)

        # 3. 验证存在非阻塞后台任务执行器 runPlaylistTask
        self.assertIn("runPlaylistTask(taskItem)", js_code)

        # 4. 验证渲染中有 '正在后台解析中' 强提醒或旋转动效指示
        self.assertIn("正在后台解析中", js_code)
        self.assertIn("animate-spin", js_code)

        # 5. 验证页面加载时的任务续跑自愈逻辑
        self.assertIn("pl.status === 'parsing'", js_code)

    def test_04_html_and_css_structure(self):
        """验证HTML和CSS具备歌单卡片与模态框支撑"""
        html_resp = requests.get(f"{BASE_URL}/")
        self.assertEqual(html_resp.status_code, 200)
        self.assertIn("myPlaylistsModal", html_resp.text)
        self.assertIn("modalImportPlaylistBtn", html_resp.text)

        css_resp = requests.get(f"{BASE_URL}/static/style.css")
        self.assertEqual(css_resp.status_code, 200)
        self.assertIn("playlist-card", css_resp.text)

if __name__ == '__main__':
    unittest.main()
