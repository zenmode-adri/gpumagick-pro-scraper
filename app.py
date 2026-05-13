import re
import streamlit as st
import pandas as pd
import sqlite3
import subprocess
import sys
import json
import time
import os
import psutil
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="GPUMagick",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH     = "gpumagick.db"
STATUS_FILE = "status.json"
PYTHON      = sys.executable
CLI_SCRIPT  = "cli.py"

CPU_PRICES = {
    "Ryzen 5 3600":   75,  "Ryzen 5 5600":  115,
    "Core i5-12400F": 125, "Core i3-12100F": 85,
    "Ryzen 7 5700X":  165, "Ryzen 5 2600":   45,
    "Core i7-4770":    40, "Xeon E5-2667 v2": 25,
}

CPU_PRICES_FILE = "cpu_prices.json"

def load_cpu_prices():
    if Path(CPU_PRICES_FILE).exists():
        with open(CPU_PRICES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {**CPU_PRICES}

def save_cpu_prices(d):
    with open(CPU_PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

# ── Design system ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block');

/* ── Tokens dark ──────────────────────────────────────── */
:root {
  --bg:    #0b0b12;
  --s0:    #111119;
  --s1:    #17171f;
  --s2:    #1e1e28;
  --b0:    #1e1e30;
  --b1:    #2c2c42;
  --t0:    #ddddf0;
  --t1:    #6868a0;
  --t2:    #404060;
  --ac:    #4ade80;
  --ac-bg: rgba(74,222,128,.10);
  --ac-dk: #166534;
  --err:   #f87171;
  --er-bg: rgba(248,113,113,.10);
  --warn:  #fbbf24;
  --wa-bg: rgba(251,191,36,.10);
  --r0:    6px;
  --r1:    10px;
  --sh:    0 2px 12px rgba(0,0,0,.5);
  --sh-sm: 0 1px 4px rgba(0,0,0,.4);
  --ease:  140ms cubic-bezier(.4,0,.2,1);
  --font:  'Inter', system-ui, sans-serif;
  --mono:  'JetBrains Mono', monospace;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg:    #f0f0f6;
    --s0:    #fafafa;
    --s1:    #f3f3f8;
    --s2:    #ffffff;
    --b0:    #d0d0e0;
    --b1:    #b0b0c8;
    --t0:    #18182c;
    --t1:    #5c5c88;
    --t2:    #9090b8;
    --ac:    #16a34a;
    --ac-bg: rgba(22,163,74,.10);
    --ac-dk: #bbf7d0;
    --err:   #dc2626;
    --er-bg: rgba(220,38,38,.10);
    --warn:  #d97706;
    --wa-bg: rgba(217,119,6,.10);
    --sh:    0 2px 12px rgba(0,0,0,.10);
    --sh-sm: 0 1px 4px rgba(0,0,0,.07);
  }
}

/* ── Base ─────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
.stApp {
  background: var(--bg) !important;
  color: #cbd5e1 !important; /* Soft gray instead of white */
  font-family: var(--font) !important;
  font-size: 14px !important;
  -webkit-font-smoothing: antialiased !important;
}
#MainMenu, footer, header { visibility: hidden !important; }
.block-container { padding: 1.5rem 1.75rem 3rem !important; max-width: 100% !important; }

/* ── Tables Refinement ────────────────────────────────── */
[data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
    color: #cbd5e1 !important;
    font-family: var(--mono) !important;
}
[data-testid="stDataFrame"] th {
    text-transform: capitalize !important;
    background-color: #1e1e28 !important;
    color: var(--ac) !important;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--b1); border-radius: 99px; }

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--s0) !important;
  border-right: 1px solid var(--b0) !important;
  min-width: 220px !important; max-width: 220px !important;
}
[data-testid="stSidebarCollapseButton"] { display: none !important; }
[data-testid="stSidebar"] .block-container { padding: 1.25rem 0.75rem !important; }

.brand { display: flex; align-items: center; gap: 10px; padding: 0 .375rem 1rem; }
.brand-icon {
  width: 30px; height: 30px; flex-shrink: 0;
  background: var(--ac-bg); border: 1.5px solid var(--ac); border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; color: var(--ac);
}
.brand-name { font-size: 14px; font-weight: 700; color: var(--t0); letter-spacing: -.025em; line-height: 1.2; }
.brand-sub  { font-size: 10px; font-weight: 500; letter-spacing: .08em; text-transform: uppercase; color: var(--t1); }

[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 2px !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  display: flex !important; align-items: center !important;
  padding: .5rem .75rem !important; border-radius: var(--r0) !important;
  font-family: var(--font) !important; font-size: 13.5px !important; font-weight: 500 !important;
  color: var(--t1) !important; cursor: pointer !important; width: 100% !important; margin: 0 !important;
  transition: background var(--ease), color var(--ease) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: var(--s1) !important; color: var(--t0) !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  background: var(--ac-bg) !important; color: var(--ac) !important; font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"],
[data-testid="stSidebar"] [data-testid="stRadio"] svg { display: none !important; }
/* Hide the radio circle indicator (the filled/empty dot) */
[data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child { display: none !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  font-family: var(--mono) !important; font-size: 10.5px !important; color: var(--t2) !important;
}

/* ── Typography ─────────────────────────────────────────── */
h1, h2, h3, h4, p, li, .stMarkdown p {
  font-family: var(--font) !important; color: var(--t0) !important;
}
h1, h2, h3, h4 { letter-spacing: -.025em !important; }
.page-title { font-size: 1.3rem; font-weight: 700; color: var(--t0); letter-spacing: -.03em; margin: 0 0 .15rem 0; line-height: 1.25; }
.page-sub   { font-size: 12.5px; color: var(--t1); margin: 0 0 1.25rem 0; }
[data-testid="stCaptionContainer"] {
  font-family: var(--font) !important; font-size: 10.5px !important; font-weight: 600 !important;
  letter-spacing: .07em !important; text-transform: uppercase !important; color: var(--t1) !important;
}

/* ── Cards ──────────────────────────────────────────────── */
/* Outside columns: Streamlit wraps in stVerticalBlockBorderWrapper             */
/* Inside columns:  bordered stVerticalBlock sits directly inside stLayoutWrapper */
[data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"],
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
  background: var(--s1) !important;
  border: 1px solid var(--b1) !important;
  border-radius: var(--r1) !important;
  padding: 1rem 1.125rem !important;
}

/* Expander nested inside a card — blend in, no double border */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stExpander"],
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] [data-testid="stExpander"],
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stExpander"] details,
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] [data-testid="stExpander"] details,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stExpander"] details > div,
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] [data-testid="stExpander"] details > div,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stExpanderDetails"],
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] [data-testid="stExpanderDetails"] {
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stExpander"] summary,
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] [data-testid="stExpander"] summary {
  background: transparent !important;
  padding: .3rem 0 !important;
  font-size: 12.5px !important;
  color: var(--t1) !important;
}

/* ── Metrics ────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--s2) !important;
  border: 1px solid var(--b0) !important;
  border-left: 3px solid var(--ac) !important;
  border-radius: var(--r1) !important;
  padding: .875rem 1rem !important;
}
[data-testid="stMetricLabel"] > div {
  font-family: var(--font) !important; font-size: 10.5px !important; font-weight: 600 !important;
  letter-spacing: .07em !important; text-transform: uppercase !important; color: var(--t1) !important;
}
[data-testid="stMetricValue"] {
  font-family: var(--mono) !important; font-size: 1.35rem !important;
  font-weight: 700 !important; color: var(--t0) !important; letter-spacing: -.02em !important;
}
[data-testid="stMetricDelta"] { font-family: var(--mono) !important; font-size: 12px !important; }

/* ── Inputs — THE FIX: border lives on [data-baseweb="input"] not on <input> ── */
[data-baseweb="input"] {
  background: var(--s2) !important;
  border: 1px solid var(--b0) !important;
  border-radius: var(--r0) !important;
  transition: border-color var(--ease), box-shadow var(--ease) !important;
}
[data-baseweb="base-input"] { background: transparent !important; }
[data-baseweb="input"] input {
  background: transparent !important;
  color: var(--t0) !important;
  font-family: var(--mono) !important;
  font-size: 13px !important;
}
[data-baseweb="input"]:focus-within {
  border-color: var(--ac) !important;
  box-shadow: 0 0 0 3px var(--ac-bg) !important;
}

/* Select / multiselect */
[data-baseweb="select"] > div:first-child {
  background: var(--s2) !important;
  border: 1px solid var(--b0) !important;
  border-radius: var(--r0) !important;
  transition: border-color var(--ease), box-shadow var(--ease) !important;
}
[data-baseweb="select"]:focus-within > div:first-child {
  border-color: var(--ac) !important;
  box-shadow: 0 0 0 3px var(--ac-bg) !important;
}
[data-baseweb="select"] span { color: var(--t0) !important; font-family: var(--font) !important; }
[data-baseweb="tag"] {
  background: var(--ac-bg) !important; border: 1px solid var(--ac) !important;
  border-radius: 4px !important;
}
[data-baseweb="tag"] span { color: var(--ac) !important; font-size: 11.5px !important; font-weight: 500 !important; }
[data-baseweb="popover"] {
  background: var(--s1) !important; border: 1px solid var(--b0) !important;
  border-radius: var(--r1) !important; box-shadow: 0 8px 24px rgba(0,0,0,.55) !important;
}
[role="option"] { font-family: var(--font) !important; font-size: 13px !important; color: var(--t0) !important; background: transparent !important; }
[role="option"]:hover { background: var(--s2) !important; }
[aria-selected="true"][role="option"] { background: var(--ac-bg) !important; color: var(--ac) !important; }

/* Number input +/- */
[data-testid="stNumberInputStepDown"],
[data-testid="stNumberInputStepUp"] {
  background: transparent !important; border: none !important;
  color: var(--t2) !important; outline: none !important; box-shadow: none !important;
  border-radius: 4px !important; transition: color var(--ease) !important;
}
[data-testid="stNumberInputStepDown"]:hover,
[data-testid="stNumberInputStepUp"]:hover { color: var(--t0) !important; }
[data-testid="stNumberInputStepDown"]:active,
[data-testid="stNumberInputStepUp"]:active,
[data-testid="stNumberInputStepDown"]:focus,
[data-testid="stNumberInputStepUp"]:focus {
  color: var(--ac) !important; background: transparent !important;
  outline: none !important; box-shadow: none !important;
}

/* ── Buttons ────────────────────────────────────────────── */
.stButton > button {
  font-family: var(--font) !important; font-size: 13px !important; font-weight: 500 !important;
  border-radius: var(--r0) !important; border: none !important;
  background: var(--s2) !important; color: var(--t1) !important;
  padding: 0 .875rem !important; height: 34px !important;
  transition: background var(--ease), color var(--ease) !important;
  box-shadow: none !important; outline: none !important;
}
.stButton > button:hover { background: var(--b1) !important; color: var(--t0) !important; }
.stButton > button:focus, .stButton > button:active, .stButton > button:focus-visible {
  outline: none !important; box-shadow: none !important; border: none !important;
}
/* Primary button — needs higher specificity than .stButton > button (0,1,1) */
.stButton > button[data-testid="stBaseButton-primary"] {
  background: var(--ac) !important; color: #032b13 !important; font-weight: 600 !important;
}
.stButton > button[data-testid="stBaseButton-primary"]:hover {
  opacity: .88 !important; box-shadow: 0 0 0 3px var(--ac-bg) !important;
}
.stButton > button[data-testid="stBaseButton-primary"]:focus,
.stButton > button[data-testid="stBaseButton-primary"]:active {
  outline: none !important; box-shadow: 0 0 0 3px var(--ac-bg) !important;
}

/* ── Tabs ───────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
  background: transparent !important; border-bottom: 1px solid var(--b0) !important;
  gap: 0 !important; padding: 0 !important;
}
[data-baseweb="tab"] {
  font-family: var(--font) !important; font-size: 13px !important; font-weight: 500 !important;
  color: var(--t1) !important; background: transparent !important;
  border-bottom: 2px solid transparent !important; padding: .5rem 1rem !important;
  transition: color var(--ease), border-color var(--ease) !important;
}
[data-baseweb="tab"]:hover { color: var(--t0) !important; }
[aria-selected="true"][data-baseweb="tab"] {
  color: var(--ac) !important; border-bottom-color: var(--ac) !important; font-weight: 600 !important;
}
[data-baseweb="tab-panel"] { padding: .75rem 0 0 !important; }

/* ── Progress ───────────────────────────────────────────── */
[data-testid="stProgress"] { margin: .25rem 0 .5rem !important; }
[data-testid="stProgress"] [role="progressbar"] {
  background: var(--b0) !important; border-radius: 99px !important;
  height: 4px !important; overflow: hidden !important;
}
[data-testid="stProgress"] [role="progressbar"] > div {
  background: linear-gradient(90deg, var(--ac-dk), var(--ac)) !important;
  height: 100% !important; border-radius: 99px !important; transition: width .4s ease !important;
}
/* text — anything inside stProgress that is NOT the bar */
[data-testid="stProgress"] p,
[data-testid="stProgress"] > div:not([role="progressbar"]),
[data-testid="stProgress"] + div {
  color: var(--t1) !important; font-family: var(--mono) !important;
  font-size: 11.5px !important; height: auto !important; margin-top: 5px !important;
}

/* ── Expander ───────────────────────────────────────────── */
[data-testid="stExpander"],
[data-testid="stExpander"] details,
[data-testid="stExpander"] details > div,
[data-testid="stExpander"] > div,
[data-testid="stExpanderDetails"] {
  background: var(--s1) !important;
  border: 1px solid var(--b0) !important;
  border-radius: var(--r1) !important;
  overflow: hidden !important;
}
/* Avoid double-border on nested elements */
[data-testid="stExpander"] details,
[data-testid="stExpander"] details > div,
[data-testid="stExpander"] > div,
[data-testid="stExpanderDetails"] {
  border: none !important;
}
[data-testid="stExpander"] summary {
  font-family: var(--font) !important; font-size: 13px !important; font-weight: 500 !important;
  color: var(--t1) !important; padding: .625rem .875rem !important; transition: color var(--ease) !important;
  background: var(--s1) !important;
}
[data-testid="stExpander"] summary:hover { color: var(--t0) !important; }

/* ── Alerts ─────────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: var(--r1) !important; font-family: var(--font) !important;
  font-size: 13px !important; border-left-width: 3px !important;
}

/* ── Dataframe ──────────────────────────────────────────── */
[data-testid="stDataFrame"], [data-testid="stDataFrameResizable"] {
  border: 1px solid var(--b0) !important; border-radius: var(--r1) !important; overflow: hidden !important;
}

/* ── Segmented control — real testids from DOM inspection ── */
/* Inactive button */
[data-testid="stBaseButton-segmented_control"] {
  background: var(--s1) !important;
  color: var(--t1) !important;
  border: 1px solid var(--b0) !important; outline: none !important; box-shadow: none !important;
  font-family: var(--font) !important; font-size: 12.5px !important; font-weight: 500 !important;
  border-radius: 4px !important; padding: .3rem .75rem !important;
  transition: background var(--ease), color var(--ease), border-color var(--ease) !important;
}
[data-testid="stBaseButton-segmented_control"]:hover {
  background: var(--s2) !important; color: var(--t0) !important;
  border-color: var(--b1) !important;
}
/* Active/selected button */
[data-testid="stBaseButton-segmented_controlActive"] {
  background: var(--ac) !important;
  color: #032b13 !important;
  border: 1px solid var(--ac) !important; outline: none !important;
  font-family: var(--font) !important; font-size: 12.5px !important; font-weight: 600 !important;
  border-radius: 4px !important; padding: .3rem .75rem !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.3) !important;
}
/* Wrapper container (find by finding what wraps these buttons) */
[data-testid="stBaseButton-segmented_control"],
[data-testid="stBaseButton-segmented_controlActive"] {
  /* ensure parent bg shows through transparent buttons */
}

/* ── Slider ─────────────────────────────────────────────── */
[data-baseweb="slider"] [role="slider"] {
  background: var(--ac) !important; border-color: var(--ac) !important;
  box-shadow: 0 0 0 4px var(--ac-bg) !important;
}

/* ── Toast ──────────────────────────────────────────────── */
[data-testid="stToast"] {
  background: var(--s1) !important; border: 1px solid var(--b0) !important;
  border-radius: var(--r1) !important; color: var(--t0) !important;
  font-family: var(--font) !important; font-size: 13px !important; box-shadow: var(--sh) !important;
}

/* ── File uploader ───────────────────────────────────────── */
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
  border: none !important;
  background: transparent !important;
  padding: 0 !important;
  min-height: 0 !important;
}
[data-testid="stFileUploaderDropzone"] > div {
  padding: 0 !important;
  min-height: 0 !important;
}
/* Helper text "200MB per file • CSV, DB" */
[data-testid="stFileUploader"] section p,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploader"] section small,
[data-testid="stFileUploaderDropzone"] small {
  color: var(--t1) !important;
  font-family: var(--font) !important;
  font-size: 12px !important;
  margin: 0 !important;
}
/* Upload button — primary accent style so it stands out */
[data-testid="stFileUploader"] section button,
[data-testid="stFileUploaderDropzone"] button {
  background: var(--ac) !important;
  border: none !important;
  border-radius: var(--r0) !important;
  color: #032b13 !important;
  font-family: var(--font) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  padding: .3rem .875rem !important;
  height: 34px !important;
  cursor: pointer !important;
  transition: opacity var(--ease) !important;
  outline: none !important;
  flex-shrink: 0 !important;
}
[data-testid="stFileUploader"] section button:hover,
[data-testid="stFileUploaderDropzone"] button:hover { opacity: .85 !important; }

/* Material icon spans — scoped to testid so expander arrows are NOT affected */
[data-testid="stIconMaterial"] {
  font-family: 'Material Symbols Outlined' !important;
  font-weight: normal !important; font-style: normal !important;
  font-size: 18px !important; line-height: 1 !important;
  display: inline-block !important; white-space: nowrap !important;
  word-wrap: normal !important; direction: ltr !important;
  -webkit-font-smoothing: antialiased !important;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24 !important;
  vertical-align: middle !important;
}

/* ── Widget labels (above inputs, sliders, multiselects) ─── */
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] > div {
  color: var(--t0) !important;
  font-family: var(--font) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}

/* ── Slider ─────────────────────────────────────────────── */
/* Track background */
[data-baseweb="slider"] > div > div:first-child {
  background: var(--b0) !important;
}
/* Filled portion of track */
[data-baseweb="slider"] > div > div:first-child > div:first-child {
  background: var(--ac) !important;
}
/* Thumb */
[data-baseweb="slider"] [role="slider"] {
  background: var(--ac) !important;
  border-color: var(--ac) !important;
  box-shadow: 0 0 0 4px var(--ac-bg) !important;
  outline: none !important;
}
/* Thumb value tooltip */
[data-baseweb="slider"] [role="slider"] div,
[data-baseweb="slider"] [role="slider"] + div {
  background: var(--s2) !important;
  color: var(--t0) !important;
  border: 1px solid var(--b1) !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
  border-radius: 4px !important;
}
/* Tick labels (min/max values shown at ends) */
[data-testid="stSlider"] [data-baseweb="slider-inner-thumb-value"],
[data-testid="stSlider"] p,
[data-testid="stSlider"] span {
  color: var(--t1) !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
}
/* The tick bar (numbers below track) */
[data-testid="stSlider"] ul,
[data-testid="stSlider"] ul li {
  color: var(--t2) !important;
  font-family: var(--mono) !important;
  font-size: 10.5px !important;
}

/* ── Multiselect & Selectbox — full override ─────────────── */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: var(--s2) !important;
  border: 1px solid var(--b0) !important;
  border-radius: var(--r0) !important;
  transition: border-color var(--ease), box-shadow var(--ease) !important;
}
[data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within > div,
[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within > div {
  border-color: var(--ac) !important;
  box-shadow: 0 0 0 3px var(--ac-bg) !important;
}
/* Dropdown chevron / clear icon */
[data-baseweb="select"] svg { color: var(--t1) !important; }
/* Placeholder text */
[data-baseweb="select"] [data-baseweb="select"] input::placeholder { color: var(--t2) !important; }

/* ── Dataframe header ────────────────────────────────────── */
[data-testid="stDataFrame"] > div {
  background: var(--s1) !important;
}
/* Toolbar (column config, download icons) */
[data-testid="stElementToolbarButton"] {
  background: var(--s2) !important;
  border: 1px solid var(--b0) !important;
  border-radius: var(--r0) !important;
  color: var(--t1) !important;
}
[data-testid="stElementToolbarButton"]:hover { color: var(--t0) !important; }

/* ── Misc ───────────────────────────────────────────────── */
hr { border-color: var(--b0) !important; margin: .625rem 0 !important; }
.js-plotly-plot .plotly .xtick text,
.js-plotly-plot .plotly .ytick text { fill: var(--t1) !important; }
.js-plotly-plot .plotly .gridlayer path { stroke: var(--b0) !important; }

/* ── Custom components ───────────────────────────────────── */
.status-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 99px;
  font-family: var(--font); font-size: 11px; font-weight: 600;
  letter-spacing: .05em; text-transform: uppercase;
}
.status-chip.running { background: var(--ac-bg); color: var(--ac); border: 1px solid var(--ac); }
.status-chip.idle    { background: var(--s2); color: var(--t2); border: 1px solid var(--b0); }
.status-chip.done    { background: var(--ac-bg); color: var(--ac); border: 1px solid var(--ac); }
.status-chip.error   { background: var(--er-bg); color: var(--err); border: 1px solid var(--err); }
.status-chip.warn    { background: var(--wa-bg); color: var(--warn); border: 1px solid var(--warn); }
.dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.dot.pulse { animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse {
  0%,100% { opacity:1; transform:scale(1); }
  50%      { opacity:.35; transform:scale(.65); }
}
.empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 3.5rem 1rem; text-align: center; gap: .5rem;
}
/* ── Section helpers (used inside cards) ────────────────── */
.section-label {
  font-family: var(--font) !important; font-size: 10.5px !important;
  font-weight: 700 !important; letter-spacing: .09em !important;
  text-transform: uppercase !important; color: var(--t2) !important;
  margin: 0 0 .5rem 0 !important;
}
hr.section-sep {
  border: none !important; border-top: 1px solid var(--b1) !important;
  margin: .875rem 0 !important; width: 100% !important;
}
.section-note {
  font-family: var(--mono) !important; font-size: 11px !important;
  color: var(--t1) !important; margin: .35rem 0 0 0 !important;
}


.empty-icon {
  width: 44px; height: 44px; border-radius: 10px;
  background: var(--s2); border: 1px solid var(--b0);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; margin-bottom: .5rem;
}
.empty-title { font-family: var(--font); font-size: 13.5px; font-weight: 600; color: var(--t1); }
.empty-sub   { font-family: var(--font); font-size: 12px; color: var(--t2); }
</style>
""", unsafe_allow_html=True)


# ── Translations ───────────────────────────────────────────────────────────
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
        "probing": "Probing latest IDs...", "scrape_done": "Scrape complete",
        "no_session": "No active session", "no_session_sub": "Configure a target GPU and hit Execute to start collecting",
        "wait_scraper": "Waiting for scraper to start...",
        "db_records": "records in database", "filters": "Filters",
        "gpu": "GPU", "bench": "Benchmark", "resolution": "Resolution",
        "score_rng": "Score range", "samples": "Samples", "gpus": "GPUs", "cpus": "CPUs",
        "median_score": "Median score", "sort_by": "Sort by", "cpu_table": "CPU score table",
        "median_by_cpu": "Median score by CPU", "outliers": "Outliers",
        "median_by_gpu": "Median score by GPU",
        "no_data": "No data available", "no_data_sub": "Run the scraper first, or import a .db / .csv file above",
        "gpu_cfg": "GPU Configuration", "perf_metrics": "Performance Metrics",
        "best_fps_eur": "Best FPS/€", "total_cost": "Total cost", "priced_combos": "Priced combos",
        "gpu_price": "GPU Market Price (€)", "cpu_prices": "CPU Market Prices", "action_center": "Action Center",
        "add_to_ranking": "Add to ranking", "save_prices": "Save Prices", "full_breakdown": "Full Breakdown",
        "top_cpus": "Top CPUs", "score_dist": "Score Distribution",
        "clear_status": "Clear Status", "kill_scraper": "Kill Scraper",
        "db": "DB", "killed": "Killed", "quick_eval": "Quick Evaluate",
        "select_cpu_eval": "Select a CPU to check its value in Builds",
        "eval_value": "Evaluate Value", "jump_to_builds": "Jump to Builds",
        "market_val": "Market Value (€)", "tech_specs": "Technical Specs", "median_fps": "Median FPS"
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
        "probing": "Sondeando últimos IDs...", "scrape_done": "Extracción completada",
        "no_session": "Sin sesión activa", "no_session_sub": "Configura una GPU y pulsa Ejecutar para empezar",
        "wait_scraper": "Esperando que el extractor arranque...",
        "db_records": "registros en base de datos", "filters": "Filtros",
        "gpu": "GPU", "bench": "Benchmark", "resolution": "Resolución",
        "score_rng": "Rango de puntos", "samples": "Muestras", "gpus": "GPUs", "cpus": "CPUs",
        "median_score": "Puntuación media", "sort_by": "Ordenar por", "cpu_table": "Tabla de CPUs",
        "median_by_cpu": "Puntuación media por CPU", "median_by_gpu": "Puntuación media por GPU", "outliers": "Valores atípicos",
        "no_data": "Sin datos disponibles", "no_data_sub": "Lanza el extractor primero o importa un archivo .db / .csv",
        "gpu_cfg": "Configuración de GPU", "perf_metrics": "Métricas de Rendimiento",
        "best_fps_eur": "Mejor FPS/€", "total_cost": "Coste total", "priced_combos": "Combos valorados",
        "gpu_price": "Precio de Mercado GPU (€)", "cpu_prices": "Precios de Mercado CPU", "action_center": "Centro de Acción",
        "add_to_ranking": "Añadir al ranking", "save_prices": "Guardar Precios", "full_breakdown": "Desglose Completo",
        "top_cpus": "Top CPUs", "score_dist": "Distribución de Puntos",
        "clear_status": "Limpiar Estado", "kill_scraper": "Matar Extractor",
        "db": "BD", "killed": "Se detuvieron", "quick_eval": "Evaluación Rápida",
        "select_cpu_eval": "Selecciona un CPU para ver su valor en Ensambles",
        "eval_value": "Evaluar Valor", "jump_to_builds": "Ir a Ensambles",
        "market_val": "Valor de Mercado (€)", "tech_specs": "Especificaciones Técnicas", "median_fps": "FPS Medios"
    }
}

# ── Helpers ────────────────────────────────────────────────────────────────
def t(key):
    return T[st.session_state.lang].get(key, key)
def load_data():
    if not Path(DB_PATH).exists():
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql_query("SELECT * FROM scores", conn)
    conn.close()
    return df


def short_gpu(name):
    # 1. Detect if it's a mobile/low-power variant before stripping
    is_mobile = bool(re.search(r'Mobile|Max-Q|Design|Laptop', name, flags=re.IGNORECASE))
    
    # 2. Remove Brand & Vendor noise
    name = re.sub(r'^(NVIDIA|AMD|ATI|ASUS|MSI|GIGABYTE|ZOTAC|EVGA|PALIT|GAINWARD|INNO3D|SAPPHIRE|XFX|POWERCOLOR)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^GeForce\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^Radeon\s*(\(TM\))?\s+', '', name, flags=re.IGNORECASE)
    
    # 3. Strip common technical suffixes and junk
    name = re.sub(r'\s*\(radeonsi[^)]*\)', ' (Linux)',  name, flags=re.IGNORECASE)
    name = re.sub(r'\s+Series$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(TM\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(R\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+Graphics$', '', name, flags=re.IGNORECASE)
    
    # 4. Remove all mobile-related junk to clean the base name
    name = re.sub(r'\s*\(?Mobile|with Max-Q|Design|Laptop\)?', '', name, flags=re.IGNORECASE)
    
    # 5. Re-attach a clean suffix if it was mobile
    res = name.strip()
    if is_mobile:
        res += " (Mobile)"
    
    return res[:40]


def make_bar(df, x, y, color_scale, text_fmt="%{text:,.0f}", height=400):
    fig = px.bar(df, x=x, y=y, orientation="h",
                 template="plotly_dark", color=x,
                 color_continuous_scale=color_scale, text=x)
    fig.update_traces(
        texttemplate=text_fmt, textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11, color="#ddddf0"),
        marker_line_width=0,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#6868a0"),
        showlegend=False, coloraxis_showscale=False,
        margin=dict(l=0, r=70, t=8, b=0), height=height,
        xaxis=dict(showgrid=True, gridcolor="#1e1e30", zeroline=False,
                   tickfont=dict(size=10, family="JetBrains Mono")),
        yaxis=dict(showgrid=False, tickfont=dict(size=11, family="Inter")),
    )
    return fig


def chip(label, kind="idle"):
    dot_cls = "dot pulse" if kind == "running" else "dot"
    return f'<span class="status-chip {kind}"><span class="{dot_cls}"></span>{label}</span>'


def page_header(title, subtitle=""):
    sub = f'<p class="page-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<h2 class="page-title">{title}</h2>{sub}', unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "EN"

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

    # Language Toggle (Compact Segmented Control at Top)
    lang_sel = st.segmented_control(
        "LANG", ["EN", "ES"], 
        default=st.session_state.lang, 
        label_visibility="collapsed",
        key="lang_toggle_sidebar"
    )
    if lang_sel and lang_sel != st.session_state.lang:
        st.session_state.lang = lang_sel
        st.rerun()

    st.divider()

    # Navigation Labels (Simplified for translation)
    nav_options = {
        "EN": ["Scraper", "Analysis", "Builds"],
        "ES": ["Extractor", "Análisis", "Builds"]
    }
    
    # Programmatic navigation support
    if "pending_nav" in st.session_state:
        st.session_state.main_nav = st.session_state.pop("pending_nav")

    if "main_nav" not in st.session_state:
        st.session_state.main_nav = "Scraper"

    selected_nav = st.radio(
        "", 
        nav_options["EN"], 
        format_func=lambda x: nav_options[st.session_state.lang][nav_options["EN"].index(x)],
        label_visibility="collapsed",
        key="main_nav"
    )
    page = selected_nav

    st.divider()

    if Path(DB_PATH).exists():
        size_kb = Path(DB_PATH).stat().st_size / 1024
        st.caption(f"{t('db')}  ·  {size_kb:.0f} KB")

    # Contextual Scraper Actions
    if page == "Scraper":
        st.markdown(f"### {t('action_center')}")
        if st.button(t("clear_status"), use_container_width=True):
            if Path(STATUS_FILE).exists():
                Path(STATUS_FILE).unlink()
            st.rerun()

        if st.button(t("kill_scraper"), use_container_width=True, type="primary"):
            count = 0
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = " ".join(proc.info.get('cmdline') or [])
                    if CLI_SCRIPT in cmdline:
                        proc.terminate()
                        count += 1
                except:
                    continue
            if Path(STATUS_FILE).exists():
                Path(STATUS_FILE).unlink()
            st.toast(f"{t('killed')} {count} process(es)")
            time.sleep(0.5)
            st.rerun()


# ── State ──────────────────────────────────────────────────────────────────
if "proc" not in st.session_state:
    st.session_state.proc = None

if "filter_gpu" not in st.session_state:
    st.session_state.filter_gpu = None
if "filter_bench" not in st.session_state:
    st.session_state.filter_bench = None
if "filter_res" not in st.session_state:
    st.session_state.filter_res = None


def is_engine_running():
    if st.session_state.proc is not None and st.session_state.proc.poll() is None:
        return True
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


is_running = is_engine_running()


# ══════════════════════════════════════════════════════════════════════════
# SCRAPER
# ══════════════════════════════════════════════════════════════════════════
if page == "Scraper":
    page_header(t("scraper"), t("scraper_sub"))

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

        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
        _, btn_col = st.columns([4, 1])
        with btn_col:
            if is_running:
                if st.button(t("stop"), use_container_width=True, key="btn_stop", type="primary"):
                    if st.session_state.proc: st.session_state.proc.terminate()
                    if Path(STATUS_FILE).exists():
                        try:
                            import json, psutil
                            with open(STATUS_FILE) as f: s = json.load(f)
                            pid = s.get("pid")
                            if pid and psutil.pid_exists(pid): psutil.Process(pid).terminate()
                            s["status"] = "stopped"; json.dump(s, open(STATUS_FILE, "w"))
                        except: pass
                    st.session_state.proc = None
                    st.rerun()
            else:
                if st.button(t("execute"), use_container_width=True, key="btn_start", type="primary"):
                    if Path(STATUS_FILE).exists(): Path(STATUS_FILE).unlink()
                    
                    # Process multi-GPU input
                    gpus = [g.strip() for g in gpu_input.split(",") if g.strip()]
                    
                    # Modular CLI Arguments (cli.py)
                    cmd = [
                        PYTHON, CLI_SCRIPT, 
                        "--start-id", str(int(s_id)), 
                        "--end-id", str(int(e_id)), 
                        "--stride", str(int(stride)), 
                        "--max-results", str(int(max_r)), 
                        "--workers", str(int(wrk)), 
                        "--delay", str(dly), 
                        "--db", DB_PATH
                    ]
                    
                    if gpus:
                        cmd += ["--gpu-filter"] + gpus
                    if bench_t:
                        cmd += ["--benchmark-types"] + bench_t
                    
                    import os, subprocess, time
                    st.session_state.proc = subprocess.Popen(cmd, stdout=open("scraper.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                    st.toast(f"Scraper started ({len(gpus)} GPUs)")
                    time.sleep(0.5); st.rerun()

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    col_left, col_right = st.columns([1.1, 1.3])

    @st.fragment(run_every=2)
    def _scraper_status():
        _running = is_engine_running()

        if _running and not Path(STATUS_FILE).exists():
            with st.container(border=True):
                st.markdown(
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'margin-bottom:.75rem">'
                    f'<span style="font-size:11px;font-weight:600;letter-spacing:.08em;'
                    f'text-transform:uppercase;color:var(--t2)">{t("session")}</span>'
                    f'{chip("INITIALIZING", "running")}</div>',
                    unsafe_allow_html=True
                )
                st.caption(t("wait_scraper"))
            return

        if not Path(STATUS_FILE).exists() and not _running:
            with st.container(border=True):
                st.markdown(f"""
                <div class="empty-state">
                  <div class="empty-icon">◉</div>
                  <div class="empty-title">{t("no_session")}</div>
                  <div class="empty-sub">{t("no_session_sub")}</div>
                </div>
                """, unsafe_allow_html=True)
            return

        if not Path(STATUS_FILE).exists():
            return

        stats = None
        for _ in range(3):
            try:
                with open(STATUS_FILE, encoding="utf-8") as f:
                    stats = json.load(f)
                break
            except (json.JSONDecodeError, OSError):
                time.sleep(0.1)

        if not stats:
            return

        remaining   = stats['total_ids'] - stats['checked']
        eta_s       = int(remaining / stats['speed']) if stats.get('speed', 0) > 0 else 0
        eta_str     = f"{eta_s//3600}h {(eta_s%3600)//60}m" if eta_s > 0 else "---"
        hit_rate    = f"{stats['found']/stats['checked']*100:.1f}%" if stats['checked'] > 0 else "---"
        status      = stats['status']
        status_kind = "running" if status in ("running", "probing", "initializing") else \
                      "done"    if status == "finished" else \
                      "error"   if "crashed" in status else "idle"

        with st.container(border=True):
            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'margin-bottom:.75rem">'
                f'<span style="font-size:11px;font-weight:600;letter-spacing:.08em;'
                f'text-transform:uppercase;color:var(--t2)">{t("session")}</span>'
                f'{chip(status.upper(), status_kind)}</div>',
                unsafe_allow_html=True
            )
            m1, m2, m3 = st.columns(3)
            m1.metric(t("checked"),  f"{stats['checked']:,}")
            m2.metric(t("found"),    f"{stats['found']:,}")
            m3.metric(t("hit_rate"), hit_rate)
            m4, m5, m6 = st.columns(3)
            m4.metric(t("speed"),   f"{stats.get('speed', 0):.1f} /s")
            m5.metric(t("eta"),     eta_str)
            m6.metric(t("skipped"), f"{stats.get('skipped', 0):,}")

            if stats['total_ids'] > 0:
                pct = min(stats['checked'] / stats['total_ids'], 1.0)
                st.markdown(
                    f'<p class="section-note" style="margin:.75rem 0 .25rem">'
                    f'{pct*100:.1f}% &nbsp;·&nbsp; {stats["checked"]:,} / {stats["total_ids"]:,}</p>',
                    unsafe_allow_html=True
                )
                st.progress(pct)

            if status == "probing":
                st.caption(t("probing"))
            elif status == "finished":
                st.success(t("scrape_done"))
            elif "crashed" in status:
                st.error(f"Crash: {status}")

        df_live = load_data()
        if not df_live.empty:
            df_live["score"] = pd.to_numeric(df_live["score"], errors="coerce")
            df_live = df_live.dropna(subset=["score", "cpu"])

            tab1, tab2 = st.tabs([t("score_dist"), t("top_cpus")])
            with tab1:
                with st.container(border=True):
                    fig_h = px.histogram(df_live, x="score", nbins=40,
                                         template="plotly_dark",
                                         color_discrete_sequence=["#4ade80"])
                    fig_h.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter", color="#6868a0"),
                        margin=dict(l=0, r=0, t=8, b=0), height=260, bargap=0.05,
                        xaxis=dict(showgrid=True, gridcolor="#1e1e30",
                                   tickfont=dict(family="JetBrains Mono", size=10)),
                        yaxis=dict(showgrid=True, gridcolor="#1e1e30",
                                   tickfont=dict(family="JetBrains Mono", size=10)),
                    )
                    fig_h.update_traces(marker_line_width=0)
                    st.plotly_chart(fig_h, use_container_width=True,
                                    config={"displayModeBar": False})
            with tab2:
                with st.container(border=True):
                    top_cpus = df_live["cpu"].value_counts().head(15).reset_index()
                    top_cpus.columns = ["CPU", "count"]
                    top_cpus = top_cpus.iloc[::-1].reset_index(drop=True)
                    fig_c = make_bar(top_cpus, "count", "CPU",
                                     [[0, "#0d3320"], [1, "#4ade80"]],
                                     height=max(260, len(top_cpus) * 26))
                    st.plotly_chart(fig_c, use_container_width=True,
                                    config={"displayModeBar": False})

    with col_left:
        _scraper_status()

    with col_right:
        # ── Results table ──────────────────────────────────────────────────────
        df_tbl = load_data()
        if not df_tbl.empty:
            df_tbl["score"] = pd.to_numeric(df_tbl["score"], errors="coerce")
            df_tbl = df_tbl.dropna(subset=["score"])
            if "score_id" in df_tbl.columns:
                df_tbl = df_tbl.sort_values("score_id", ascending=False)

            cols_want = ["score_id", "cpu", "gpu", "score", "benchmark_type", "resolution", "os", "submitted_date"]
            cols_show = [c for c in cols_want if c in df_tbl.columns]
            
            # Map to Capital Case
            header_map = {
                "score_id": "Score ID", "cpu": "CPU", "gpu": "GPU", "score": "Score",
                "benchmark_type": "Benchmark", "resolution": "Resolution",
                "os": "OS", "submitted_date": "Date"
            }
            df_display = df_tbl[cols_show].head(500).rename(columns=header_map)

            st.markdown(
                f'<p class="section-label" style="margin:0 0 .5rem 0">'
                f'{len(df_tbl):,} {t("db_records")}</p>',
                unsafe_allow_html=True
            )
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                height=650,
            )

        if Path("scraper.log").exists():
            with st.expander("Scraper log"):
                try:
                    log_text = Path("scraper.log").read_text(encoding="utf-8", errors="replace")
                    tail = log_text[-5000:] if len(log_text) > 5000 else log_text
                    st.code(tail, language="")
                except OSError:
                    st.caption("Cannot read log")


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ══════════════════════════════════════════════════════════════════════════
elif page == "Analysis":
    page_header(t("analysis"), t("analysis_sub"))

    uploaded = st.file_uploader(
        "Import file (CSV or DB)", type=["csv", "db"],
        label_visibility="collapsed",
        help="Upload a gpumagick.db or exported CSV to analyse a different dataset",
    )

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
            st.markdown(f"""
            <div class="empty-state">
              <div class="empty-icon">≡</div>
              <div class="empty-title">{t("no_data")}</div>
              <div class="empty-sub">{t("no_data_sub")}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        df["score"]     = pd.to_numeric(df["score"], errors="coerce")
        df["fps"]       = pd.to_numeric(df["fps"],   errors="coerce")
        df              = df.dropna(subset=["score", "cpu", "gpu"])
        df["gpu_short"] = df["gpu"].apply(short_gpu)

        all_gpus  = sorted(df["gpu_short"].dropna().unique())
        all_bench = sorted(df["benchmark_type"].dropna().unique())
        all_res   = sorted(df["resolution"].dropna().unique())

        # ── Filter bar — GPU is the primary action ─────────────────────────────
        if "an_gpu"   not in st.session_state: st.session_state.an_gpu   = []
        if "an_bench" not in st.session_state: st.session_state.an_bench = all_bench
        if "an_res"   not in st.session_state:
            st.session_state.an_res = ["1920x1080"] if "1920x1080" in all_res else all_res

        with st.container(border=True):
            fc1, fc2, fc3 = st.columns([3, 1.5, 1.5])
            fc1.caption(t("gpu"))
            fc2.caption(t("bench"))
            fc3.caption(t("resolution"))
            sel_gpus  = fc1.multiselect(t("gpu"),       all_gpus,  key="an_gpu",   label_visibility="collapsed")
            sel_bench = fc2.multiselect(t("bench"),      all_bench, key="an_bench", label_visibility="collapsed")
            sel_res   = fc3.multiselect(t("resolution"), all_res,   key="an_res",   label_visibility="collapsed")

        if not sel_gpus:
            with st.container(border=True):
                st.markdown(f"""
                <div class="empty-state">
                  <div class="empty-icon">◈</div>
                  <div class="empty-title">Selecciona una o más GPUs</div>
                  <div class="empty-sub">Elige las GPUs que quieres comparar — RX 580, GTX 1650, etc.</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            fdf = df[
                df["gpu_short"].isin(sel_gpus) &
                df["benchmark_type"].isin(sel_bench if sel_bench else all_bench) &
                df["resolution"].isin(sel_res if sel_res else all_res)
            ]

            if fdf.empty:
                st.warning("No hay datos para los filtros actuales.")
            else:
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
                    # ── Modo una GPU: ranking de CPUs ──────────────────────────
                    stats = (
                        cpu_gpu[cpu_gpu["gpu_short"] == sel_gpus[0]]
                        .sort_values("Median", ascending=False)
                        .reset_index(drop=True)
                        .rename(columns={"cpu": "CPU"})
                    )
                    max_med = stats["Median"].max()
                    stats["Tier"] = stats["Median"].apply(lambda x:
                        "Top"  if x >= max_med * 0.97 else
                        "Good" if x >= max_med * 0.92 else ""
                    )

                    _sc1, _sc2 = st.columns([2, 1])
                    sort_by = _sc1.segmented_control(
                        t("sort_by"), ["Median", "Samples"],
                        default="Median", key="sort_cpu"
                    )
                    an_metric_sg = _sc2.segmented_control(
                        "Metric", ["Score", "FPS"], default="Score", key="an_metric_sg"
                    ) if has_fps else "Score"
                    if sort_by == "Samples":
                        stats = stats.sort_values("Samples", ascending=False).reset_index(drop=True)

                    tcol, gcol = st.columns([1, 1.4])
                    with tcol:
                        with st.container(border=True):
                            st.caption(t("cpu_table"))
                            _sg_cols = ["CPU", "Median"] + (["MedianFPS"] if has_fps else []) + ["Samples", "Tier"]
                            st.dataframe(stats[_sg_cols],
                                         use_container_width=True, hide_index=True, height=420)
                        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
                        with st.container(border=True):
                            st.markdown(f'<p class="section-label">{t("quick_eval")}</p>', unsafe_allow_html=True)
                            st.caption(t("select_cpu_eval"))
                            ec, bc = st.columns([2, 1])
                            cpu_to_eval = ec.selectbox("CPU", stats["CPU"].tolist(), label_visibility="collapsed")
                            if bc.button(t("eval_value"), use_container_width=True, type="primary"):
                                st.session_state.jump_cpu = cpu_to_eval
                                st.session_state.pending_nav = "Builds"
                                st.rerun()
                    with gcol:
                        with st.container(border=True):
                            top20 = stats.head(20).iloc[::-1].reset_index(drop=True)
                            _sg_x = "MedianFPS" if an_metric_sg == "FPS" and has_fps else "Median"
                            fig = make_bar(top20, _sg_x, "CPU",
                                           [[0, "#0a2e18"], [0.5, "#16a34a"], [1, "#4ade80"]],
                                           height=420)
                            vals = top20[_sg_x]
                            if not vals.empty and vals.max() > vals.min():
                                vr = vals.max() - vals.min()
                                fig.update_xaxes(range=[vals.min() - vr * 0.05, vals.max() + vr * 0.02])
                            _sg_lbl = t("median_fps") if an_metric_sg == "FPS" else t("median_by_cpu")
                            st.caption(f"{_sg_lbl}  ·  {sel_gpus[0]}")
                            st.plotly_chart(fig, use_container_width=True,
                                            config={"displayModeBar": False})

                else:
                    # ── Modo comparación: varias GPUs lado a lado ──────────────

                    # Tabla pivotada: una fila por CPU, una columna por GPU
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
                            lambda x: "✓" if pd.notna(x) and x >= best * 0.95 else ""
                        )

                    tier_cols = [f"✓ {g}" for g in gpu_cols]
                    _delta_cols = ["Δ%"] if "Δ%" in pivot_raw.columns else []
                    disp_df = pivot_raw[["CPU"] + gpu_cols + _delta_cols + tier_cols].copy()

                    an_metric = st.segmented_control(
                        "Metric", ["Score", "FPS"], default="Score", key="an_metric_mg"
                    ) if has_fps else "Score"

                    tcol, gcol = st.columns([1, 1.4])
                    with tcol:
                        with st.container(border=True):
                            st.caption(f"{t('median_by_cpu')}  ·  {len(gpu_cols)} GPUs  ·  ✓ = top 5%")
                            st.dataframe(disp_df, use_container_width=True,
                                         hide_index=True, height=460)
                        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
                        with st.container(border=True):
                            st.markdown(f'<p class="section-label">{t("quick_eval")}</p>', unsafe_allow_html=True)
                            st.caption(t("select_cpu_eval"))
                            ec, bc = st.columns([2, 1])
                            cpu_to_eval = ec.selectbox("CPU", pivot_raw["CPU"].tolist(), label_visibility="collapsed")
                            if bc.button(t("eval_value"), use_container_width=True, type="primary"):
                                st.session_state.jump_cpu = cpu_to_eval
                                st.session_state.pending_nav = "Builds"
                                st.rerun()
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
                                _colors = ["#4ade80", "#60a5fa", "#f472b6", "#fb923c"]
                                _best_med = gpu_summary["Median"].max()
                                _num_fmt = ".1f" if an_metric == "FPS" else ".0f"
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
                                    showlegend=False, coloraxis_showscale=False,
                                    margin=dict(l=0, r=160, t=8, b=0),
                                    height=max(200, len(gpu_summary) * 70),
                                    xaxis=dict(showgrid=True, gridcolor="#1e1e30", zeroline=False,
                                               tickfont=dict(size=10, family="JetBrains Mono")),
                                    yaxis=dict(showgrid=False, tickfont=dict(size=13, family="Inter")),
                                )
                                _ovw_lbl = t("median_fps") if an_metric == "FPS" else t("median_by_gpu")
                                st.caption(f"{_ovw_lbl}  ·  {len(_ovw_fdf):,} samples")
                                st.plotly_chart(fig_ovw, use_container_width=True,
                                                config={"displayModeBar": False})

                        with tab_cpu:
                            with st.container(border=True):
                                # Each GPU contributes its top CPUs so no GPU is crowded out
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
                                top_cpus = sorted(_top, key=lambda c: _piv_rank.get(c, 9999))[:20]
                                chart_df = cpu_gpu[cpu_gpu["cpu"].isin(top_cpus)].copy()
                                chart_df = chart_df.rename(columns={"cpu": "CPU", "gpu_short": "GPU"})
                                chart_df["CPU"] = pd.Categorical(
                                    chart_df["CPU"],
                                    categories=top_cpus[::-1],
                                    ordered=True,
                                )
                                chart_df = chart_df.sort_values("CPU")

                                _cpu_x = "MedianFPS" if an_metric == "FPS" and "MedianFPS" in chart_df.columns else "Median"
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
                                    legend=dict(
                                        orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                                        font=dict(family="Inter", size=11, color="#ddddf0"),
                                        bgcolor="rgba(0,0,0,0)",
                                    ),
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
                                st.plotly_chart(fig, use_container_width=True,
                                                config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════
# BUILDS
# ══════════════════════════════════════════════════════════════════════════
elif page == "Builds":
    page_header(t("builds"), t("builds_sub"))

    df = load_data()
    if df.empty:
        with st.container(border=True):
            st.markdown(f'''
            <div class="empty-state">
              <div class="empty-icon">◈</div>
              <div class="empty-title">{t("no_data")}</div>
              <div class="empty-sub">{t("no_data_sub")}</div>
            </div>
            ''', unsafe_allow_html=True)
        st.stop()

    df["fps"]       = pd.to_numeric(df["fps"],   errors="coerce")
    df["score"]     = pd.to_numeric(df["score"], errors="coerce")
    df["gpu_short"] = df["gpu"].apply(short_gpu)
    df              = df.dropna(subset=["score", "cpu", "gpu"])

    saved_prices = load_cpu_prices()
    gpu_options  = sorted(df["gpu_short"].dropna().unique())

    # B3: 1. Fila Superior (Top Bar) ──────────────────────────────────────────
    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        top_c1, top_c2, top_c3 = st.columns([1.5, 2, 2.5])
        
        with top_c1:
            st.caption(t("gpu_cfg"))
            sel_gpus = st.multiselect(
                t("gpu"), gpu_options,
                default=st.session_state.filter_gpu if st.session_state.filter_gpu is not None else ([gpu_options[0]] if gpu_options else []),
                label_visibility="collapsed",
            )
            st.session_state.filter_gpu = sel_gpus
            
        with top_c2:
            st.caption(t("filters"))
            if not sel_gpus:
                bench_opts = []
                res_opts = []
            else:
                sel_gpu_full = set()
                for g in sel_gpus: sel_gpu_full.update(df[df["gpu_short"] == g]["gpu"].unique())
                gpu_mask   = df["gpu"].isin(sel_gpu_full)
                bench_opts = sorted(df[gpu_mask]["benchmark_type"].dropna().unique())
                res_opts   = sorted(df[gpu_mask]["resolution"].dropna().unique())

            sel_bench = st.multiselect(t("bench"), bench_opts, default=st.session_state.filter_bench if st.session_state.filter_bench is not None else (["FurMark (GL)"] if "FurMark (GL)" in bench_opts else bench_opts[:1]), label_visibility="collapsed", disabled=not sel_gpus)
            st.session_state.filter_bench = sel_bench
            
            sel_res = st.multiselect(t("resolution"), res_opts, default=st.session_state.filter_res if st.session_state.filter_res is not None else (["1920x1080"] if "1920x1080" in res_opts else res_opts[:1]), label_visibility="collapsed", disabled=not sel_gpus)
            st.session_state.filter_res = sel_res
            min_samples = st.slider(f"{t('samples')} / CPU", 1, 20, 3, disabled=not sel_gpus)
            
        with top_c3:
            st.caption(t("perf_metrics"))
            kpi_placeholder = st.empty() # B3: Placeholder para KPIs

    if not sel_gpus:
        st.info("Select one or more GPUs to continue")
        st.stop()

    # Calcular combo_stats
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

    # B3: 2. División Inferior (Bottom Split) ─────────────────────────────────
    bot_left, bot_right = st.columns([1, 2])

    with bot_left:
        # 1. GPU Price & Specs Editor
        with st.container(border=True):
            st.caption(t("gpu_price"))
            gpu_stats = combo_stats.groupby("gpu_short").agg(Samples=("samples", "sum")).reset_index()
            gpu_stats = gpu_stats.rename(columns={"gpu_short": "GPU"})
            gpu_stats["Price (€)"] = gpu_stats["GPU"].apply(lambda g: int(saved_prices.get(f"gpu_price:{g}", 80)))
            
            gpu_price_ed = st.data_editor(
                gpu_stats,
                column_config={
                    "GPU": st.column_config.TextColumn("GPU", disabled=True),
                    "Samples": st.column_config.NumberColumn("Samples", disabled=True),
                    "Price (€)": st.column_config.NumberColumn(t("market_val"), min_value=0, step=5, format="%d €")
                },
                hide_index=True, use_container_width=True, key="gpu_p_ed"
            )
            gpu_price_map = dict(zip(gpu_price_ed["GPU"], gpu_price_ed["Price (€)"]))

        # 2. CPU Price & Specs Editor
        top_cpus_idx = combo_stats.groupby("cpu")["samples"].sum().sort_values(ascending=False).head(20).index.tolist()
        top_cpus = top_cpus_idx
        
        # Priority for jumped CPU
        jump_cpu = st.session_state.get("jump_cpu")
        if jump_cpu and jump_cpu not in top_cpus:
            top_cpus.insert(0, jump_cpu)

        # Prepare CPU Editor Data
        cpu_metrics = combo_stats.groupby("cpu").agg(
            Samples=("samples", "sum"),
            Median_Score=("score_med", "median")
        ).reset_index()
        
        _cpu_rows = []
        for cpu in top_cpus:
            price = saved_prices.get(cpu, 0)
            if price == 0:
                price = next((v for k, v in saved_prices.items() if isinstance(v, (int, float)) and not k.startswith("gpu_price:") and (k.lower() in cpu.lower() or cpu.lower() in k.lower())), 0)
            
            metrics = cpu_metrics[cpu_metrics["cpu"] == cpu].iloc[0] if cpu in cpu_metrics["cpu"].values else {"Samples": 0, "Median_Score": 0}
            _cpu_rows.append({
                "CPU": cpu, 
                "Samples": int(metrics["Samples"]),
                "Median Score": int(metrics["Median_Score"]),
                "Price (€)": int(price)
            })

        with st.container(border=True):
            st.caption(f"{t('cpu_prices')}  ·  top {len(_cpu_rows)}")
            cpu_price_ed = st.data_editor(
                pd.DataFrame(_cpu_rows),
                column_config={
                    "CPU": st.column_config.TextColumn("CPU", disabled=True),
                    "Samples": st.column_config.NumberColumn("Samples", disabled=True),
                    "Median Score": st.column_config.NumberColumn("Median Score", disabled=True),
                    "Price (€)": st.column_config.NumberColumn(t("market_val"), min_value=0, step=5, format="%d €")
                },
                hide_index=True, use_container_width=True, key="cpu_p_ed",
                height=min(400, max(120, len(_cpu_rows) * 35 + 42)),
            )

            st.markdown('<hr class="section-sep">', unsafe_allow_html=True)

            with st.container(border=True):
                st.caption(t("action_center"))
                shown = set(cpu_price_ed["CPU"].tolist())
                available = [c for c in all_cpus if c not in shown]
                if available:
                    a1, a2 = st.columns([2, 1])
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
                    st.toast("Prices saved")

    # ── CÁLCULO DE RESULTADOS Y KPIs ──────────────────────────────────────────
    if combo_stats.empty:
        with bot_right:
            with st.container(border=True):
                st.markdown(f'''
                <div class="empty-state">
                  <div class="empty-icon">◈</div>
                  <div class="empty-title">{t("no_data")}</div>
                  <div class="empty-sub">Selecciona una GPU con datos disponibles</div>
                </div>
                ''', unsafe_allow_html=True)
        # Rellenar KPI vacío
        with kpi_placeholder.container():
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(t("best_fps_eur"), "—"); m2.metric("Median FPS", "—"); m3.metric(t("total_cost"), "—"); m4.metric(t("priced_combos"), 0)
    else:
        cpu_price_final = dict(zip(cpu_price_ed["CPU"], cpu_price_ed["Price (€)"]))
        priced = combo_stats.copy()
        priced["cpu_price"] = priced["cpu"].map(cpu_price_final).fillna(0).astype(int)
        priced["gpu_price"] = priced["gpu_short"].map(gpu_price_map).fillna(0).astype(int)
        priced = priced[priced["cpu_price"] > 0].copy()

        if priced.empty:
            with bot_right:
                with st.container(border=True):
                    st.info("Enter CPU prices in the left column to view the FPS/€ ranking")
            # Rellenar KPI vacío
            with kpi_placeholder.container():
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(t("best_fps_eur"), "—"); m2.metric("Median FPS", "—"); m3.metric(t("total_cost"), "—"); m4.metric(t("priced_combos"), 0)
        else:
            priced["total_eur"] = priced["cpu_price"] + priced["gpu_price"]
            priced["fps_eur"]   = (priced["fps_med"] / priced["total_eur"]).round(4)
            priced["score_eur"] = (priced["score_med"] / priced["total_eur"]).round(2)
            priced = priced.sort_values("fps_eur", ascending=False, na_position="last").reset_index(drop=True)

            fps_priced = priced.dropna(subset=["fps_eur"])
            best = fps_priced.iloc[0] if not fps_priced.empty else None

            # B3: Inyectar KPIs calculados en el placeholder superior
            with kpi_placeholder.container():
                if best is not None:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric(t("best_fps_eur"),   f"{best['fps_eur']:.4f}")
                    m2.metric("Median FPS",   f"{best['fps_med']:.0f}" if pd.notna(best["fps_med"]) else "—")
                    m3.metric(t("total_cost"),   f"{int(best['total_eur'])} €")
                    m4.metric(t("priced_combos"), len(fps_priced))

            # Gráfico Principal
            with bot_right:
                with st.container(border=True):
                    if not fps_priced.empty:
                        if len(sel_gpus) == 1:
                            chart_df = fps_priced.head(25).iloc[::-1].reset_index(drop=True)
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

            # B3: 3. Expander oculto al final para Full Breakdown
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
