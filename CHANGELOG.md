# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-05-13

### Added
- **Dual-Range Checkpoint System**: New persistence logic in `scraper/db.py` to track min/max explored IDs, preventing redundant scanning of empty ranges.
- **SQLModel Integration**: Migrated data models to `sqlmodel` for better ORM support and easier database migrations.
- **Enhanced Network Stealth**: Added more modern User-Agents and implemented a random jitter (±20%) to request delays to bypass anti-bot detections.
- **Assets Directory**: Created `assets/style.css` to store UI styling separately from the application logic.

### Changed
- **Async Orchestrator Refactor**: Replaced the batch-based processing with a more efficient `asyncio.Queue` and worker pool architecture in `scraper/core.py`.
- **UI Decoupling**: Moved heavy CSS blocks out of `app.py` into external stylesheets, improving code readability and maintainability.
- **Database Manager**: Refactored `DatabaseManager` to use SQLAlchemy's async sessions via SQLModel.

### Fixed
- Improved handling of 429 (Rate Limit) errors with a more aggressive exponential backoff.
- Fixed atomic writing of `status.json` to prevent Streamlit from reading corrupted telemetry data.

## [1.0.0] - 2026-04-20
- Initial modular release.
- Basic async scraping capabilities.
- SQLite persistence.
- Streamlit dashboard.
