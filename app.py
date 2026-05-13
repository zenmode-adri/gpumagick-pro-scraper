import streamlit as st
from utils.ui import load_css, t

st.set_page_config(
    page_title="GPUMagick Pro",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()

if "lang" not in st.session_state:
    st.session_state.lang = "EN"

# Sidebar Branding & Language
with st.sidebar:
    st.markdown("""
    <div class="brand">
      <div class="brand-icon">◈</div>
      <div>
        <div class="brand-name">GPUMagick</div>
        <div class="brand-sub">Analyzer</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    lang_sel = st.segmented_control(
        "LANG", ["EN", "ES"], 
        default=st.session_state.lang, 
        label_visibility="collapsed"
    )
    if lang_sel and lang_sel != st.session_state.lang:
        st.session_state.lang = lang_sel
        st.rerun()

    st.divider()

# Navigation definition
scraper_page = st.Page("pages/scraper.py", title=t("scraper"), icon="◉")
analysis_page = st.Page("pages/analysis.py", title=t("analysis"), icon="≡")
builds_page = st.Page("pages/builds.py", title=t("builds"), icon="◈")

pg = st.navigation([scraper_page, analysis_page, builds_page])
pg.run()
