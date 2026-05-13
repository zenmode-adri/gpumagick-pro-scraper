# Arquitectura y Convenciones: GPUMagick Pro (Scraper)

Este documento resume la estructura y decisiones técnicas del proyecto de scraping de `gpumagick.com`. Sirve como memoria de contexto para futuras interacciones de IA, reduciendo el consumo de tokens y evitando análisis redundantes.

## 🧱 Arquitectura del Proyecto

El proyecto ha sido refactorizado desde un monolito basado en hilos a una **Arquitectura Modular Asíncrona**.

### 1. Núcleo de Scraping (`/scraper/`)
*   **`network.py`**: Cliente HTTP asíncrono basado en `aiohttp`. Maneja `asyncio.Semaphore` para limitar la concurrencia, rotación de User-Agents y control de "Delay Adaptativo" (frente a errores 429).
*   **`parser.py`**: Motor de extracción de datos en HTML utilizando Regex puras. Convierte el HTML bruto en objetos limpios.
*   **`models.py`**: Define la clase de datos estructurada `GpuScore` usando `@dataclass`.
*   **`db.py`**: Gestor de persistencia asíncrono utilizando `aiosqlite`. Escribe directamente en `gpumagick.db`.
*   **`core.py`**: Orquestador principal (`ScraperOrchestrator`). Coordina los workers asíncronos, la fase de *probing* (detección del último ID) y gestiona la escritura atómica del archivo de telemetría `status.json`.

### 2. Interfaces
*   **`cli.py`**: Punto de entrada por línea de comandos para uso *headless*.
*   **`app.py`**: Aplicación web frontend construida con Streamlit y Plotly.

## 🎨 Diseño y UI (`app.py`)

*   **Estética Radical (Terminal/Dark Dashboard):** Se utiliza CSS fuertemente modificado inyectado vía `st.markdown`. Se ha ocultado toda la cabecera, pie de página y botones estándar de Streamlit.
*   **Fuentes:** 'Inter' para texto general y 'JetBrains Mono' para componentes técnicos y botones.
*   **Colores Principales:** Fondos oscuros (`#0d1117`, `#161b22`) y acentos de terminal (verde neón `#2ea043`, rojo `#da3633`).
*   **Componentes Clave:** 
    *   Uso de `st.container(border=True)` para simular "tarjetas" (cards).
    *   Botones de acción (Execute/Stop) con animaciones CSS (hover, scale, glow).

## ⚙️ Flujos Críticos a Recordar

### Sincronización UI - Proceso (Telemetría en Vivo)
El mayor desafío resuelto en este proyecto fue la comunicación entre Streamlit y el proceso de scraping asíncrono sin bloquear la web.
1.  **Escritura Atómica:** El orquestador escribe su estado en un archivo temporal y usa `os.rename()` para reemplazar `status.json`. Esto evita que Streamlit lea archivos JSON a medias y cause errores de decodificación.
2.  **Detección por PID:** Para evitar "motores huérfanos" que corrompan la telemetría, el proceso de scraping inscribe su PID de Windows en `status.json`. Streamlit (usando `psutil`) verifica activamente si este PID existe antes de permitir arrancar un nuevo proceso.
3.  **Botón Purge:** La UI incluye una herramienta de sistema que hace un barrido de procesos del SO usando `psutil` para matar brutalmente cualquier hilo que coincida con `cli.py`.

### Fase de Sondeo (Probing)
El scraper nunca asume que el usuario introdujo el "último ID" correcto. Al arrancar, el orquestador entra en estado `probing` y escanea rangos superiores (hasta +30,000) buscando las últimas subidas. Streamlit muestra un "spinner" durante esta fase antes de comenzar a contar el progreso.

## 📝 Directrices para Futuros Cambios

1.  **NO usar UI plana de Streamlit:** Cualquier nuevo componente en `app.py` debe envolverse en `st.container(border=True)` o adaptarse al estilo CSS global para no romper la estética "Pro-Dev".
2.  **Manejo de Errores Asíncronos:** Las modificaciones en `core.py` y `network.py` no deben bloquear el `EventLoop`. Nunca usar `time.sleep()` dentro de la capa `scraper/`, siempre `asyncio.sleep()`.
3.  **Base de Datos vs CSV:** La persistencia primaria es **SQLite** (`gpumagick.db`). Ya no dependemos de exportaciones en CSV en el flujo de trabajo principal. Cualquier análisis debe consultarse mediante SQL (a través de pandas `read_sql_query`).