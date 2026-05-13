# GPUMagick Pro Scraper 🚀

[🇺🇸 English](#english) | [🇪🇸 Español](#español)

---

<a name="english"></a>
## 🇺🇸 English Version

### 🎯 The Goal: Finding the best Price/Performance combo
This project was born from a simple question: **What is the best CPU and GPU combo for the price?** I wanted to have my own dataset to analyze because the GPUMagick website only shows the last 100 submissions in its public view, which makes it difficult to see long-term trends or compare less common hardware.

I built this tool to collect data from thousands of pages to build a more comprehensive personal database. I chose FurMark as the main data source because, even though it's often debated for creating unrealistic loads that a GPU might never see in real use, I personally find it to be an interesting baseline. It is also one of the most frequent benchmarks available on the site, allowing me to build a much larger dataset. I'm aware it's heavily **GPU-bound**, but it serves its purpose for comparing how different CPUs behave under a specific, extreme stress scenario.

### 🛠️ What’s under the hood?
- **Fast Data Collection:** Uses `asyncio` and `aiohttp` to grab data efficiently.
- **Visual Dashboard:** A Streamlit interface to filter, compare, and see rankings.
- **SQLite Database:** Keeps all hardware records organized and easy to query.
- **Ethical Scraping:** Pre-configured with a 10s delay to respect the website's rules.

### 🚀 Quick Start
1. **Prerequisites:** Python 3.9+
2. **Install Dependencies:**
   ```bash
   pip install streamlit pandas plotly aiohttp aiosqlite psutil
   ```
3. **Run Application:**
   ```bash
   streamlit run app.py
   ```
   *Note: The app will typically open automatically in your browser at `http://localhost:8501`.*

---

<a name="español"></a>
## 🇪🇸 Versión en Español

### 🎯 El Objetivo: Encontrar el mejor combo Calidad/Precio
Este proyecto nació de una pregunta sencilla: **¿Cuál es el mejor combo de procesador y gráfica por su precio?** Quería tener mis propios datos para analizar porque la web de GPUMagick solo muestra los últimos 100 resultados en su vista pública, lo que hace difícil ver tendencias a largo plazo o comparar hardware menos común.

Creé esta herramienta para recoger datos de miles de páginas y construir una base de datos personal más completa. Elegí FurMark como fuente principal porque, aunque mucha gente lo critica por generar cargas poco realistas que la gráfica nunca soportará en un uso normal, personalmente me parece un punto de referencia interesante. Además, es uno de los benchmarks más frecuentes en la web, lo que me ha permitido recolectar un volumen de datos mucho mayor. Soy consciente de que es muy **GPU-bound**, pero cumple su función para comparar cómo se comportan diferentes CPUs bajo un escenario de estrés específico y extremo.

### 🛠️ ¿Qué hay detrás de esto?
- **Extracción Eficiente:** Usa `asyncio` para recoger datos de forma rápida y organizada.
- **Panel Visual:** Una interfaz en Streamlit para filtrar, comparar y ver el ranking de piezas.
- **Base de Datos SQLite:** Mantiene todos los registros ordenados y listos para consultar.
- **Scraping Ético:** Configurado con un delay de 10s para respetar las normas de la web.

### 🚀 Guía de Inicio Rápido
1. **Requisitos:** Python 3.9+
2. **Instalación:**
   ```bash
   pip install streamlit pandas plotly aiohttp aiosqlite psutil
   ```
3. **Ejecución:**
   ```bash
   streamlit run app.py
   ```
   *Nota: La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`.*

---
*Project created to find the best hardware value / Proyecto creado para encontrar el mejor valor en hardware.*

## 📸 Visual Showcase / Vista Previa

| Main Dashboard | Data Analysis | Builds Ranking |
| :---: | :---: | :---: |
| ![Main UI](assets/screenshots/shot_final.png) | ![Analysis](assets/screenshots/shot_analysis.png) | ![Builds](assets/screenshots/shot_builds.png) |

> *Note: UI designed for a clean, technical look / Interfaz diseñada con una estética técnica y limpia.*
