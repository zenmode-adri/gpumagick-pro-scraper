import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from utils.ui import t, page_header
from utils.data import load_data, short_gpu
from utils.charts import make_bar

def show():
    page_header(t("analysis"), t("analysis_sub"))

    uploaded = st.file_uploader("Import file (CSV or DB)", type=["csv", "db"], label_visibility="collapsed")
    if uploaded:
        if uploaded.name.endswith(".db"):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            conn = sqlite3.connect(tmp_path)
            df = pd.read_sql_query("SELECT * FROM scores", conn)
            conn.close()
            Path(tmp_path).unlink(missing_ok=True)
        else:
            df = pd.read_csv(uploaded)
    else:
        df = load_data()

    if df.empty:
        with st.container(border=True):
            st.markdown(f'<div class="empty-state"><div class="empty-icon">≡</div><div class="empty-title">{t("no_data")}</div><div class="empty-sub">{t("no_data_sub")}</div></div>', unsafe_allow_html=True)
    else:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        df["fps"] = pd.to_numeric(df["fps"], errors="coerce")
        df = df.dropna(subset=["score", "cpu", "gpu"])
        df["gpu_short"] = df["gpu"].apply(short_gpu)

        all_gpus = sorted(df["gpu_short"].dropna().unique())
        all_bench = sorted(df["benchmark_type"].dropna().unique())
        all_res = sorted(df["resolution"].dropna().unique())

        if "an_gpu" not in st.session_state: st.session_state.an_gpu = []
        if "an_bench" not in st.session_state: st.session_state.an_bench = all_bench
        if "an_res" not in st.session_state: st.session_state.an_res = ["1920x1080"] if "1920x1080" in all_res else all_res

        with st.container(border=True):
            fc1, fc2, fc3 = st.columns([3, 1.5, 1.5])
            sel_gpus = fc1.multiselect(t("gpu"), all_gpus, key="an_gpu")
            sel_bench = fc2.multiselect(t("bench"), all_bench, key="an_bench")
            sel_res = fc3.multiselect(t("resolution"), all_res, key="an_res")

        if not sel_gpus:
            with st.container(border=True):
                st.markdown(f'<div class="empty-state"><div class="empty-icon">◈</div><div class="empty-title">{t("select_gpus_title")}</div><div class="empty-sub">{t("select_gpus_sub")}</div></div>', unsafe_allow_html=True)
        else:
            fdf = df[df["gpu_short"].isin(sel_gpus) & df["benchmark_type"].isin(sel_bench if sel_bench else all_bench) & df["resolution"].isin(sel_res if sel_res else all_res)]
            if fdf.empty:
                st.warning(t("no_data_filters"))
            else:
                with st.container(border=True):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric(t("samples"), f"{len(fdf):,}")
                    m2.metric(t("gpus"), fdf["gpu"].nunique())
                    m3.metric(t("cpus"), fdf["cpu"].nunique())
                    m4.metric(t("median_score"), f"{int(fdf['score'].median()):,}")

                cpu_gpu = fdf.assign(_fps=fdf["fps"].where(fdf["fps"] > 0)).groupby(["gpu_short", "cpu"]).agg(Median=("score", "median"), MedianFPS=("_fps", "median"), Samples=("score", "count")).round(1).reset_index()
                has_fps = cpu_gpu["MedianFPS"].notna().any()

                if len(sel_gpus) == 1:
                    stats = cpu_gpu[cpu_gpu["gpu_short"] == sel_gpus[0]].sort_values("Median", ascending=False).reset_index(drop=True).rename(columns={"cpu": "CPU"})
                    sort_by = st.segmented_control(t("sort_by"), ["Median", "Samples"], default="Median", key="sort_cpu")
                    if sort_by == "Samples": stats = stats.sort_values("Samples", ascending=False).reset_index(drop=True)
                    tcol, gcol = st.columns([1, 1.4])
                    with tcol:
                        with st.container(border=True):
                            st.dataframe(stats[["CPU", "Median", "Samples"]], use_container_width=True, hide_index=True, height=420)
                    with gcol:
                        with st.container(border=True):
                            top20 = stats.head(20).iloc[::-1].reset_index(drop=True)
                            fig = make_bar(top20, "Median", "CPU", height=420)
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    pivot_raw = cpu_gpu.pivot_table(index="cpu", columns="gpu_short", values="Median", aggfunc="first").round(0).reset_index().rename(columns={"cpu": "CPU"})
                    st.dataframe(pivot_raw, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    show()
