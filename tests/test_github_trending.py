"""Regression tests for Trending HTML parsing; never access the database."""
import unittest
from unittest.mock import Mock, patch

from scripts.pipeline import github_trending


def card(repo="owner/agent", description="An agent", css="pr-4", before="", stars="123", forks="900", today="12"):
    return f'''<article class="Box-row">
      {before}<h2><a href="/{repo}"><span>owner /</span> repo</a></h2>
      <p class="{css}">{description}</p>
      <span itemprop="programmingLanguage">Python</span>
      <a href="/{repo}/stargazers"><svg></svg> {stars}</a>
      <a href="/{repo}/forks"><svg></svg> {forks}</a>
      <span class="float-sm-right"><svg></svg> {today} stars today</span>
    </article>'''


class FetchTrendingTests(unittest.TestCase):
    def fetch(self, html):
        response = Mock(text=html)
        with patch.object(github_trending.requests, "get", return_value=response), patch.object(
            github_trending, "get_db", side_effect=AssertionError("database forbidden")
        ):
            return github_trending.fetch_trending()

    def test_description_does_not_depend_on_spacing_classes(self):
        repos = self.fetch(card(repo="owner/tool", description="A large language model", css="col-9 color-fg-muted tmp-my-1 tmp-pr-4"))
        self.assertEqual([r["repo_full"] for r in repos], ["owner/tool"])
        self.assertEqual(repos[0]["description"], "A large language model")

    def test_last_article_survives_page_footer(self):
        repos = self.fetch('<main>' + card("owner/agent-one") + card("owner/agent-last") + '</main><footer>GitHub</footer>')
        self.assertEqual({r["repo_full"] for r in repos}, {"owner/agent-one", "owner/agent-last"})

    def test_repository_link_comes_from_heading_not_sponsor_link(self):
        repos = self.fetch(card(before='<a href="/sponsors/someone">Sponsor</a>'))
        self.assertEqual(repos[0]["repo_full"], "owner/agent")
        self.assertEqual(repos[0]["url"], "https://github.com/owner/agent")

    def test_stargazer_count_is_not_larger_fork_count(self):
        repos = self.fetch(card(stars="1,234", forks="9,876", today="1,001"))
        self.assertEqual(repos[0]["total_stars"], 1234)
        self.assertEqual(repos[0]["stars_today"], 1001)

    def test_description_decodes_entities_and_nested_text(self):
        repos = self.fetch(card(description='An <b>agent</b> &amp; LLM&#160;tool'))
        self.assertEqual(repos[0]["description"], "An agent & LLM tool")

    def test_article_class_order_and_quote_style_do_not_matter(self):
        html = card().replace('<article class="Box-row">', "<article data-x='1' class='extra Box-row'>")
        self.assertEqual([r["repo_full"] for r in self.fetch(html)], ["owner/agent"])

    def test_missing_star_count_does_not_fall_back_to_forks(self):
        html = card().replace('<a href="/owner/agent/stargazers"><svg></svg> 123</a>', '')
        self.assertEqual(self.fetch(html)[0]["total_stars"], 0)

    def test_heading_without_repository_link_is_skipped(self):
        html = card().replace('href="/owner/agent"', 'href="/login?return_to=/owner/agent"')
        self.assertEqual(self.fetch(html), [])

    def test_existing_filter_dedup_sort_limit_and_description_cap(self):
        html = card("owner/plain", description="A simple editor")
        html += card("owner/agent-0", today="0")
        html += ''.join(card(f"owner/agent-{i}", description="agent " + "x" * 550, today=str(i)) for i in range(32))
        repos = self.fetch(html)
        self.assertEqual(len(repos), 30)
        self.assertEqual([r["stars_today"] for r in repos], list(range(31, 1, -1)))
        self.assertEqual(len(repos[0]["description"]), 500)
        self.assertEqual(repos[0]["language"], "Python")

    def test_empty_page_returns_empty_list(self):
        self.assertEqual(self.fetch('<main>No repositories</main>'), [])


if __name__ == "__main__":
    unittest.main()
