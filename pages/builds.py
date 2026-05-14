import streamlit as st
import pandas as pd
from utils.ui import t, page_header, load_cpu_prices, save_cpu_prices
from utils.data import load_data, short_gpu
from utils.charts import make_bar

def show():
    page_header(t("builds"), t("builds_sub"))

    df = load_data()
    if df.empty:
        with st.container(border=True):
            st.markdown(f'<div class="empty-state"><div class="empty-icon">◈</div><div class="empty-title">{t("no_data")}</div><div class="empty-sub">{t("no_data_sub")}</div></div>', unsafe_allow_html=True)
        return

    df["fps"]       = pd.to_numeric(df["fps"],   errors="coerce")
    df["score"]     = pd.to_numeric(df["score"], errors="coerce")
    df["gpu_short"] = df["gpu"].apply(short_gpu)
    df              = df.dropna(subset=["score", "cpu", "gpu"])

    saved_prices = load_cpu_prices()
    gpu_options  = sorted(df["gpu_short"].dropna().unique())

    if "filter_gpu"   not in st.session_state: st.session_state.filter_gpu   = None
    if "filter_bench" not in st.session_state: st.session_state.filter_bench = None
    if "filter_res"   not in st.session_state: st.session_state.filter_res   = None

    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        top_c1, top_c2, top_c3 = st.columns([1.5, 2, 2.5])

        with top_c1:
            st.caption(t("gpu_cfg"))
            jump_default = None
            if st.session_state.filter_gpu is not None:
                jump_default = st.session_state.filter_gpu
            elif gpu_options:
                jump_default = [gpu_options[0]]
            sel_gpus = st.multiselect(t("gpu"), gpu_options, default=jump_default, label_visibility="collapsed")
            st.session_state.filter_gpu = sel_gpus

        with top_c2:
            st.caption(t("filters"))
            if not sel_gpus:
                bench_opts, res_opts = [], []
            else:
                sel_gpu_full = set()
                for g in sel_gpus:
                    sel_gpu_full.update(df[df["gpu_short"] == g]["gpu"].unique())
                gpu_mask   = df["gpu"].isin(sel_gpu_full)
                bench_opts = sorted(df[gpu_mask]["benchmark_type"].dropna().unique())
                res_opts   = sorted(df[gpu_mask]["resolution"].dropna().unique())

            def _safe_default(saved, opts, fallback):
                if saved is not None:
                    valid = [x for x in saved if x in opts]
                    return valid if valid else (fallback if fallback in opts else (opts[:1] if opts else []))
                return fallback if fallback in opts else (opts[:1] if opts else [])

            sel_bench = st.multiselect(t("bench"), bench_opts,
                default=_safe_default(st.session_state.filter_bench, bench_opts, "FurMark (GL)"),
                label_visibility="collapsed", disabled=not sel_gpus)
            st.session_state.filter_bench = sel_bench

            sel_res = st.multiselect(t("resolution"), res_opts,
                default=_safe_default(st.session_state.filter_res, res_opts, "1920x1080"),
                label_visibility="collapsed", disabled=not sel_gpus)
            st.session_state.filter_res = sel_res

            min_samples = st.slider(f"{t('samples')} / CPU", 1, 20, 3, disabled=not sel_gpus)

        with top_c3:
            st.caption(t("perf_metrics"))
            kpi_placeholder = st.empty()

    if not sel_gpus:
        st.info(t("select_gpu_prompt"))
        return

    filt = (
        df["gpu"].isin(sel_gpu_full) &
        df["benchmark_type"].isin(sel_bench if sel_bench else bench_opts) &
        df["resolution"].isin(sel_res if sel_res else res_opts)
    )
    combo_stats = (
        df[filt]
        .groupby(["gpu_short", "cpu"])
        .agg(fps_med=("fps", "median"), score_med=("score", "median"), samples=("score", "count"))
        .reset_index()
    )
    combo_stats = combo_stats[combo_stats["samples"] >= min_samples]
    all_cpus = sorted(combo_stats["cpu"].unique())

    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    bot_left, bot_right = st.columns([1, 2])

    with bot_left:
        with st.container(border=True):
            st.caption(t("gpu_price"))
            gpu_stats = combo_stats.groupby("gpu_short").agg(Samples=("samples", "sum")).reset_index()
            gpu_stats = gpu_stats.rename(columns={"gpu_short": "GPU"})
            gpu_stats["Price (€)"] = gpu_stats["GPU"].apply(lambda g: int(saved_prices.get(f"gpu_price:{g}", 0)))
            gpu_price_ed = st.data_editor(
                gpu_stats,
                column_config={
                    "GPU":       st.column_config.TextColumn("GPU", disabled=True),
                    "Samples":   st.column_config.NumberColumn("Samples", disabled=True),
                    "Price (€)": st.column_config.NumberColumn(t("market_val"), min_value=1, step=5, format="%d €"),
                },
                hide_index=True, use_container_width=True, key="gpu_p_ed",
            )
            gpu_price_map = dict(zip(gpu_price_ed["GPU"], gpu_price_ed["Price (€)"]))

        top_cpus_idx = combo_stats.groupby("cpu")["samples"].sum().sort_values(ascending=False).head(20).index.tolist()
        top_cpus = list(top_cpus_idx)

        # jump_cpu is set by pages/analysis.py Quick Evaluate button via st.switch_page
    jump_cpu = st.session_state.get("jump_cpu")
        if jump_cpu and jump_cpu not in top_cpus:
            top_cpus.insert(0, jump_cpu)

        cpu_metrics = combo_stats.groupby("cpu").agg(
            Samples=("samples", "sum"), Median_Score=("score_med", "median")
        ).reset_index()

        _cpu_rows = []
        for cpu in top_cpus:
            price = saved_prices.get(cpu, 0)
            if price == 0:
                price = next((v for k, v in saved_prices.items()
                              if isinstance(v, (int, float)) and not k.startswith("gpu_price:")
                              and (k.lower() in cpu.lower() or cpu.lower() in k.lower())), 0)
            m = cpu_metrics[cpu_metrics["cpu"] == cpu]
            metrics = m.iloc[0] if not m.empty else {"Samples": 0, "Median_Score": 0}
            _cpu_rows.append({"CPU": cpu, "Samples": int(metrics["Samples"]),
                               "Median Score": int(metrics["Median_Score"]), "Price (€)": int(price)})

        with st.container(border=True):
            st.caption(f"{t('cpu_prices')}  ·  top {len(_cpu_rows)}")
            cpu_price_ed = st.data_editor(
                pd.DataFrame(_cpu_rows),
                column_config={
                    "CPU":          st.column_config.TextColumn("CPU", disabled=True),
                    "Samples":      st.column_config.NumberColumn("Samples", disabled=True),
                    "Median Score": st.column_config.NumberColumn("Median Score", disabled=True),
                    "Price (€)":    st.column_config.NumberColumn(t("market_val"), min_value=0, step=5, format="%d €"),
                },
                hide_index=True, use_container_width=True, key="cpu_p_ed",
                height=min(400, max(120, len(_cpu_rows) * 35 + 42)),
            )

            st.markdown('<hr class="section-sep">', unsafe_allow_html=True)

            with st.container(border=True):
                st.caption(t("action_center"))
                shown     = set(cpu_price_ed["CPU"].tolist())
                available = [c for c in all_cpus if c not in shown]
                if available:
                    a1, a2   = st.columns([2, 1])
                    new_cpu   = a1.selectbox("CPU", available, label_visibility="collapsed", key="new_cpu_sel")
                    new_price = a2.number_input("€", value=50, min_value=0, step=5, label_visibility="collapsed", key="new_cpu_price")
                    if st.button(t("add_to_ranking"), use_container_width=True, key="btn_add_cpu"):
                        merged = {row["CPU"]: int(row["Price (€)"]) for _, row in cpu_price_ed.iterrows()}
                        merged[new_cpu] = int(new_price)
                        for g, p in gpu_price_map.items(): merged[f"gpu_price:{g}"] = int(p)
                        save_cpu_prices(merged)
                        st.rerun()

                if st.button(t("save_prices"), use_container_width=True, type="primary"):
                    new_p = {row["CPU"]: int(row["Price (€)"]) for _, row in cpu_price_ed.iterrows()}
                    for g, p in gpu_price_map.items(): new_p[f"gpu_price:{g}"] = int(p)
                    save_cpu_prices(new_p)
                    st.toast("Prices saved ✓")

    if combo_stats.empty:
        with bot_right:
            with st.container(border=True):
                st.markdown(f'<div class="empty-state"><div class="empty-icon">◈</div><div class="empty-title">{t("no_data")}</div><div class="empty-sub">Selecciona una GPU con datos disponibles</div></div>', unsafe_allow_html=True)
        with kpi_placeholder.container():
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(t("best_fps_eur"), "—"); m2.metric("Median FPS", "—")
            m3.metric(t("total_cost"), "—");   m4.metric(t("priced_combos"), 0)
        return

    cpu_price_final = dict(zip(cpu_price_ed["CPU"], cpu_price_ed["Price (€)"]))
    priced = combo_stats.copy()
    priced["cpu_price"] = priced["cpu"].map(cpu_price_final).fillna(0).astype(int)
    priced["gpu_price"] = priced["gpu_short"].map(gpu_price_map).fillna(0).astype(int)
    priced = priced[(priced["cpu_price"] > 0) & (priced["gpu_price"] > 0)].copy()

    if priced.empty:
        with bot_right:
            with st.container(border=True):
                st.info("Enter CPU prices in the left column to view the FPS/€ ranking")
        with kpi_placeholder.container():
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(t("best_fps_eur"), "—"); m2.metric("Median FPS", "—")
            m3.metric(t("total_cost"), "—");   m4.metric(t("priced_combos"), 0)
        return

    priced["total_eur"] = priced["cpu_price"] + priced["gpu_price"]
    priced["fps_eur"]   = (priced["fps_med"] / priced["total_eur"]).round(4)
    priced["score_eur"] = (priced["score_med"] / priced["total_eur"]).round(2)
    priced = priced.sort_values("fps_eur", ascending=False, na_position="last").reset_index(drop=True)

    fps_priced = priced.dropna(subset=["fps_eur"])
    best = fps_priced.iloc[0] if not fps_priced.empty else None

    with kpi_placeholder.container():
        if best is not None:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(t("best_fps_eur"),  f"{best['fps_eur']:.4f}")
            m2.metric("Median FPS",       f"{best['fps_med']:.0f}" if pd.notna(best["fps_med"]) else "—")
            m3.metric(t("total_cost"),    f"{int(best['total_eur'])} €")
            m4.metric(t("priced_combos"), len(fps_priced))

    with bot_right:
        with st.container(border=True):
            if not fps_priced.empty:
                if len(sel_gpus) == 1:
                    chart_df  = fps_priced.head(25).iloc[::-1].reset_index(drop=True)
                    label_col = "cpu"
                    caption   = f"FPS/€  ·  {sel_gpus[0]}  @  {gpu_price_map.get(sel_gpus[0], '?')} €"
                else:
                    fps_priced = fps_priced.copy()
                    fps_priced["build"] = fps_priced["cpu"] + "  +  " + fps_priced["gpu_short"]
                    chart_df  = fps_priced.head(25).iloc[::-1].reset_index(drop=True)
                    label_col = "build"
                    caption   = "Top 25 builds by FPS/€"

                fig = make_bar(
                    chart_df, "fps_eur", label_col,
                    [[0, "#0a2e18"], [0.5, "#16a34a"], [1, "#4ade80"]],
                    text_fmt="%{text:.4f}",
                    height=max(280, len(chart_df) * 30),
                )
                st.caption(caption)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No FPS data available for the selected filters")

    with st.expander(t("full_breakdown")):
        tbl = priced.rename(columns={
            "cpu": "CPU", "gpu_short": "GPU",
            "fps_med": "Median FPS", "score_med": "Score med",
            "cpu_price": "CPU (€)", "gpu_price": "GPU (€)",
            "total_eur": "Total (€)", "fps_eur": "FPS/€",
            "score_eur": "Score/€", "samples": "N",
        })
        show_cols = [c for c in ["CPU","GPU","Median FPS","Score med","CPU (€)","GPU (€)","Total (€)","FPS/€","Score/€","N"] if c in tbl.columns]
        st.dataframe(tbl[show_cols], use_container_width=True, hide_index=True)

if __name__ == "__main__":
    show()
