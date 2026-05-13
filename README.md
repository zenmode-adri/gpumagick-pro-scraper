# GPUMagick Pro Scraper 🚀

[🇺🇸 English](#english) | [🇪🇸 Español](#español)

---

<a name="english"></a>
## 🇺🇸 English Version

### 🎯 The Goal: Finding the best Price/Performance combo
This project was born from a simple question: **What is the best CPU and GPU combo for the price?** Instead of relying on old reviews or guessing, I built this tool to collect real benchmark data from GPUMagick and compare it with current market prices.

It’s a technical but practical project created with AI assistance to solve a specific problem: finding out exactly how many FPS you get for every Euro spent.

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
Este proyecto nació de una pregunta sencilla: **¿Cuál es el mejor combo de procesador y gráfica por su precio?** En lugar de adivinar o mirar reviews antiguas, creé esta herramienta para recoger datos reales de GPUMagick y compararlos con los precios actuales del mercado.

Es un proyecto técnico pero práctico, hecho con ayuda de IA para resolver un problema concreto: saber exactamente cuántos FPS obtienes por cada euro invertido.

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
