import unittest

from scraper.app_store import AppStoreScraper


class AppStoreSmokeTests(unittest.TestCase):
    def test_build_review_url(self):
        url = AppStoreScraper._build_review_url("us", 2, "123456")
        self.assertEqual(
            url,
            "https://itunes.apple.com/us/rss/customerreviews/page=2/id=123456/sortby=mostrecent/json",
        )


if __name__ == "__main__":
    unittest.main()
