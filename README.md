# GPUMagick Pro Scraper 🚀

[🇺🇸 English](#english) | [🇪🇸 Español](#español)

---

<a name="english"></a>
## 🇺🇸 English Version

### 🎯 The Goal: Finding the best Price/Performance combo
This project was born from a simple question: **What is the best CPU and GPU combo for the price?** Instead of relying on old reviews or guessing, I built this tool to collect real data from thousands of benchmark pages on GPUMagick and compare it with current market prices.

I chose FurMark as the main data source because it's the most consistent and widely available on the site. I'm aware it's a heavily **GPU-bound** benchmark and might not be the most "realistic" for gaming, but it serves as a solid baseline for comparing how different CPUs affect a specific GPU's performance.

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

---

<a name="español"></a>
## 🇪🇸 Versión en Español

### 🎯 El Objetivo: Encontrar el mejor combo Calidad/Precio
Este proyecto nació de una pregunta sencilla: **¿Cuál es el mejor combo de procesador y gráfica por su precio?** En lugar de adivinar o mirar reviews antiguas, creé esta herramienta para recoger datos de miles de páginas de GPUMagick y compararlos con los precios actuales del mercado.

Elegí FurMark como fuente principal porque es el dato más común y consistente en la web. Soy consciente de que es un benchmark muy **GPU-bound** (depende casi todo de la gráfica) y quizá no es el más "realista" para juegos, pero me sirve como una base sólida para comparar cómo diferentes CPUs afectan al rendimiento de una misma GPU.

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

---
*Project created to find the best hardware value / Proyecto creado para encontrar el mejor valor en hardware.*

## 📸 Visual Showcase / Vista Previa

| Main Dashboard | Data Analysis | Builds Ranking |
| :---: | :---: | :---: |
| ![Main UI](assets/screenshots/shot_final.png) | ![Analysis](assets/screenshots/shot_analysis.png) | ![Builds](assets/screenshots/shot_builds.png) |

> *Note: UI designed for a clean, technical look / Interfaz diseñada con una estética técnica y limpia.*
