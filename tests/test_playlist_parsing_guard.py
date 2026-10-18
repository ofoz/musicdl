import unittest
import requests

BASE_URL = "http://127.0.0.1:5050"

class TestPlaylistParsingGuard(unittest.TestCase):
    def test_01_html_contains_parsing_alert_banner(self):
        """测试 index.html 存在醒目的解析防关闭强提醒横幅"""
        resp = requests.get(f"{BASE_URL}/")
        self.assertEqual(resp.status_code, 200)
        html = resp.text

        # 检查元素 ID
        self.assertIn('id="playlistParsingAlert"', html)
        # 检查核心警示文案
        self.assertIn("请勿关闭或刷新网页", html)
        self.assertIn("全部歌单解析完成前请绝对不要关闭或刷新此浏览器窗口", html)
        self.assertIn("animate-pulse", html)

    def test_02_js_contains_window_beforeunload_guard(self):
        """测试 app.js 实现了 window.onbeforeunload 物理级防误关拦截"""
        resp = requests.get(f"{BASE_URL}/static/app.js")
        self.assertEqual(resp.status_code, 200)
        js = resp.text

        # 检查 guard 函数
        self.assertIn("function updateParsingGuard()", js)
        # 检查原生事件拦截
        self.assertIn("window.onbeforeunload = function", js)
        self.assertIn("e.preventDefault()", js)
        self.assertIn("如果在解析完成前关闭或刷新网页，解析传输将被强制中断", js)
        # 检查解析完成后解除拦截
        self.assertIn("window.onbeforeunload = null", js)

    def test_03_card_and_toast_strong_warning(self):
        """测试卡片状态与提交Toast均带有请勿关闭页面的强提醒"""
        resp = requests.get(f"{BASE_URL}/static/app.js")
        self.assertEqual(resp.status_code, 200)
        js = resp.text

        # 卡片解析中文案强化
        self.assertIn("正在后台解析中（请保持当前网页开启，勿关闭！）", js)
        # 提交时的强提醒 Toast
        self.assertIn("请保持当前网页开启，全部解析完毕前切勿关闭！", js)
        # 弹窗收起时的兜底提醒
        self.assertIn("歌单仍在后台持续解析中，请保持当前网页开启直至完成！", js)

if __name__ == '__main__':
    unittest.main()
