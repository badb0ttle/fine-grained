import unittest

from scripts.pipeline.scorer import AUTHORITY, score_authority


class BestBlogsAuthorityTests(unittest.TestCase):
    def test_bestblogs_has_explicit_curated_source_authority(self):
        self.assertEqual(AUTHORITY["BestBlogs"], 70)
        self.assertEqual(score_authority("BestBlogs"), 0.70)


if __name__ == "__main__":
    unittest.main()
