# App Store Scraper

A runnable Apple App Store review scraper with optional AI-based review categorization (AWS Bedrock / Claude). Google Play is explicitly out of scope for this project.

## Features

- Scrapes App Store reviews via the public iTunes RSS feed — no authentication or API keys required.
- Preconfigured for 16 broker/trading app brands (see `configs/app_id.py` and `configs/countries.py`).
- Optional AI Tagger: categorizes scraped reviews by sentiment (`Good`/`Bad`/`Neutral`) and topic (e.g. `Payment`, `Customer Service`, `Trading Experience`) using Claude via AWS Bedrock.
- Interactive CLI menu — no flags to memorize.
- Output as plain CSV files under `output/`.

## Requirements

- Python 3.9+
- An AWS account with Bedrock access (only needed for the AI Tagger — the scraper works with zero setup)

## Setup

```bash
pip install -r requirements.txt
```

If you want to use the AI Tagger, copy `.env.example` to `.env` and fill in your AWS credentials:

```bash
cp .env.example .env
```

```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-2
```

## Usage

```bash
python main.py
```

### 1. Scraper

Pick a brand from the menu. The scraper fetches reviews for every configured storefront country and writes them to `output/{brand}_appstore_reviews.csv` with columns:

| Date | Country | Rating | Author | Title | Content |
|------|---------|--------|--------|-------|---------|

### 2. AI Tagger

Pick a CSV previously produced by the scraper. Each review is sent to Claude via AWS Bedrock and categorized. The output file (`*_categorized.csv`) adds three columns:

| Type | Lvl1 Category | Lvl2 Category |
|------|----------------|----------------|

Rows that fail to categorize are marked `Unknown` and automatically retried (up to 10 passes). If AWS credentials aren't configured, the menu prints a clear error and returns you to the main menu instead of crashing.

## Architecture

```
main.py                  interactive CLI entrypoint
scraper/app_store.py      AppStoreScraper — iTunes RSS pagination + CSV export
ai_tagger/categorize.py    AWS Bedrock categorization, batching, and retry logic
configs/                  brand -> app ID / country mappings, topic taxonomy, prompt template
output/                   generated CSVs (gitignored)
tests/                    smoke tests
```

## Supported brands

XM, Vantage, Exness, Deriv, AvaTrade, XTB, RoboForex, Hantec Markets, Interactive Brokers, CFI Financial, Capital.com, Plus500, ADSS, PU Prime, VT Markets, StarTrader.

## Testing

```bash
python -m unittest discover tests
```

## Out of scope

Google Play Store scraping is intentionally not supported by this project.
