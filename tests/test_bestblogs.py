"""Offline RSS contract tests; only the HTTP boundary is mocked."""
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

import requests

from scripts.db_init import init_db
from scripts.pipeline import SOURCES, scanner

URL = "https://www.bestblogs.dev/zh/feeds/rss?category=ai&type=article&minScore=85&timeFilter=1w"
SOURCE = {"name": "BestBlogs", "url": URL, "category": "中文媒体", "max_entries": 100}


def response(count=1, campaign="rss", extra=""):
    items = []
    for i in range(count):
        link = f"https://www.bestblogs.dev/article/{i}?utm_source={campaign}&utm_medium=feed{extra}"
        items.append(f"""<item><title>AI article {i}</title>
        <link>{escape(link)}</link><guid>{escape(link)}</guid>
        <description><![CDATA[<p>BestBlogs 摘要</p><a href="{link}">阅读更多</a>]]></description>
        <pubDate>Fri, 18 Sep 2026 08:00:00 GMT</pubDate></item>""")
    result = requests.Response()
    result.status_code = 200
    result._content = ("<rss version='2.0'><channel><title>BestBlogs</title>" + "".join(items) + "</channel></rss>").encode()
    return result


class BestBlogsTests(unittest.TestCase):
    def test_source_config_adds_bestblogs_without_replacing_existing_sources(self):
        matches = [s for s in SOURCES if s['name'] == 'BestBlogs']
        self.assertEqual(matches, [SOURCE])
        self.assertEqual({s['name'] for s in SOURCES if s['name'] != 'BestBlogs'}, {
            'OpenAI Blog', 'Google AI', 'Google DeepMind', 'Apple ML Research',
            'NVIDIA Blog', 'ArXiv cs.AI', 'ArXiv cs.LG', 'ArXiv cs.CL',
            'ArXiv cs.CV', 'ArXiv stat.ML', 'HuggingFace Blog', 'PyTorch Blog',
            '雷锋网 AI', '量子位', 'TechCrunch AI', 'VentureBeat AI',
        })

    def test_bestblogs_reads_100_entries_and_caps_larger_feeds(self):
        for count in (100, 101):
            with self.subTest(count=count), patch.object(scanner.requests, 'get', return_value=response(count)):
                articles = scanner.fetch_feed(SOURCE, retries=0)
                self.assertEqual(len(articles), 100)
                self.assertEqual(articles[-1]['title'], 'AI article 99')

    def test_bestblogs_keeps_attribution_and_page_url_but_removes_only_utm(self):
        with patch.object(scanner.requests, 'get', return_value=response(extra='&lang=zh&empty=#section')):
            article = scanner.fetch_feed(SOURCE, retries=0)[0]
        self.assertEqual(article['link'], 'https://www.bestblogs.dev/article/0?lang=zh&empty=#section')
        self.assertEqual(article['source_name'], 'BestBlogs')
        self.assertEqual(article['summary'], 'BestBlogs 摘要阅读更多')
        self.assertEqual(article['published'], '2026-09-18 08:00:00')

    def test_other_sources_keep_default_limit_and_tracking_links(self):
        with patch.object(scanner.requests, 'get', return_value=response(100)):
            articles = scanner.fetch_feed({'name': 'Other', 'url': URL, 'category': 'Blog'}, retries=0)
        self.assertEqual(len(articles), 20)
        self.assertEqual(articles[0]['link'], 'https://www.bestblogs.dev/article/0?utm_source=rss&utm_medium=feed')

    def test_repeated_scan_with_changed_utm_is_idempotent_and_skips_daily_stats(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'test.db'
            conn = init_db(db)
            conn.execute("INSERT INTO daily_stats (date, new_articles) VALUES ('2026-09-18', 123)")
            conn.commit()
            conn.close()
            with patch.object(scanner, 'SOURCES', [SOURCE]), \
                 patch.object(scanner, 'get_db', side_effect=lambda: sqlite3.connect(db)), \
                 patch.object(scanner.requests, 'get', side_effect=[response(100), response(100, campaign='changed')]):
                first = scanner.run(skip_stats=True)
                second = scanner.run(skip_stats=True)
            self.assertEqual(first['new_articles'], 100)
            self.assertEqual(second['new_articles'], 0)
            with closing(sqlite3.connect(db)) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0], 100)
                self.assertEqual(conn.execute('SELECT date, new_articles FROM daily_stats').fetchall(), [('2026-09-18', 123)])
                self.assertEqual(conn.execute('SELECT name, article_count_last, consecutive_failures FROM sources').fetchall(), [('BestBlogs', 100, 0)])


if __name__ == '__main__':
    unittest.main()
