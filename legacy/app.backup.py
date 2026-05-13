#!/usr/bin/env python3
"""
GPU Magick — Streamlit UI
"""
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mGKHJABCDEF]')

def parse_log_stats(log_text: str) -> dict:
    stats = {}
    for line in reversed(log_text.splitlines()):
        line = ANSI_RE.sub("", line).strip()
        if "Velocidad:" in line and "vel" not in stats:
            m = re.search(r"Velocidad:\s*([\d.]+)", line)
            if m: stats["vel"] = m.group(1)
        if "ETA:" in line and "eta" not in stats:
            m = re.search(r"ETA:\s*(\S+)", line)
            if m: stats["eta"] = m.group(1)
        if "Encontrados:" in line and "encontrados" not in stats:
            m = re.search(r"Encontrados:\s*(\d+)", line)
            if m: stats["encontrados"] = m.group(1)
        if "IDs revisados:" in line and "revisados" not in stats:
            m = re.search(r"IDs revisados:\s*([\d,]+)\s*/\s*([\d,]+)", line)
            if m: stats["revisados"] = m.group(1); stats["total_ids"] = m.group(2)
        if len(stats) >= 5:
            break
    return stats

st.set_page_config(page_title="GPU Magick", page_icon="🎮", layout="wide")

SCRIPT = Path(__file__).parent / "scrape_gpumagick_v14_1.py"
PYTHON = sys.executable


# ─── NAVEGACIÓN ──────────────────────────────────────────────────────────────
page = st.sidebar.radio("Navegación", ["🔍 Scraping", "📊 Análisis", "💶 Builds"])


# ─── SCRAPING ────────────────────────────────────────────────────────────────
if page == "🔍 Scraping":
    st.header("🔍 Scraping")

    with st.expander("Configuración", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.subheader("GPU")
            gpu_filter  = st.text_input("Filtro GPU", "RX 580")
            filter_mode = st.selectbox("Modo filtro", ["substring", "exact", "regex"])
            bench_types = st.multiselect(
                "Benchmarks",
                ["FurMark (GL)", "FurMark (VK)"],
                default=["FurMark (GL)"],
            )

        with c2:
            st.subheader("Rango de IDs")
            start_id = st.number_input("Start ID (más reciente)", value=2625523, step=1000, format="%d")
            end_id   = st.number_input("End ID (más antiguo)",    value=2125523, step=1000, format="%d")
            stride   = st.number_input("Stride (1 = todos)", value=1, min_value=1)

        with c3:
            st.subheader("Rendimiento")
            workers      = st.number_input("Workers",        value=8,    min_value=1, max_value=20)
            delay        = st.number_input("Delay (s)",      value=0.4,  min_value=0.1, step=0.1)
            max_results  = st.number_input("Max resultados", value=2000, step=100, format="%d")
            output_csv   = st.text_input("Archivo CSV salida", "gpumagick_scores.csv")
            check_robots = st.checkbox("Respetar robots.txt (fuerza 10s delay)", value=False)

    # ── Botones ──
    running = st.session_state.get("running", False)
    proc    = st.session_state.get("proc")

    col_start, col_stop, _ = st.columns([1, 1, 4])
    with col_start:
        start_clicked = st.button("🚀 Iniciar", disabled=running, use_container_width=True)
    with col_stop:
        stop_clicked = st.button("⏹ Parar", disabled=not running, use_container_width=True)

    if start_clicked and not running:
        cmd = [
            PYTHON, str(SCRIPT),
            "--start-id",        str(int(start_id)),
            "--end-id",          str(int(end_id)),
            "--stride",          str(int(stride)),
            "--workers",         str(int(workers)),
            "--delay",           str(delay),
            "--max-results",     str(int(max_results)),
            "--gpu-filter",      *gpu_filter.split(),
            "--gpu-filter-mode", filter_mode,
            "--output",          output_csv,
            "--no-color",
            "--auto-export-every", "25",
        ]
        if bench_types:
            cmd += ["--benchmark-type"] + bench_types
        if not check_robots:
            cmd.append("--no-check-robots-txt")

        log_fh = open("scraper.log", "w", encoding="utf-8")
        proc   = subprocess.Popen(cmd, stdout=log_fh, stderr=log_fh)

        st.session_state.update({
            "proc":       proc,
            "log_fh":     log_fh,
            "output_csv": output_csv,
            "start_time": time.time(),
            "running":    True,
        })
        st.rerun()

    if stop_clicked and running and proc:
        proc.terminate()
        if fh := st.session_state.get("log_fh"):
            fh.close()
        st.session_state["running"] = False
        st.rerun()

    # Si el proceso terminó solo, actualizar estado
    if running and proc and proc.poll() is not None:
        if fh := st.session_state.get("log_fh"):
            fh.close()
        st.session_state["running"] = False
        running = False

    # ── Estado + stats del log ──
    if running:
        st.info("⏳ Scraping en curso… la tabla se actualiza cada 3 segundos.")
        log_path = Path("scraper.log")
        if log_path.exists():
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            s = parse_log_stats(log_text)
            if s:
                l1, l2, l3, l4 = st.columns(4)
                l1.metric("Encontrados", s.get("encontrados", "—"))
                l2.metric("IDs revisados", s.get("revisados", "—"))
                l3.metric("Velocidad", f"{s.get('vel', '—')} IDs/s")
                l4.metric("ETA", s.get("eta", "—"))
    elif st.session_state.get("start_time"):
        st.success("✅ Completado (o parado manualmente)")

    # ── Resultados en vivo ──
    csv_path = Path(st.session_state.get("output_csv", "gpumagick_scores.csv"))

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            df = pd.DataFrame()

        if not df.empty:
            elapsed = time.time() - st.session_state.get("start_time", time.time())

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Resultados encontrados", len(df))
            m2.metric("GPUs distintas", df["gpu"].nunique() if "gpu" in df.columns else "-")
            m3.metric("Tiempo transcurrido", f"{int(elapsed // 60)}m {int(elapsed % 60)}s")
            score_num = pd.to_numeric(df.get("score", pd.Series()), errors="coerce")
            m4.metric("Score mediano", int(score_num.median()) if not score_num.empty else "-")

            if "gpu" in df.columns:
                st.subheader("Distribución por GPU")
                st.bar_chart(df["gpu"].value_counts())

            st.subheader("Últimos 100 resultados")
            st.dataframe(df.tail(100), use_container_width=True)

            with st.expander("Ver log del scraper"):
                log_path = Path("scraper.log")
                if log_path.exists():
                    st.code(log_path.read_text(encoding="utf-8", errors="replace")[-3000:])

    # Auto-refresh cada 3s mientras corre
    if running:
        time.sleep(3)
        st.rerun()


# ─── ANÁLISIS ────────────────────────────────────────────────────────────────
elif page == "📊 Análisis":
    st.header("📊 Análisis")

    # Carga de datos
    uploaded = st.file_uploader("Cargar CSV", type="csv")
    default_csv = Path("gpumagick_scores.csv")

    if uploaded:
        df = pd.read_csv(uploaded)
    elif default_csv.exists():
        df = pd.read_csv(default_csv)
        st.caption(f"Cargado automáticamente: {default_csv} ({len(df)} filas)")
    else:
        st.warning("No hay datos. Primero haz un scraping o sube un CSV.")
        st.stop()

    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["fps"]   = pd.to_numeric(df["fps"],   errors="coerce")
    df = df.dropna(subset=["score"])

    # Filtros
    with st.sidebar:
        st.subheader("Filtros")
        gpus      = st.multiselect("GPU",       sorted(df["gpu"].dropna().unique()),       default=sorted(df["gpu"].dropna().unique())[:3])
        benches   = st.multiselect("Benchmark", sorted(df["benchmark_type"].dropna().unique()), default=list(df["benchmark_type"].dropna().unique()))
        score_rng = st.slider("Rango score", int(df["score"].min()), int(df["score"].max()),
                              (int(df["score"].min()), int(df["score"].max())))

    fdf = df.copy()
    if gpus:
        fdf = fdf[fdf["gpu"].isin(gpus)]
    if benches:
        fdf = fdf[fdf["benchmark_type"].isin(benches)]
    fdf = fdf[fdf["score"].between(*score_rng)]

    if fdf.empty:
        st.warning("Sin datos con los filtros actuales.")
        st.stop()

    # Métricas globales
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Scores",        len(fdf))
    m2.metric("GPUs",          fdf["gpu"].nunique())
    m3.metric("CPUs únicos",   fdf["cpu"].nunique())
    m4.metric("Score mediano", int(fdf["score"].median()))

    # Stats por CPU
    st.subheader("Scores por CPU")
    cpu_stats = (
        fdf.groupby("cpu")["score"]
        .agg(Muestras="count", Mediana="median", Media="mean", Desv="std", Mínimo="min", Máximo="max")
        .round(0)
        .astype({"Muestras": int})
        .sort_values("Mediana", ascending=False)
        .reset_index()
    )
    cpu_stats = cpu_stats.rename(columns={"cpu": "CPU"})
    cpu_stats["⚠️"] = cpu_stats["Muestras"].apply(lambda x: "⚠️ pocas muestras" if x < 3 else "")
    st.dataframe(cpu_stats, use_container_width=True, height=350)

    # Gráfico mediana por CPU (top 20)
    st.subheader("Mediana de score por CPU (top 20)")
    top20 = cpu_stats.head(20).set_index("CPU")["Mediana"]
    st.bar_chart(top20)

    # Outliers globales (>2σ de la media)
    mean, std = fdf["score"].mean(), fdf["score"].std()
    outliers = fdf[((fdf["score"] - mean).abs() > 2 * std)]
    if not outliers.empty:
        with st.expander(f"⚠️ Outliers detectados ({len(outliers)}) — scores a >2σ de la media"):
            st.dataframe(outliers[["score_id", "cpu", "gpu", "score", "benchmark_type", "submitted_date"]],
                         use_container_width=True)

    # Tabla completa
    with st.expander("Ver todos los datos"):
        st.dataframe(fdf, use_container_width=True)


# ─── BUILDS ──────────────────────────────────────────────────────────────────
elif page == "💶 Builds":
    st.header("💶 Builds — Score / €")

    uploaded = st.file_uploader("Cargar CSV", type="csv", key="builds_csv")
    default_csv = Path("gpumagick_scores.csv")

    if uploaded:
        df = pd.read_csv(uploaded)
    elif default_csv.exists():
        df = pd.read_csv(default_csv)
    else:
        st.warning("No hay datos. Primero haz un scraping o sube un CSV.")
        st.stop()

    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df = df.dropna(subset=["score", "cpu", "gpu"])

    # Selección de GPU
    gpu_sel = st.selectbox("GPU a comparar", sorted(df["gpu"].unique()))
    fdf = df[df["gpu"] == gpu_sel]

    # Stats por CPU para esa GPU
    cpu_stats = (
        fdf.groupby("cpu")["score"]
        .agg(Muestras="count", Mediana="median")
        .round(0).astype({"Muestras": int})
        .sort_values("Mediana", ascending=False)
        .reset_index()
        .rename(columns={"cpu": "CPU"})
    )

    st.caption(f"{len(cpu_stats)} CPUs encontrados con {gpu_sel}")

    # Precio de la GPU (fijo para todos los combos)
    gpu_price = st.number_input("Precio GPU (€)", min_value=0, value=80, step=5)

    # Tabla editable: usuario introduce precio por CPU
    st.subheader("Introduce el precio de cada CPU (€)")
    cpu_stats["Precio CPU (€)"] = 0
    cpu_stats["⚠️"] = cpu_stats["Muestras"].apply(lambda x: "⚠️" if x < 3 else "")

    edited = st.data_editor(
        cpu_stats[["CPU", "Muestras", "Mediana", "Precio CPU (€)", "⚠️"]],
        use_container_width=True,
        hide_index=True,
        column_config={"Precio CPU (€)": st.column_config.NumberColumn(min_value=0, step=5)},
    )

    # Calcular score/€ para los que tienen precio > 0
    priced = edited[edited["Precio CPU (€)"] > 0].copy()
    if not priced.empty:
        priced["Total (€)"]  = priced["Precio CPU (€)"] + gpu_price
        priced["Score/€"]    = (priced["Mediana"] / priced["Total (€)"]).round(2)
        priced["GPU"]        = gpu_sel
        resultado = priced[["CPU", "GPU", "Muestras", "Mediana", "Precio CPU (€)", "Total (€)", "Score/€", "⚠️"]] \
            .sort_values("Score/€", ascending=False)

        st.subheader("Ranking por Score / €")
        st.dataframe(resultado, use_container_width=True, hide_index=True)

        st.subheader("Score/€ por CPU")
        st.bar_chart(resultado.set_index("CPU")["Score/€"])
    else:
        st.info("Introduce el precio de al menos un CPU para ver el ranking.")
