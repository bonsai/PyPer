"""
research.py テストスクリプト
============================
使い方:
  python test_research.py             # 全テスト実行
  python test_research.py --dry-only  # dry run だけ
  python test_research.py --quick     # 関数単体テストだけ（ネットワークなし）
"""

import os, sys, json, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# research.py のインポート
sys.path.insert(0, str(Path(__file__).parent))
import research


# ── ユーティリティテスト ──

class TestUtils(unittest.TestCase):
    def test_save_json_creates_file(self):
        tmp = Path("data/_test_utils.json")
        research.save_json({"hello": "world"}, tmp)
        self.assertTrue(tmp.exists())
        data = json.loads(tmp.read_text(encoding="utf-8"))
        self.assertEqual(data["hello"], "world")
        tmp.unlink()

    def test_log_output(self):
        # 標準出力に出るだけなので例外が出なければOK
        research.log("test message")


# ── Googleトレンドモックテスト ──

class TestFetchTrendsQuick(unittest.TestCase):
    @patch("research.fetch_trends")
    def test_structure(self, mock_fetch):
        mock_fetch.return_value = {"trending": ["A", "B"], "related": [{"keyword": "A", "query": "B", "value": 100}]}
        result = research.fetch_trends()
        self.assertIn("trending", result)
        self.assertIn("related", result)
        self.assertIsInstance(result["trending"], list)
        self.assertIsInstance(result["related"], list)


# ── YouTube モックテスト ──

class TestYouTubeMocked(unittest.TestCase):
    def test_fetch_youtube_data_empty_channels(self):
        """WATCH_CHANNELS が空のときも動くこと"""
        with patch.object(research, "WATCH_CHANNELS", {}):
            with patch.object(research, "SEED_KEYWORDS", ["test"]):
                with patch.object(research, "YOUTUBE_API_KEY", ""):
                    with patch("research.fetch_yt_dlp", return_value=[]):
                        videos = research.fetch_youtube_data({"trending": []})
                        self.assertEqual(videos, [])

    def test_dedup_logic(self):
        """重複除去ロジックのテスト"""
        sample = [
            {"video_id": "abc", "views": 100, "title": "A"},
            {"video_id": "abc", "views": 200, "title": "A dup"},
            {"video_id": "xyz", "views": 50, "title": "B"},
        ]
        seen, unique = set(), []
        for v in sample:
            key = v.get("video_id") or v.get("url")
            if key and key not in seen:
                seen.add(key)
                unique.append(v)
        unique.sort(key=lambda x: x.get("views", 0), reverse=True)
        self.assertEqual(len(unique), 2)
        self.assertEqual(unique[0]["video_id"], "abc")


# ── Qwen分析モックテスト ──

class TestQwenAnalysis(unittest.TestCase):
    def test_dry_run(self):
        result = research.analyze_with_qwen({"trending": [], "related": []}, [], dry=True)
        self.assertEqual(result, "（dry run）")

    def test_no_api_key(self):
        with patch.object(research, "QWEN_API_KEY", ""):
            result = research.analyze_with_qwen({"trending": [], "related": []}, [], dry=False)
            self.assertIn("未設定", result)

    def test_mock_api_call(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "### test analysis"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("research.QWEN_API_KEY", "test-key"):
            with patch("research.QWEN_BASE_URL", "https://example.com"):
                with patch("openai.OpenAI", return_value=mock_client):
                    result = research.analyze_with_qwen(
                        {"trending": ["A"], "related": [{"keyword": "A", "query": "B", "value": 100}]},
                        [{"title": "Test Video", "channel": "Ch", "views": 1000}]
                    )
                    self.assertIn("test analysis", result)
                    mock_client.chat.completions.create.assert_called_once()


# ── レポートビルドテスト ──

class TestReportBuild(unittest.TestCase):
    def test_build_report(self):
        trends = {"trending": ["キーワード1", "キーワード2"], "related": []}
        videos = [
            {"title": "テスト動画", "channel": "テストチャンネル", "views": 10000,
             "url": "https://youtube.com/watch?v=abc"},
        ]
        analysis = "### テスト分析結果\n本文"
        report = research.build_report(trends, videos, analysis)
        self.assertIn("週次トレンドリサーチ", report)
        self.assertIn("Qwen 分析", report)
        self.assertIn("テスト動画", report)
        self.assertIn("キーワード1", report)


# ── dry run 実行テスト ──

class TestDryRun(unittest.TestCase):
    @patch.object(sys, "argv", ["research.py", "--dry", "--no-trends", "--no-youtube"])
    def test_dry_run_main(self):
        """main() が例外を出さず終了すること"""
        # QWEN_API_KEY を空にしておけばスキップされる
        with patch.object(research, "QWEN_API_KEY", ""):
            research.main()
        # レポートファイルが生成されていることを確認
        date_str = datetime.now().strftime("%Y%m%d")
        report_path = Path(f"report_{date_str}.md")
        self.assertTrue(report_path.exists())
        report_path.unlink()


# ── メイン ──

if __name__ == "__main__":
    # --quick: ネットワーク系をスキップ
    if "--quick" in sys.argv:
        suite = unittest.TestSuite()
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestUtils))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestYouTubeMocked))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestQwenAnalysis))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestReportBuild))
        unittest.TextTestRunner(verbosity=2).run(suite)
    else:
        unittest.main(verbosity=2)
