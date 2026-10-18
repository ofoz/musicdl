import unittest
import requests
from musicdl.web.server import extract_playlist_title
from musicdl.modules.utils.data import SongInfo

class DummyClient:
    def __init__(self, name=None):
        if name:
            self.cur_playlist_name = name

class TestPlaylistOriginalTitle(unittest.TestCase):
    def test_01_extract_from_client_cur_playlist_name(self):
        """测试从 client.cur_playlist_name 提取歌单原始名称"""
        client = DummyClient("周杰伦经典专辑全集")
        title = extract_playlist_title(client, [], "")
        self.assertEqual(title, "周杰伦经典专辑全集")

    def test_02_extract_from_song_info_work_dir(self):
        """测试从 song_info.work_dir 还原原始歌单名称"""
        client = DummyClient("playlist-12345")  # 占位默认名
        song = SongInfo(source="QQMusicClient")
        song.work_dir = "C:/musicdl/downloads/QQMusicClient/2026-10-18-15-24-33 华语流行巅峰榜"
        title = extract_playlist_title(client, [song], "")
        self.assertEqual(title, "华语流行巅峰榜")

    def test_03_extract_from_html_title_fallback(self):
        """测试网页 title 嗅探过滤平台后缀"""
        client = DummyClient(None)
        # 测试网易云音乐公开发布的歌单
        url = "https://music.163.com/playlist?id=3778678"
        title = extract_playlist_title(client, [], url)
        # 网易云 3778678 为 热歌榜
        self.assertIn("热歌榜", title)

    def test_04_api_returns_title_and_playlist_name(self):
        """测试 /api/playlist/parse 响应包含 title 与 playlist_name 字段"""
        resp = requests.post("http://127.0.0.1:5050/api/playlist/parse", json={"url": ""})
        self.assertEqual(resp.status_code, 400)

        # 检查代码中是否注册了相应字段映射
        import inspect
        from musicdl.web import server
        source_code = inspect.getsource(server.api_parse_playlist)
        self.assertIn("'title': final_title", source_code)
        self.assertIn("'playlist_name': final_title", source_code)
        self.assertIn("'source_label': source_label", source_code)

    def test_05_frontend_uses_original_title(self):
        """测试前端 app.js 使用 data.title / data.playlist_name 作为歌单卡片名称"""
        resp = requests.get("http://127.0.0.1:5050/static/app.js")
        self.assertEqual(resp.status_code, 200)
        js = resp.text
        self.assertIn("data.title || data.playlist_name", js)
        self.assertNotIn("target.name = `${target.source_label}歌单 · ${data.tracks.length}首`", js)

if __name__ == '__main__':
    unittest.main()
