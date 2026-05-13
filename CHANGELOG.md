# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-05-13

### 🧱 Arquitectura y Refactorización
- **Modularización Total:** Se ha fragmentado la aplicación monolítica `app.py` en una estructura de páginas (`pages/`) y utilidades (`utils/`).
- **Navegación Nativa:** Implementación de `st.navigation` para una gestión de páginas más robusta y limpia.
- **Utilidades Compartidas:** Centralización de lógica de UI, datos y gráficos para eliminar redundancia.

### ⚙️ Núcleo del Scraper
- **Tipado de Fechas Real:** Conversión de `submitted_date` de String a `datetime` de Python. Permite análisis temporales precisos en SQL.
- **Circuit Breaker (Escudo de Red):** Mecanismo de seguridad que detiene el scraper tras 10 errores 429 (Rate Limit) consecutivos o 20 errores generales.
- **Feedback en UI:** Notificaciones visuales críticas en el dashboard cuando el Circuit Breaker se activa.
- **Logging Profesional:** Sustitución de `print` por el módulo `logging` con niveles de severidad.

### 🎨 UI/UX
- **Avisos Críticos:** Alertas de color en el dashboard para estados de error de red.
- **Estética Pulida:** Mejoras menores en el CSS global para mantener la coherencia "Pro-Dev".

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
