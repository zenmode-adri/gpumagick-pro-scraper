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

    df["fps"]       = pd.to_numeric(df["fps"],   errors="coerce")
    df["score"]     = pd.to_numeric(df["score"], errors="coerce")
    df["gpu_short"] = df["gpu"].apply(short_gpu)
    df = df.dropna(subset=["score", "cpu", "gpu"])

    saved_prices = load_cpu_prices()
    gpu_options  = sorted(df["gpu_short"].dropna().unique())

    with st.container(border=True):
        top_c1, top_c2, top_c3 = st.columns([1.5, 2, 2.5])
        with top_c1:
            sel_gpus = st.multiselect(t("gpu"), gpu_options)
        with top_c2:
            min_samples = st.slider(f"{t('samples')} / CPU", 1, 20, 3)
        with top_c3:
            kpi_placeholder = st.empty()

    if not sel_gpus:
        with st.container(border=True):
            st.markdown(f'<div class="empty-state"><div class="empty-icon">🛠️</div><div class="empty-title">{t("select_gpu_prompt")}</div></div>', unsafe_allow_html=True)
        return

    fdf = df[df["gpu_short"].isin(sel_gpus)]
    combo_stats = (
        fdf.groupby(["gpu_short", "cpu"])
        .agg(fps_med=("fps", "median"), score_med=("score", "median"), samples=("score", "count"))
        .reset_index()
    )
    combo_stats = combo_stats[combo_stats["samples"] >= min_samples]

    if combo_stats.empty:
        st.warning(t("no_data_filters"))
        return

    bot_left, bot_right = st.columns([1, 2])

    with bot_left:
        with st.container(border=True):
            st.markdown(f'<p class="section-label">{t("gpu_price")}</p>', unsafe_allow_html=True)
            gpu_price = st.number_input("€", value=100, min_value=1, label_visibility="collapsed")

        with st.container(border=True):
            st.markdown(f'<p class="section-label">{t("cpu_prices")}</p>', unsafe_allow_html=True)
            cpus_in_combo = sorted(combo_stats["cpu"].unique())
            cpu_rows = [{"CPU": cpu, "€": saved_prices.get(cpu, 50)} for cpu in cpus_in_combo]
            cpu_ed = st.data_editor(
                pd.DataFrame(cpu_rows), use_container_width=True,
                hide_index=True, num_rows="fixed",
                column_config={"€": st.column_config.NumberColumn(min_value=1)}
            )
            if st.button(t("save_prices"), use_container_width=True):
                updated = {row["CPU"]: int(row["€"]) for _, row in cpu_ed.iterrows()}
                save_cpu_prices({**saved_prices, **updated})
                st.toast(t("save_prices") + " ✓")

    with bot_right:
        cpu_price_map = {row["CPU"]: row["€"] for _, row in cpu_ed.iterrows()}
        combo_stats["cpu_price"]   = combo_stats["cpu"].map(lambda c: cpu_price_map.get(c, saved_prices.get(c, 50)))
        combo_stats["total_cost"]  = gpu_price + combo_stats["cpu_price"]
        combo_stats["fps_eur"]     = (combo_stats["fps_med"]   / combo_stats["total_cost"]).round(3)
        combo_stats["score_eur"]   = (combo_stats["score_med"] / combo_stats["total_cost"]).round(2)
        ranking = combo_stats.sort_values("fps_eur", ascending=False).reset_index(drop=True)

        best = ranking.iloc[0]
        kpi_placeholder.metric(t("best_fps_eur"), f"{best['fps_eur']:.3f}", f"{best['cpu']} + {best['gpu_short']}")

        with st.container(border=True):
            st.markdown(f'<p class="section-label">{t("best_fps_eur")}</p>', unsafe_allow_html=True)
            display_cols = {
                "gpu_short": "GPU", "cpu": "CPU",
                "fps_eur": "FPS/€", "fps_med": t("median_fps"),
                "score_med": t("median_score"), "total_cost": t("total_cost"),
                "samples": t("samples"),
            }
            st.dataframe(
                ranking[list(display_cols)].rename(columns=display_cols),
                use_container_width=True, hide_index=True, height=460
            )

        if len(ranking) >= 3:
            with st.container(border=True):
                top_chart = ranking.head(20).iloc[::-1].reset_index(drop=True)
                fig = make_bar(top_chart, "fps_eur", "cpu", height=max(300, len(top_chart) * 26))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

if __name__ == "__main__":
    show()
