# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-17

### Added
- Apple App Store review scraper using the public iTunes RSS feed (no auth required), covering 16 broker brands.
- AWS Bedrock (Claude) based AI review categorization with sentiment + topic tagging and automatic retry of unresolved rows.
- Interactive CLI menu (`main.py`) to run the scraper and the AI tagger.
- CSV output written to `output/`.
- Smoke tests for the App Store URL builder.
