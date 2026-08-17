# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project purpose

Apple App Store review scraper (iTunes RSS feed, no auth) plus an optional AWS Bedrock (Claude) AI review categorizer. CSV in, CSV out — no database, no cloud storage backend.

## Layout

- `main.py` — interactive CLI menu (Scraper / AI Tagger / quit). This is the only entrypoint.
- `scraper/app_store.py` — `AppStoreScraper`. Paginates the iTunes RSS feed per country, writes `output/{brand}_appstore_reviews.csv`. Keep this module free of AWS/Bedrock dependencies.
- `ai_tagger/categorize.py` — Bedrock-based async categorization (`categorize_reviews_async`, `retry_unknowns`). AWS credential checks happen lazily via `get_bedrock_credentials()`, not at import time, so `python main.py` never crashes just because `.env` is unset.
- `configs/app_id.py` + `configs/countries.py` — single source of truth for brand → App Store ID / storefront countries. Add new brands here, not inline in `main.py`.
- `configs/topic_list.py` + `configs/templates.py` — categorization taxonomy and LLM prompt. Keep these in sync — every `[Lvl1, Lvl2]` pair used in `templates.py`'s topic definitions must exist in `topic_list.py`.
- `output/` — gitignored CSVs (`.gitkeep` is tracked so the directory exists on clone).
- `tests/test_smoke.py` — stdlib `unittest`, no extra test framework dependency.

## Running

```bash
pip install -r requirements.txt
python main.py
```

Testing: `python -m unittest discover tests`

## Conventions

- CSV schema from the scraper is fixed: `Date, Country, Rating, Author, Title, Content`. Categorization appends `Type, Lvl1 Category, Lvl2 Category`. Don't rename these columns without updating both `ai_tagger/categorize.py`'s `key_names` usage and the README.
- Don't reintroduce the runtime `pip install` auto-dependency pattern from the original reference scripts — all dependencies belong in `requirements.txt`.
- Do not add Google Play, Playwright, Apify, S3, or Lark integration — these were deliberately descoped for this project. If broader multi-platform scraping is ever needed, that belongs in a separate project.
