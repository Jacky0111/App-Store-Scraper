import os
import time

import pandas as pd
import requests

OUTPUT_DIR = "output"


class AppStoreScraper:
    """Scrapes app reviews from the Apple App Store RSS feed."""

    max_pages = 10
    delay = 1.0

    def __init__(self, app_id, countries_list, platform, brand):
        """
        @param app_id: The Apple App Store application ID to fetch reviews for.
        @param countries_list: List of country codes to fetch reviews from.
        @param platform: Platform label used in the output filename (e.g. 'appstore').
        @param brand: Brand name used in the output filename.
        """
        self.app_id = app_id
        self.countries_list = countries_list
        self.platform = platform
        self.brand = brand
        self.output_csv = None
        self.all_reviews = []

    def run_scraper(self):
        """Fetch reviews for all configured countries and save them to CSV."""
        for country in self.countries_list:
            country_reviews = self.fetch_reviews_for_country(country)
            self.all_reviews.extend(country_reviews)

        self.save_to_csv()

    def fetch_reviews_for_country(self, country_code):
        """
        Fetch app reviews for a specific country by paginating the RSS feed.
        @param country_code: The country code to fetch reviews from.
        @return: List of dictionaries containing review data.
        """
        reviews = []

        for page in range(1, self.max_pages + 1):
            url = AppStoreScraper._build_review_url(country_code, page, self.app_id)
            print(f"Fetching {country_code.upper()} - page {page}... {url}")

            try:
                data = AppStoreScraper._get_json_response(url)
                if not data:
                    break

                # Skip the first entry, which is app info rather than a review.
                entries = data.get("feed", {}).get("entry", [])[1:]
                if not entries:
                    break

                for e in entries:
                    reviews.append({
                        "Date": e["updated"]["label"],
                        "Country": country_code.upper(),
                        "Rating": int(e["im:rating"]["label"]),
                        "Author": e["author"]["name"]["label"],
                        "Title": e["title"]["label"],
                        "Content": e["content"]["label"],
                    })

                time.sleep(self.delay)

            except Exception as err:
                print(f"❌ Error fetching {country_code} page {page}: {err}")
                continue

        return reviews

    def save_to_csv(self):
        """Save all fetched reviews to a CSV file under OUTPUT_DIR."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.output_csv = os.path.join(OUTPUT_DIR, f"{self.brand}_{self.platform}_reviews.csv")

        df = pd.DataFrame(self.all_reviews)
        df.to_csv(self.output_csv, index=False, encoding="utf-8-sig")

        print(f"\n✅ Completed. {len(df)} reviews saved to {self.output_csv}")

    @staticmethod
    def _build_review_url(country_code, page, app_id):
        """Build the iTunes RSS feed URL for a given country/page/app_id."""
        return f"https://itunes.apple.com/{country_code}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"

    @staticmethod
    def _get_json_response(url):
        """Perform a GET request and return the parsed JSON, or None on failure."""
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"⚠️  Skipping URL {url} (HTTP {response.status_code})")
            return None

        return response.json()
