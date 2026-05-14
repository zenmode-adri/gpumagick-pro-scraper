# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2026-05-14

### ⚡ Rendimiento
- **Cache de datos:** `load_data()` ahora usa `@st.cache_data(ttl=30)` — elimina reconsultas a la DB en cada render de Streamlit.
- **Eliminado DuckDB como capa intermedia:** Reemplazado por `sqlite3` directo. DuckDB no aportaba beneficio con `SELECT *` sin agregaciones en SQL.
- **Índices de base de datos:** Añadidos índices en `gpu+benchmark_type`, `cpu` y `resolution` para queries rápidas con datasets grandes.
- **WAL mode activado:** `PRAGMA journal_mode=WAL` en la inicialización de la DB — el scraper y Streamlit ya no se bloquean entre sí al acceder simultáneamente.

### 🔒 Seguridad y Robustez
- **Escritura atómica real de status.json:** Reemplazado `os.remove + os.rename` por `os.replace()` — atómico en Windows, elimina la race condition.
- **Validación de valores parseados:** Score negativo → 0, FPS fuera de rango (>50.000 o <0) → 0.0, CPU vacío → registro descartado con log.
- **Precio GPU por defecto eliminado:** El valor por defecto de 80 € ha sido reemplazado por 0. GPUs sin precio explícito quedan excluidas del ranking FPS/€.
- **Filtro doble en ranking:** Ahora se requiere `cpu_price > 0` **y** `gpu_price > 0` para aparecer en el ranking de builds.

### 🧹 Calidad de Código
- **Constantes de tier extraídas:** `TIER_TOP = 0.97` y `TIER_HIGH = 0.92` definidas en `utils/ui.py` e importadas en `pages/analysis.py`.
- **`make_grouped_bar()` eliminada:** Función sin uso removida de `utils/charts.py`.
- **Errores silenciosos corregidos:** `get_seen_ids()` y workers ahora loguean excepciones con `exc_info=True`.
- **`load_cpu_prices()` robusta:** Muestra `st.warning` si `cpu_prices.json` está corrupto en lugar de fallar silenciosamente.
- **`t()` con log de claves ausentes:** Claves de traducción faltantes ahora se registran en el log.
- **`jump_cpu` documentado:** Comentario añadido en `pages/builds.py` explicando el origen del valor desde `pages/analysis.py`.

### 🛠️ DX
- **`requirements.txt` corregido:** Añadidos `sqlalchemy[asyncio]` y `filelock` que faltaban.
- **`.gitignore` actualizado:** Añadidos patrones `*.tmp.*` y `status.json.lock`.

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
