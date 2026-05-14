import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path
from utils.ui import t, page_header, TIER_TOP, TIER_HIGH
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
        return

    df["score"]     = pd.to_numeric(df["score"], errors="coerce")
    df["fps"]       = pd.to_numeric(df["fps"],   errors="coerce")
    df              = df.dropna(subset=["score", "cpu", "gpu"])
    df["gpu_short"] = df["gpu"].apply(short_gpu)

    all_gpus  = sorted(df["gpu_short"].dropna().unique())
    all_bench = sorted(df["benchmark_type"].dropna().unique())
    all_res   = sorted(df["resolution"].dropna().unique())

    if "an_gpu"   not in st.session_state: st.session_state.an_gpu   = []
    if "an_bench" not in st.session_state: st.session_state.an_bench = all_bench
    if "an_res"   not in st.session_state:
        st.session_state.an_res = ["1920x1080"] if "1920x1080" in all_res else all_res

    with st.container(border=True):
        fc1, fc2, fc3 = st.columns([3, 1.5, 1.5])
        fc1.caption(t("gpu"))
        fc2.caption(t("bench"))
        fc3.caption(t("resolution"))
        sel_gpus  = fc1.multiselect(t("gpu"),        all_gpus,  key="an_gpu",   label_visibility="collapsed")
        sel_bench = fc2.multiselect(t("bench"),       all_bench, key="an_bench", label_visibility="collapsed")
        sel_res   = fc3.multiselect(t("resolution"),  all_res,   key="an_res",   label_visibility="collapsed")

    if not sel_gpus:
        with st.container(border=True):
            st.markdown(f'<div class="empty-state"><div class="empty-icon">◈</div><div class="empty-title">{t("select_gpus_title")}</div><div class="empty-sub">{t("select_gpus_sub")}</div></div>', unsafe_allow_html=True)
        return

    fdf = df[
        df["gpu_short"].isin(sel_gpus) &
        df["benchmark_type"].isin(sel_bench if sel_bench else all_bench) &
        df["resolution"].isin(sel_res if sel_res else all_res)
    ]
    if fdf.empty:
        st.warning(t("no_data_filters"))
        return

    with st.container(border=True):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t("samples"),      f"{len(fdf):,}")
        m2.metric(t("gpus"),         fdf["gpu"].nunique())
        m3.metric(t("cpus"),         fdf["cpu"].nunique())
        m4.metric(t("median_score"), f"{int(fdf['score'].median()):,}")

    cpu_gpu = (
        fdf.assign(_fps=fdf["fps"].where(fdf["fps"] > 0))
        .groupby(["gpu_short", "cpu"])
        .agg(Median=("score", "median"), MedianFPS=("_fps", "median"), Samples=("score", "count"))
        .round(1)
        .reset_index()
    )
    has_fps = cpu_gpu["MedianFPS"].notna().any()

    if len(sel_gpus) == 1:
        stats = (
            cpu_gpu[cpu_gpu["gpu_short"] == sel_gpus[0]]
            .sort_values("Median", ascending=False)
            .reset_index(drop=True)
            .rename(columns={"cpu": "CPU"})
        )
        max_med = stats["Median"].max()
        stats["Tier"] = stats["Median"].apply(lambda x:
            "Top"  if x >= max_med * TIER_TOP else
            "Good" if x >= max_med * TIER_HIGH else ""
        )

        _sc1, _sc2 = st.columns([2, 1])
        sort_by      = _sc1.segmented_control(t("sort_by"), ["Median", "Samples"], default="Median", key="sort_cpu")
        an_metric_sg = _sc2.segmented_control("Metric", ["Score", "FPS"], default="Score", key="an_metric_sg") if has_fps else "Score"
        if sort_by == "Samples":
            stats = stats.sort_values("Samples", ascending=False).reset_index(drop=True)

        tcol, gcol = st.columns([1, 1.4])
        with tcol:
            with st.container(border=True):
                st.caption(t("cpu_table"))
                _sg_cols = ["CPU", "Median"] + (["MedianFPS"] if has_fps else []) + ["Samples", "Tier"]
                st.dataframe(stats[_sg_cols], use_container_width=True, hide_index=True, height=350)
            st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(f'<p class="section-label">{t("quick_eval")}</p>', unsafe_allow_html=True)
                st.caption(t("select_cpu_eval"))
                ec, bc = st.columns([2, 1])
                cpu_to_eval = ec.selectbox("CPU", stats["CPU"].tolist(), label_visibility="collapsed", key="eval_cpu_sg")
                if bc.button(t("eval_value"), use_container_width=True, type="primary", key="eval_btn_sg"):
                    st.session_state.jump_cpu = cpu_to_eval
                    st.switch_page("pages/builds.py")
        with gcol:
            with st.container(border=True):
                top20 = stats.head(20).iloc[::-1].reset_index(drop=True)
                _sg_x = "MedianFPS" if an_metric_sg == "FPS" and has_fps else "Median"
                fig = make_bar(top20, _sg_x, "CPU", [[0, "#0a2e18"], [0.5, "#16a34a"], [1, "#4ade80"]], height=420)
                vals = top20[_sg_x]
                if not vals.empty and vals.max() > vals.min():
                    vr = vals.max() - vals.min()
                    fig.update_xaxes(range=[vals.min() - vr * 0.05, vals.max() + vr * 0.02])
                _sg_lbl = t("median_fps") if an_metric_sg == "FPS" else t("median_by_cpu")
                st.caption(f"{_sg_lbl}  ·  {sel_gpus[0]}")
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    else:
        pivot_raw = (
            cpu_gpu.pivot_table(index="cpu", columns="gpu_short", values="Median", aggfunc="first")
            .round(0)
        )
        pivot_raw.columns.name = None
        pivot_raw = pivot_raw.reset_index().rename(columns={"cpu": "CPU"})
        gpu_cols = [c for c in pivot_raw.columns if c != "CPU"]

        pivot_raw["_avg"] = pivot_raw[gpu_cols].mean(axis=1)
        pivot_raw = pivot_raw.sort_values("_avg", ascending=False).reset_index(drop=True)

        if len(gpu_cols) >= 2:
            _rmax = pivot_raw[gpu_cols].max(axis=1)
            _rmin = pivot_raw[gpu_cols].min(axis=1)
            pivot_raw["Δ%"] = ((_rmax - _rmin) / _rmax * 100).round(1)

        for g in gpu_cols:
            best = pivot_raw[g].max()
            pivot_raw[f"✓ {g}"] = pivot_raw[g].apply(
                lambda x, b=best: "✓" if pd.notna(x) and x >= b * 0.95 else ""
            )

        tier_cols  = [f"✓ {g}" for g in gpu_cols]
        _delta_cols = ["Δ%"] if "Δ%" in pivot_raw.columns else []
        disp_df = pivot_raw[["CPU"] + gpu_cols + _delta_cols + tier_cols].copy()

        an_metric = st.segmented_control("Metric", ["Score", "FPS"], default="Score", key="an_metric_mg") if has_fps else "Score"

        tcol, gcol = st.columns([1, 1.4])
        with tcol:
            with st.container(border=True):
                st.caption(f"{t('median_by_cpu')}  ·  {len(gpu_cols)} GPUs  ·  ✓ = top 5%")
                st.dataframe(disp_df, use_container_width=True, hide_index=True, height=380)
            st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(f'<p class="section-label">{t("quick_eval")}</p>', unsafe_allow_html=True)
                st.caption(t("select_cpu_eval"))
                ec, bc = st.columns([2, 1])
                cpu_to_eval = ec.selectbox("CPU", pivot_raw["CPU"].tolist(), label_visibility="collapsed", key="eval_cpu_mg")
                if bc.button(t("eval_value"), use_container_width=True, type="primary", key="eval_btn_mg"):
                    st.session_state.jump_cpu = cpu_to_eval
                    st.switch_page("pages/builds.py")

        with gcol:
            tab_ovw, tab_cpu = st.tabs([t("median_by_gpu"), t("median_by_cpu")])

            with tab_ovw:
                with st.container(border=True):
                    _ovw_src = "fps" if an_metric == "FPS" else "score"
                    _ovw_fdf = fdf[fdf["fps"] > 0] if an_metric == "FPS" else fdf
                    gpu_summary = (
                        _ovw_fdf.groupby("gpu_short")
                        .agg(Median=(_ovw_src, "median"), Samples=(_ovw_src, "count"))
                        .reset_index()
                        .rename(columns={"gpu_short": "GPU"})
                        .sort_values("Median", ascending=True)
                        .reset_index(drop=True)
                    )
                    _colors   = ["#4ade80", "#60a5fa", "#f472b6", "#fb923c"]
                    _best_med = gpu_summary["Median"].max()
                    _num_fmt  = ".1f" if an_metric == "FPS" else ".0f"
                    gpu_summary["_label"] = gpu_summary["Median"].apply(
                        lambda v: f"{v:{_num_fmt}}"
                        if v == _best_med
                        else f"{v:{_num_fmt}}  (−{(_best_med - v) / _best_med * 100:.1f}%)"
                    )
                    fig_ovw = px.bar(
                        gpu_summary, x="Median", y="GPU",
                        orientation="h", template="plotly_dark",
                        color="GPU", color_discrete_sequence=_colors,
                        text="_label",
                    )
                    fig_ovw.update_traces(
                        texttemplate="%{text}", textposition="outside",
                        textfont=dict(family="JetBrains Mono", size=11, color="#ddddf0"),
                        marker_line_width=0,
                    )
                    fig_ovw.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter", color="#6868a0"),
                        showlegend=False,
                        margin=dict(l=0, r=160, t=8, b=0),
                        height=max(200, len(gpu_summary) * 70),
                        xaxis=dict(showgrid=True, gridcolor="#1e1e30", zeroline=False,
                                   tickfont=dict(size=10, family="JetBrains Mono")),
                        yaxis=dict(showgrid=False, tickfont=dict(size=13, family="Inter")),
                    )
                    _ovw_lbl = t("median_fps") if an_metric == "FPS" else t("median_by_gpu")
                    st.caption(f"{_ovw_lbl}  ·  {len(_ovw_fdf):,} samples")
                    st.plotly_chart(fig_ovw, use_container_width=True, config={"displayModeBar": False})

            with tab_cpu:
                with st.container(border=True):
                    _n_each = max(5, 20 // len(sel_gpus))
                    _seen, _top = set(), []
                    for _g in sel_gpus:
                        for _c in (
                            cpu_gpu[cpu_gpu["gpu_short"] == _g]
                            .sort_values("Median", ascending=False)
                            .head(_n_each)["cpu"]
                            .tolist()
                        ):
                            if _c not in _seen:
                                _top.append(_c)
                                _seen.add(_c)
                    _piv_rank = {c: i for i, c in enumerate(pivot_raw["CPU"].tolist())}
                    top_cpus  = sorted(_top, key=lambda c: _piv_rank.get(c, 9999))[:20]
                    chart_df  = cpu_gpu[cpu_gpu["cpu"].isin(top_cpus)].copy()
                    chart_df  = chart_df.rename(columns={"cpu": "CPU", "gpu_short": "GPU"})
                    chart_df["CPU"] = pd.Categorical(chart_df["CPU"], categories=top_cpus[::-1], ordered=True)
                    chart_df  = chart_df.sort_values("CPU")

                    _cpu_x   = "MedianFPS" if an_metric == "FPS" and "MedianFPS" in chart_df.columns else "Median"
                    _cpu_fmt = "%{text:.1f}" if an_metric == "FPS" else "%{text:.0f}"
                    fig = px.bar(
                        chart_df, x=_cpu_x, y="CPU", color="GPU",
                        orientation="h", barmode="group",
                        template="plotly_dark",
                        color_discrete_sequence=["#4ade80", "#60a5fa", "#f472b6", "#fb923c"],
                        text=_cpu_x,
                    )
                    fig.update_traces(
                        texttemplate=_cpu_fmt, textposition="outside",
                        textfont=dict(family="JetBrains Mono", size=10, color="#ddddf0"),
                        marker_line_width=0,
                    )
                    _cpu_vals = chart_df[_cpu_x].dropna()
                    if not _cpu_vals.empty and _cpu_vals.max() > _cpu_vals.min():
                        _cvr = _cpu_vals.max() - _cpu_vals.min()
                        _cpu_xrange = [_cpu_vals.min() - _cvr * 0.05, _cpu_vals.max() + _cvr * 0.15]
                    else:
                        _cpu_xrange = None
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter", color="#6868a0"),
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                                    font=dict(family="Inter", size=11, color="#ddddf0"),
                                    bgcolor="rgba(0,0,0,0)"),
                        coloraxis_showscale=False,
                        margin=dict(l=0, r=80, t=36, b=0),
                        height=max(340, len(top_cpus) * 44),
                        xaxis=dict(showgrid=True, gridcolor="#1e1e30", zeroline=False,
                                   tickfont=dict(size=10, family="JetBrains Mono"),
                                   range=_cpu_xrange),
                        yaxis=dict(showgrid=False, tickfont=dict(size=11, family="Inter"),
                                   categoryorder="array", categoryarray=top_cpus[::-1]),
                    )
                    _cpu_lbl = t("median_fps") if an_metric == "FPS" else t("median_by_cpu")
                    st.caption(f"{_cpu_lbl}  ·  top 20")
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

if __name__ == "__main__":
    show()
