import streamlit as st
from utils.ui import load_css, t

st.set_page_config(
    page_title="GPUMagick Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()

if "lang" not in st.session_state:
    st.session_state.lang = "EN"

# Define pages
scraper_page  = st.Page("pages/scraper.py",  title=t("scraper"),  icon="📡")
analysis_page = st.Page("pages/analysis.py", title=t("analysis"), icon="📊")
builds_page   = st.Page("pages/builds.py",   title=t("builds"),   icon="🛠️")

# Hidden navigation — we render our own links so DOM order is correct
pg = st.navigation([scraper_page, analysis_page, builds_page], position="hidden")

# st.page_link() no añadir aria-current — detectar página activa por objeto
if pg is scraper_page:
    _active_href = ""
elif pg is analysis_page:
    _active_href = "analysis"
else:
    _active_href = "builds"

st.markdown(f"""<style>
[data-testid="stPageLink-NavLink"][href="{_active_href}"] {{
  background: var(--ac-bg) !important;
  color: var(--ac) !important;
  font-weight: 600 !important;
  border-left: 3px solid var(--ac) !important;
}}
</style>""", unsafe_allow_html=True)

# Sidebar: brand → lang → nav (natural DOM order, no CSS hacks)
with st.sidebar:
    st.markdown("""
    <div class="brand">
      <div class="brand-icon">⚡</div>
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

    st.markdown('<hr class="section-sep">', unsafe_allow_html=True)
    st.markdown('<div class="nav-links">', unsafe_allow_html=True)
    st.page_link(scraper_page,  label=t("scraper"),  icon="📡")
    st.page_link(analysis_page, label=t("analysis"), icon="📊")
    st.page_link(builds_page,   label=t("builds"),   icon="🛠️")
    st.markdown('</div>', unsafe_allow_html=True)

pg.run()
