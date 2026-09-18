"""Top5 独立数据源回归测试。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import github_top5


class Top5Tests(unittest.TestCase):
    def items(self):
        """构造 GitHub Search API 的仓库样本。"""
        return [dict(full_name=f"org/model{i}", name=f"model{i}", owner={"login": "org"},
                     html_url=f"https://github.com/org/model{i}", stargazers_count=i,
                     forks_count=i + 2, language="Python", topics=["llm"],
                     description=f"Model {i}", updated_at="2026-09-18T00:00:00Z")
                for i in range(7)]

    def test_fetch_returns_five_sorted_canonical_repos(self):
        """独立搜索按 Star 排名，保留真实 Fork 和简介。"""
        response = Mock()
        response.json.return_value = {"items": self.items(), "incomplete_results": False}
        with patch.object(github_top5.requests, "get", return_value=response) as get:
            data = github_top5.fetch_top5()
        self.assertEqual([r["stars"] for r in data["repos"]], [6, 5, 4, 3, 2])
        self.assertEqual(data["repos"][0]["forks"], 8)
        self.assertEqual(data["repos"][0]["full_name"], "org/model6")
        self.assertEqual(data["repos"][0]["summary"], "Model 6")
        self.assertIn("api.github.com/search/repositories", get.call_args.args[0])
        self.assertEqual(get.call_args.kwargs["params"]["sort"], "stars")
        self.assertEqual(get.call_count, 5)
        for call in get.call_args_list:
            self.assertEqual(call.kwargs["params"]["q"].count("topic:"), 1)
        self.assertEqual(len({r["full_name"] for r in data["repos"]}), 5)

    def test_rejects_short_or_incomplete_search_results(self):
        """不把不完整的结果发布成正常 Top5。"""
        for payload in ({"items": self.items()[:1]}, {"items": self.items(), "incomplete_results": True}):
            response = Mock()
            response.json.return_value = payload
            with patch.object(github_top5.requests, "get", return_value=response):
                with self.assertRaises(ValueError):
                    github_top5.fetch_top5()

    def test_failed_refresh_preserves_existing_file(self):
        """上游失败时保留上次有效数据和时间戳。"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github_top5.json"
            original = '{"generated_at":"old","repos":[]}'
            target.write_text(original)
            with patch.object(github_top5, "fetch_top5", side_effect=ValueError("upstream unavailable")):
                with self.assertRaises(ValueError):
                    github_top5.refresh(target)
            self.assertEqual(target.read_text(), original)

    def test_refresh_writes_canonical_data(self):
        """成功刷新后写入完整数据。"""
        data = {"generated_at": "now", "repos": [{"full_name": "org/repo"}]}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github_top5.json"
            with patch.object(github_top5, "fetch_top5", return_value=data):
                github_top5.refresh(target)
            self.assertEqual(json.loads(target.read_text()), data)


if __name__ == "__main__":
    unittest.main()
