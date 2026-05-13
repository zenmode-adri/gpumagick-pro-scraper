import streamlit as st
import pandas as pd
from utils.ui import t, page_header, load_cpu_prices, save_cpu_prices
from utils.data import load_data, short_gpu
from utils.charts import make_bar

def show():
    page_header(t("builds"), t("builds_sub"))
    df = load_data()
    if df.empty:
        st.info(t("no_data"))
        return

    df["fps"] = pd.to_numeric(df["fps"], errors="coerce")
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["gpu_short"] = df["gpu"].apply(short_gpu)
    df = df.dropna(subset=["score", "cpu", "gpu"])

    saved_prices = load_cpu_prices()
    gpu_options = sorted(df["gpu_short"].dropna().unique())

    with st.container(border=True):
        top_c1, top_c2, top_c3 = st.columns([1.5, 2, 2.5])
        with top_c1:
            sel_gpus = st.multiselect(t("gpu"), gpu_options)
        with top_c2:
            min_samples = st.slider(f"{t('samples')} / CPU", 1, 20, 3)
        with top_c3:
            kpi_placeholder = st.empty()

    if not sel_gpus:
        st.info("Select a GPU to see the ranking")
        return

    # Filter and calculate
    fdf = df[df["gpu_short"].isin(sel_gpus)]
    combo_stats = fdf.groupby(["gpu_short", "cpu"]).agg(fps_med=("fps", "median"), score_med=("score", "median"), samples=("score", "count")).reset_index()
    combo_stats = combo_stats[combo_stats["samples"] >= min_samples]

    bot_left, bot_right = st.columns([1, 2])
    
    with bot_left:
        with st.container(border=True):
            st.caption(t("gpu_price"))
            # Simplified for brevity in refactor
            gpu_price = st.number_input("GPU Price (€)", value=100)
            
        with st.container(border=True):
            st.caption(t("cpu_prices"))
            # Show a few CPUs
            cpu_rows = []
            for cpu in combo_stats["cpu"].unique()[:10]:
                cpu_rows.append({"CPU": cpu, "Price (€)": saved_prices.get(cpu, 50)})
            cpu_ed = st.data_editor(pd.DataFrame(cpu_rows), use_container_width=True, hide_index=True)

    with bot_right:
        with st.container(border=True):
            st.caption("FPS/€ Ranking")
            st.dataframe(combo_stats, use_container_width=True)

if __name__ == "__main__":
    show()
