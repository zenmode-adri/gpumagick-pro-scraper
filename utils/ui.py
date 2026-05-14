import streamlit as st
import json
from pathlib import Path

STATUS_FILE = "status.json"
DB_PATH = "gpumagick.db"
CPU_PRICES_FILE = "cpu_prices.json"

def load_css():
    css_path = Path("assets/style.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

def page_header(title, subtitle=""):
    sub = f'<p class="page-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<h2 class="page-title">{title}</h2>{sub}', unsafe_allow_html=True)

def chip(label, kind="idle"):
    dot_cls = "dot pulse" if kind == "running" else "dot"
    return f'<span class="status-chip {kind}"><span class="{dot_cls}"></span>{label}</span>'

def load_cpu_prices():
    default_prices = {
        "Ryzen 5 3600": 75, "Ryzen 5 5600": 115,
        "Core i5-12400F": 125, "Core i3-12100F": 85,
        "Ryzen 7 5700X": 165, "Ryzen 5 2600": 45,
        "Core i7-4770": 40, "Xeon E5-2667 v2": 25,
    }
    if Path(CPU_PRICES_FILE).exists():
        with open(CPU_PRICES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return default_prices

def save_cpu_prices(d):
    with open(CPU_PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

# Traducciones centralizadas
T = {
    "EN": {
        "scraper": "Scraper", "analysis": "Analysis", "builds": "Builds",
        "scraper_sub": "Configure and launch the benchmark data collector",
        "analysis_sub": "Filter, explore and compare benchmark results by CPU",
        "builds_sub": "FPS/€ ranking per CPU+GPU combo with real aftermarket prices",
        "engine_cfg": "Engine Configuration", "target_gpu": "Target GPU",
        "bench_type": "Benchmark type", "start_id": "Start ID (Newest)",
        "end_id": "End ID (Oldest)", "workers": "Concurrent workers",
        "adv_opts": "Advanced options", "stride": "Stride", "max_res": "Max results",
        "delay": "Delay (s)", "execute": "Execute", "stop": "Stop scraper",
        "session": "Session", "checked": "Checked", "found": "Found",
        "hit_rate": "Hit rate", "speed": "Speed", "eta": "ETA", "skipped": "Skipped",
        "scrape_done": "Scrape complete",
        "no_session": "No active session", "no_session_sub": "Configure a target GPU and hit Execute to start collecting",
        "wait_scraper": "Waiting for scraper to start...",
        "db_records": "records in database", "filters": "Filters",
        "gpu": "GPU", "bench": "Benchmark", "resolution": "Resolution",
        "score_rng": "Score range", "samples": "Samples", "gpus": "GPUs", "cpus": "CPUs",
        "median_score": "Median score", "sort_by": "Sort by", "cpu_table": "CPU score table",
        "median_by_cpu": "Median score by CPU",
        "median_by_gpu": "Median score by GPU",
        "no_data": "No data available", "no_data_sub": "Run the scraper first, or import a .db / .csv file above",
        "gpu_price": "GPU Market Price (€)", "cpu_prices": "CPU Market Prices",
        "save_prices": "Save Prices",
        "top_cpus": "Top CPUs", "score_dist": "Score Distribution",
        "best_fps_eur": "Best FPS/€",
        "clear_status": "Clear Status", "kill_scraper": "Kill Scraper",
        "db": "DB", "killed": "Killed",
        "median_fps": "Median FPS", "total_cost": "Total Cost (€)", "priced_combos": "Priced combos",
        "select_gpu_prompt": "Select a GPU to see the ranking",
        "select_gpus_title": "Select one or more GPUs",
        "select_gpus_sub": "Choose the GPUs you want to compare",
        "no_data_filters": "No data for the current filters.",
        "circuit_breaker_warn": "The server temporarily blocked requests (429). The scraper stopped to protect your IP. Increase the delay or reduce workers.",
        "ethics_warn": "A 10s delay is recommended to respect the server. Lowering it may cause IP bans."
    },
    "ES": {
        "scraper": "Extractor", "analysis": "Análisis", "builds": "Ensambles",
        "scraper_sub": "Configura y lanza el colector de datos de benchmarks",
        "analysis_sub": "Filtra, explora y compara resultados por CPU",
        "builds_sub": "Ranking FPS/€ por combo CPU+GPU con precios de mercado",
        "engine_cfg": "Configuración del Motor", "target_gpu": "GPU Objetivo",
        "bench_type": "Tipo de Benchmark", "start_id": "ID Inicio (Nuevo)",
        "end_id": "ID Fin (Viejo)", "workers": "Hilos concurrentes",
        "adv_opts": "Opciones avanzadas", "stride": "Salto (Stride)", "max_res": "Máx resultados",
        "delay": "Retraso (s)", "execute": "Ejecutar", "stop": "Detener extractor",
        "session": "Sesión", "checked": "Revisados", "found": "Encontrados",
        "hit_rate": "Acierto", "speed": "Velocidad", "eta": "Tiempo rest.", "skipped": "Saltados",
        "scrape_done": "Extracción completada",
        "no_session": "Sin sesión activa", "no_session_sub": "Configura una GPU y pulsa Ejecutar para empezar",
        "wait_scraper": "Esperando que el extractor arranque...",
        "db_records": "registros en base de datos", "filters": "Filtros",
        "gpu": "GPU", "bench": "Benchmark", "resolution": "Resolución",
        "score_rng": "Rango de puntos", "samples": "Muestras", "gpus": "GPUs", "cpus": "CPUs",
        "median_score": "Puntuación media", "sort_by": "Ordenar por", "cpu_table": "Tabla de CPUs",
        "median_by_cpu": "Puntuación media por CPU", "median_by_gpu": "Puntuación media por GPU",
        "no_data": "Sin datos disponibles", "no_data_sub": "Lanza el extractor primero o importa un archivo .db / .csv",
        "gpu_price": "Precio de Mercado GPU (€)", "cpu_prices": "Precios de Mercado CPU",
        "save_prices": "Guardar Precios",
        "top_cpus": "Top CPUs", "score_dist": "Distribución de Puntos",
        "best_fps_eur": "Mejor FPS/€",
        "clear_status": "Limpiar Estado", "kill_scraper": "Matar Extractor",
        "db": "BD", "killed": "Se detuvieron",
        "median_fps": "FPS Medios", "total_cost": "Coste Total (€)", "priced_combos": "Combos valorados",
        "select_gpu_prompt": "Selecciona una GPU para ver el ranking",
        "select_gpus_title": "Selecciona una o más GPUs",
        "select_gpus_sub": "Elige las GPUs que quieres comparar",
        "no_data_filters": "No hay datos para los filtros actuales.",
        "circuit_breaker_warn": "El servidor ha bloqueado temporalmente las peticiones (429). El scraper se detuvo para proteger tu IP. Aumenta el delay o reduce los hilos.",
        "ethics_warn": "Se recomienda un delay de 10s por ética. Bajarlo puede causar bloqueos de IP."
    }
}

def t(key):
    lang = st.session_state.get("lang", "EN")
    return T[lang].get(key, key)
