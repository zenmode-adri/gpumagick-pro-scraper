import streamlit as st
import pandas as pd
import sqlite3
import re
from pathlib import Path
from utils.ui import DB_PATH

@st.cache_data(ttl=30)
def load_data():
    if not Path(DB_PATH).exists():
        return pd.DataFrame()
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM scores", con)
    con.close()
    return df

def short_gpu(name):
    is_mobile = bool(re.search(r'Mobile|Max-Q|Design|Laptop', name, flags=re.IGNORECASE))
    name = re.sub(r'^(NVIDIA|AMD|ATI|ASUS|MSI|GIGABYTE|ZOTAC|EVGA|PALIT|GAINWARD|INNO3D|SAPPHIRE|XFX|POWERCOLOR)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^GeForce\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^Radeon\s*(\(TM\))?\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(radeonsi[^)]*\)', ' (Linux)',  name, flags=re.IGNORECASE)
    name = re.sub(r'\s+Series$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(TM\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(R\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+Graphics$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(?Mobile|with Max-Q|Design|Laptop\)?', '', name, flags=re.IGNORECASE)
    res = name.strip()
    if is_mobile:
        res += " (Mobile)"
    return res[:40]
