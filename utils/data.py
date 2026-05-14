import pandas as pd
import duckdb
import re
from pathlib import Path
from utils.ui import DB_PATH

def load_data():
    if not Path(DB_PATH).exists():
        return pd.DataFrame()
    
    con = duckdb.connect(database=':memory:')
    con.execute("INSTALL sqlite;")
    con.execute("LOAD sqlite;")
    con.execute(f"CALL sqlite_attach('{DB_PATH}');")
    
    df = con.execute("SELECT * FROM scores").df()
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
