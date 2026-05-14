import streamlit as st
import json
import time
import os
import psutil
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys
from utils.ui import t, chip, page_header, STATUS_FILE, DB_PATH
from utils.data import load_data
from utils.charts import make_bar

PYTHON = sys.executable
CLI_SCRIPT = "cli.py"

def is_engine_running():
    if Path(STATUS_FILE).exists():
        try:
            with open(STATUS_FILE) as f:
                stats = json.load(f)
            pid = stats.get("pid")
            if pid and psutil.pid_exists(pid):
                if "python" in psutil.Process(pid).name().lower():
                    return True
        except:
            pass
    return False

def show():
    page_header(t("scraper"), t("scraper_sub"))
    is_running = is_engine_running()

    with st.container(border=True):
        st.markdown(f'<p class="section-label">{t("engine_cfg")}</p>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        with c1:
            gpu_input = st.text_input(t("target_gpu"), "RX 580, GTX 1650", help="Separate multiple GPUs with commas (e.g. RX 580, GTX 1650)")
            bench_t = st.multiselect(t("bench_type"), ["FurMark (GL)", "FurMark (VK)"], default=["FurMark (GL)"])
        with c2:
            s_id = st.number_input(t("start_id"), value=2625523)
        with c3:
            e_id = st.number_input(t("end_id"), value=2125523)
        with c4:
            wrk = st.number_input(t("workers"), value=1, min_value=1, max_value=30)
            
        with st.expander(t("adv_opts")):
            a1, a2, a3 = st.columns(3)
            stride = a1.number_input(t("stride"), value=1, min_value=1)
            max_r  = a2.number_input(t("max_res"), value=10000)
            dly    = a3.number_input(t("delay"), value=10.0, step=0.5, min_value=0.1)
            if dly < 10.0:
                st.warning(t("ethics_warn"), icon="⚠️")

        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
        _, btn_col = st.columns([2, 1])
        with btn_col:
            if is_running:
                if st.button(t("stop"), use_container_width=True, key="btn_stop", type="primary"):
                    if Path(STATUS_FILE).exists():
                        try:
                            with open(STATUS_FILE) as f: s = json.load(f)
                            pid = s.get("pid")
                            if pid and psutil.pid_exists(pid): psutil.Process(pid).terminate()
                            s["status"] = "stopped"
                            with open(STATUS_FILE, "w") as f: json.dump(s, f)
                        except: pass
                    st.rerun()
            else:
                if st.button(t("execute"), use_container_width=True, key="btn_start", type="primary"):
                    if Path(STATUS_FILE).exists(): Path(STATUS_FILE).unlink()
                    gpus = [g.strip() for g in gpu_input.split(",") if g.strip()]
                    cmd = [PYTHON, CLI_SCRIPT, "--start-id", str(int(s_id)), "--end-id", str(int(e_id)), "--stride", str(int(stride)), "--max-results", str(int(max_r)), "--workers", str(int(wrk)), "--delay", str(dly), "--db", DB_PATH]
                    if gpus: cmd += ["--gpu-filter"] + gpus
                    if bench_t: cmd += ["--benchmark-types"] + bench_t
                    
                    import subprocess
                    subprocess.Popen(cmd, stdout=open("scraper.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                    st.toast(f"Scraper started ({len(gpus)} GPUs)")
                    time.sleep(0.5); st.rerun()

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    col_left, col_right = st.columns([1.1, 1.3])

    @st.fragment(run_every=2)
    def _scraper_status():
        _running = is_engine_running()
        if _running and not Path(STATUS_FILE).exists():
            with st.container(border=True):
                st.markdown(f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.75rem"><span style="font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--t2)">{t("session")}</span>{chip("INITIALIZING", "running")}</div>', unsafe_allow_html=True)
                st.caption(t("wait_scraper"))
            return
        if not Path(STATUS_FILE).exists() and not _running:
            with st.container(border=True):
                st.markdown(f'<div class="empty-state"><div class="empty-icon">◉</div><div class="empty-title">{t("no_session")}</div><div class="empty-sub">{t("no_session_sub")}</div></div>', unsafe_allow_html=True)
            return
        if not Path(STATUS_FILE).exists(): return

        stats = None
        for _ in range(3):
            try:
                with open(STATUS_FILE, encoding="utf-8") as f: stats = json.load(f)
                break
            except: time.sleep(0.1)
        if not stats: return

        remaining = stats['total_ids'] - stats['checked']
        eta_s = int(remaining / stats['speed']) if stats.get('speed', 0) > 0 else 0
        eta_str = f"{eta_s//3600}h {(eta_s%3600)//60}m" if eta_s > 0 else "---"
        hit_rate = f"{stats['found']/stats['checked']*100:.1f}%" if stats['checked'] > 0 else "---"
        status = stats['status']
        status_kind = "running" if status in ("running", "probing", "initializing") else "done" if status == "finished" else "error" if "crashed" in status else "idle"

        with st.container(border=True):
            st.markdown(f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.75rem"><span style="font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--t2)">{t("session")}</span>{chip(status.upper(), status_kind)}</div>', unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric(t("checked"), f"{stats['checked']:,}")
            m2.metric(t("found"), f"{stats['found']:,}")
            m3.metric(t("hit_rate"), hit_rate)
            m4, m5, m6 = st.columns(3)
            m4.metric(t("speed"), f"{stats.get('speed', 0):.1f} /s")
            m5.metric(t("eta"), eta_str)
            m6.metric(t("skipped"), f"{stats.get('skipped', 0):,}")

            if stats['total_ids'] > 0:
                pct = min(stats['checked'] / stats['total_ids'], 1.0)
                st.markdown(f'<p class="section-note" style="margin:.75rem 0 .25rem">{pct*100:.1f}% &nbsp;·&nbsp; {stats["checked"]:,} / {stats["total_ids"]:,}</p>', unsafe_allow_html=True)
                st.progress(pct)

            if status == "finished":
                st.success(t("scrape_done"))
            elif "crashed" in status:
                st.error(f"Crash: {status}")
                if "circuit breaker" in status.lower():
                    st.warning("⚠️ El servidor ha bloqueado temporalmente las peticiones (429). El scraper se detuvo para proteger tu IP. Aumenta el delay o reduce los hilos.", icon="🛑")

        df_live = load_data()
        if not df_live.empty:
            df_live["score"] = pd.to_numeric(df_live["score"], errors="coerce")
            df_live = df_live.dropna(subset=["score", "cpu"])
            tab1, tab2 = st.tabs([t("score_dist"), t("top_cpus")])
            with tab1:
                with st.container(border=True):
                    fig_h = px.histogram(df_live, x="score", nbins=40, template="plotly_dark", color_discrete_sequence=["#4ade80"])
                    fig_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#6868a0"), margin=dict(l=0, r=0, t=8, b=0), height=260, bargap=0.05, xaxis=dict(showgrid=True, gridcolor="#1e1e30", tickfont=dict(family="JetBrains Mono", size=10)), yaxis=dict(showgrid=True, gridcolor="#1e1e30", tickfont=dict(family="JetBrains Mono", size=10)))
                    fig_h.update_traces(marker_line_width=0)
                    st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
            with tab2:
                with st.container(border=True):
                    top_cpus = df_live["cpu"].value_counts().head(15).reset_index()
                    top_cpus.columns = ["CPU", "count"]
                    top_cpus = top_cpus.iloc[::-1].reset_index(drop=True)
                    fig_c = make_bar(top_cpus, "count", "CPU", [[0, "#0d3320"], [1, "#4ade80"]], height=max(260, len(top_cpus) * 26))
                    st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})

    with col_left: _scraper_status()
    with col_right:
        df_tbl = load_data()
        if not df_tbl.empty:
            df_tbl["score"] = pd.to_numeric(df_tbl["score"], errors="coerce")
            df_tbl = df_tbl.dropna(subset=["score"])
            if "score_id" in df_tbl.columns: df_tbl = df_tbl.sort_values("score_id", ascending=False)
            cols_show = ["score_id", "cpu", "gpu", "score", "benchmark_type", "resolution", "os", "submitted_date"]
            header_map = {"score_id": "Score ID", "cpu": "CPU", "gpu": "GPU", "score": "Score", "benchmark_type": "Benchmark", "resolution": "Resolution", "os": "OS", "submitted_date": "Date"}
            df_display = df_tbl[cols_show].head(500).rename(columns=header_map)
            st.markdown(f'<p class="section-label" style="margin:0 0 .5rem 0">{len(df_tbl):,} {t("db_records")}</p>', unsafe_allow_html=True)
            st.dataframe(df_display, use_container_width=True, hide_index=True, height=650)
        if Path("scraper.log").exists():
            with st.expander("Scraper log"):
                try:
                    log_text = Path("scraper.log").read_text(encoding="utf-8", errors="replace")
                    st.code(log_text[-5000:], language="")
                except: st.caption("Cannot read log")

if __name__ == "__main__":
    show()
