#!/usr/bin/env python3
"""
Scraper de gpumagick.com - v14.2

Cambios respecto a v14.1:
- Submission por chunks (no crea todos los futures de golpe en memoria)
- adaptive_workers implementado (pausa entre chunks si hay errores consecutivos)
- Delay se recupera gradualmente tras errores (antes se quedaba alto para siempre)
- --log-level CLI ahora funciona (no se ignoraba en merge_config)
- Auto-detect de ID inicial actualizado al último ID conocido real
- Regex benchmark_type ampliado para variantes multi-palabra (FurMark Knot X (GL))

Uso:
    python scrape_gpumagick_v14_1.py --start-id 2625523 --end-id 2125523 --stride 1 --workers 8 --delay 0.4 --max-results 2000
"""

import csv
import itertools
import json
import re
import time
import sys
import os
import argparse
import logging
import hashlib
import statistics
import sqlite3
import random
import threading
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Set, Any, Tuple
from collections import defaultdict, Counter
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Falta requests. Instala: pip install requests")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, total=None, desc="", **kwargs):
            self.total = total
            self.n = 0
            self.desc = desc
            if total:
                print(f"{desc}: 0/{total}")
        def update(self, n=1):
            self.n += n
            if self.total and self.n % 10 == 0:
                print(f"{self.desc}: {self.n}/{self.total}")
        def close(self):
            if self.total:
                print(f"{self.desc}: {self.n}/{self.total} ✓")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()


# ============== CONFIGURACIÓN POR DEFECTO ==============
DEFAULT_CONFIG = {
    "vendor_ids": [4098],
    "benchmark_id": 0,
    "preset": "1920x1080",
    "gpu_filter": ["RX 580"],
    "gpu_filter_mode": "substring",
    "gpu_filter_case_sensitive": False,
    "score_min": None,
    "score_max": None,
    "date_from": None,
    "date_to": None,
    "benchmark_types": None,
    "max_results": 2000,
    "max_workers": 6,
    "delay_between_requests": 0.5,
    "min_delay": 0.3,
    "output_csv": "gpumagick_scores.csv",
    "output_json": None,
    "output_md": None,
    "output_sqlite": None,
    "cache_dir": ".gpumagick_cache",
    "cache_ttl_hours": 24,
    "append_mode": False,
    "retries": 3,
    "retry_delay": 2.0,
    "timeout": 15,
    "log_level": "INFO",
    "colored_output": True,
    "normalize_gpu_names": True,
    "check_robots_txt": True,
    "adaptive_workers": True,
    "user_agent_rotation": True,
    "start_id": None,  # Auto-detectado si es None (busca el score más reciente)
    "end_id": None,    # Auto-detectado si es None (start_id - 500000 aprox)
    "stride": 1,
    "sample_mode": False,
    "auto_export_every": 50,  # Exportar parcial cada N resultados
}

VENDOR_NAMES = {
    4098: "AMD",
    4318: "NVIDIA",
    32902: "Intel",
    0: "All",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:137.0) Gecko/20100101 Firefox/137.0",
]

BASE_URL = "https://gpumagick.com"
KNOWN_LAST_ID = 2625523  # Último ID válido confirmado (2026-05-11)
CHUNK_SIZE = 500          # Futures en vuelo simultáneamente


# ============== COLORES ============
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"


def c(text: str, color: str = "", bold: bool = False, bg: str = "") -> str:
    if not CONFIG.get("colored_output", True):
        return text
    prefix = (Colors.BOLD if bold else "") + bg
    return f"{prefix}{color}{text}{Colors.RESET}"


def banner(text: str, color: str = Colors.CYAN):
    w = 70
    print(c("=" * w, color, bold=True))
    print(c(f" {text}", color, bold=True))
    print(c("=" * w, color, bold=True))


def section(text: str, color: str = Colors.BLUE):
    print(c(f"\n{'─' * 70}", color))
    print(c(f" {text}", color, bold=True))
    print(c(f"{'─' * 70}", color))


# ============== CONFIG PERSISTENTE ============
def get_config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    else:
        base = Path.home() / ".config"
    cfg_dir = base / "gpumagick"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


def get_config_file() -> Path:
    return get_config_dir() / "config.json"


def load_persistent_config() -> Optional[Dict]:
    cfg_file = get_config_file()
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Error leyendo config guardada: {e}")
    return None


def save_persistent_config(cfg: Dict):
    cfg_file = get_config_file()
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(c(f"✓ Config guardada en: {cfg_file}", Colors.GREEN))


def reset_persistent_config():
    cfg_file = get_config_file()
    if cfg_file.exists():
        cfg_file.unlink()
        print(c(f"✓ Config eliminada: {cfg_file}", Colors.GREEN))
    else:
        print("No había config guardada.")


def show_config(cfg: Dict):
    print("=" * 60)
    print(" CONFIGURACIÓN ACTUAL")
    print("=" * 60)
    for key, val in sorted(cfg.items()):
        val_str = json.dumps(val, ensure_ascii=False)
        if len(val_str) > 50:
            val_str = val_str[:47] + "..."
        print(f"  {key:30s} = {val_str}")
    print("=" * 60)
    print(f"Archivo: {get_config_file()}")


def edit_config_interactive():
    cfg = load_persistent_config() or dict(DEFAULT_CONFIG)
    print("=" * 60)
    print(" EDITOR DE CONFIGURACIÓN")
    print("=" * 60)
    print("Deja vacío para mantener el valor actual.")
    print("Presiona Ctrl+C en cualquier momento para cancelar sin guardar.\n")

    try:
        prompts = {
            "vendor_ids": "Vendor IDs [4098=AMD, 4318=NVIDIA, 32902=Intel] (coma)",
            "preset": "Preset resolución (1920x1080, 2560x1440, 3840x2160)",
            "gpu_filter": "Filtro GPU (coma, ej: RX 580, RX 570)",
            "gpu_filter_mode": "Modo filtro (exact/substring/regex)",
            "gpu_filter_case_sensitive": "¿Case sensitive? (true/false)",
            "score_min": "Score mínimo (número o vacío)",
            "score_max": "Score máximo (número o vacío)",
            "date_from": "Fecha desde (YYYY-MM-DD o vacío)",
            "date_to": "Fecha hasta (YYYY-MM-DD o vacío)",
            "benchmark_types": "Benchmarks (ej: FurMark (GL), FurMark (VK) o vacío=todos)",
            "max_results": "Máximo resultados totales",
            "max_workers": "Workers concurrentes",
            "delay_between_requests": "Delay entre requests (segundos)",
            "min_delay": "Delay mínimo ético (segundos)",
            "output_csv": "Archivo CSV salida",
            "output_json": "Archivo JSON salida (vacío=ninguno)",
            "output_md": "Archivo Markdown salida (vacío=ninguno)",
            "output_sqlite": "Archivo SQLite salida (vacío=ninguno)",
            "cache_dir": "Directorio caché (vacío=sin caché)",
            "cache_ttl_hours": "TTL caché en horas",
            "append_mode": "¿Modo append? (true/false)",
            "retries": "Reintentos ante error",
            "retry_delay": "Delay base reintentos (segundos)",
            "timeout": "Timeout requests (segundos)",
            "log_level": "Nivel log (DEBUG/INFO/WARNING/ERROR)",
            "colored_output": "¿Salida coloreada? (true/false)",
            "normalize_gpu_names": "¿Normalizar nombres GPU? (true/false)",
            "check_robots_txt": "¿Verificar robots.txt? (true/false)",
            "adaptive_workers": "¿Workers adaptativos? (true/false)",
            "user_agent_rotation": "¿Rotar User-Agents? (true/false)",
            "start_id": "ID inicial (más alto, vacío = auto-detectar)",
            "end_id": "ID final (más bajo, vacío = auto)",
            "stride": "Saltar N IDs entre requests (1 = todos)",
            "sample_mode": "¿Modo muestreo? (true/false)",
            "auto_export_every": "Exportar parcial cada N resultados",
        }

        type_hints = {
            "vendor_ids": "list_int",
            "gpu_filter": "list_str",
            "benchmark_types": "list_str_or_none",
            "score_min": "int_or_none",
            "score_max": "int_or_none",
            "max_results": "int",
            "max_workers": "int",
            "delay_between_requests": "float",
            "min_delay": "float",
            "cache_ttl_hours": "int",
            "retries": "int",
            "retry_delay": "float",
            "timeout": "int",
            "append_mode": "bool",
            "gpu_filter_case_sensitive": "bool",
            "colored_output": "bool",
            "normalize_gpu_names": "bool",
            "check_robots_txt": "bool",
            "adaptive_workers": "bool",
            "user_agent_rotation": "bool",
            "start_id": "int_or_none",
            "end_id": "int_or_none",
            "stride": "int",
            "sample_mode": "bool",
            "auto_export_every": "int",
        }

        for key, prompt in prompts.items():
            current = cfg.get(key, DEFAULT_CONFIG.get(key, ""))
            current_str = json.dumps(current, ensure_ascii=False)
            print(f"\n  {c(key, Colors.CYAN, bold=True)}")
            print(f"  {prompt}")
            print(f"  Actual: {current_str}")
            user_input = input(f"  Nuevo valor: ").strip()

            if user_input == "":
                continue

            hint = type_hints.get(key, "str")
            try:
                if hint == "list_int":
                    cfg[key] = [int(x.strip()) for x in user_input.split(",") if x.strip()]
                elif hint == "list_str":
                    cfg[key] = [x.strip() for x in user_input.split(",") if x.strip()]
                elif hint == "list_str_or_none":
                    if user_input.lower() in ("none", "null", "vacío", ""):
                        cfg[key] = None
                    else:
                        cfg[key] = [x.strip() for x in user_input.split(",") if x.strip()]
                elif hint == "int_or_none":
                    cfg[key] = int(user_input) if user_input.lower() not in ("none", "null", "") else None
                elif hint == "int":
                    cfg[key] = int(user_input)
                elif hint == "float":
                    cfg[key] = float(user_input)
                elif hint == "bool":
                    cfg[key] = user_input.lower() in ("true", "1", "yes", "si", "sí")
                else:
                    cfg[key] = user_input
            except ValueError:
                print(c(f"  [!] Valor inválido, se mantiene: {current}", Colors.YELLOW))

    except KeyboardInterrupt:
        print(c("\n\n[!] Edición cancelada. No se guardaron cambios.", Colors.YELLOW, bold=True))
        return

    save_persistent_config(cfg)
    print("\n" + "=" * 60)
    print(c(" Configuración guardada.", Colors.GREEN, bold=True))
    print("=" * 60)


# ============== ROBOTS.TXT ============
class RobotsChecker:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.rp = RobotFileParser()
        self.checked = False
        self.allowed = True
        self.crawl_delay = None

    def check(self) -> Tuple[bool, Optional[float]]:
        if not CONFIG.get("check_robots_txt", True):
            return True, None

        try:
            robots_url = urljoin(self.base_url, "/robots.txt")
            self.rp.set_url(robots_url)
            self.rp.read()
            self.allowed = self.rp.can_fetch("*", f"{self.base_url}/scores/")
            self.crawl_delay = self.rp.crawl_delay("*")
            self.checked = True

            if not self.allowed:
                logging.error(f"robots.txt prohíbe scrapear /scores/")
                return False, self.crawl_delay

            if self.crawl_delay:
                logging.info(f"robots.txt solicita crawl-delay: {self.crawl_delay}s")
                return True, self.crawl_delay

            return True, None
        except Exception as e:
            logging.warning(f"No se pudo leer robots.txt: {e}")
            return True, None


# ============== SESSION HTTP ============
class HttpClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Referer": "https://gpumagick.com/scores/",
        })
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.rate_limit_lock = threading.Lock()
        self.last_request_time = 0
        self.min_delay = CONFIG.get("min_delay", 0.3)
        self.current_delay = CONFIG.get("delay_between_requests", 0.5)
        self.error_count = 0
        self.consecutive_errors = 0

    def _get_headers(self) -> Dict[str, str]:
        headers = dict(self.session.headers)
        if CONFIG.get("user_agent_rotation", True):
            headers["User-Agent"] = random.choice(USER_AGENTS)
        else:
            headers["User-Agent"] = USER_AGENTS[0]
        return headers

    def _apply_rate_limit(self):
        with self.rate_limit_lock:
            now = time.time()
            elapsed = now - self.last_request_time
            wait = self.current_delay - elapsed
            if wait > 0:
                time.sleep(wait)
            self.last_request_time = time.time()

    def _adapt_delay(self, status_code: Optional[int] = None, success: bool = True):
        if success:
            self.consecutive_errors = 0
            if self.error_count > 0:
                self.error_count -= 1
            target = CONFIG.get("delay_between_requests", 0.5)
            if self.current_delay > target:
                self.current_delay = max(target, round(self.current_delay * 0.9, 2))
            return

        self.consecutive_errors += 1
        self.error_count += 1

        if status_code == 429:
            self.current_delay = min(self.current_delay * 2, 10.0)
            logging.warning(f"Rate limit detectado. Delay aumentado a {self.current_delay:.1f}s")
        elif status_code in (500, 502, 503, 504):
            self.current_delay = min(self.current_delay * 1.5, 5.0)
            logging.warning(f"Error servidor {status_code}. Delay aumentado a {self.current_delay:.1f}s")

    def get(self, url: str, timeout: int = 15) -> Tuple[Optional[str], bool, Optional[int]]:
        self._apply_rate_limit()
        headers = self._get_headers()

        try:
            r = self.session.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            self._adapt_delay(success=True)
            return r.text, True, r.status_code
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else None
            self._adapt_delay(status_code=status, success=False)
            logging.warning(f"HTTP {status} en {url}")
            return None, False, status
        except Exception as e:
            self._adapt_delay(success=False)
            logging.warning(f"Error en {url}: {e}")
            return None, False, None

    def get_delay(self) -> float:
        return max(self.current_delay, self.min_delay)

    def should_reduce_workers(self) -> bool:
        return self.consecutive_errors >= 3


# ============== CACHÉ CON TTL ============
class Cache:
    def __init__(self, cache_dir: Optional[str], ttl_hours: int = 24):
        self.enabled = cache_dir is not None
        self.dir = Path(cache_dir) if cache_dir else None
        self.ttl = timedelta(hours=ttl_hours)
        if self.enabled and self.dir:
            self.dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16] + ".html"

    def _is_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - mtime < self.ttl

    def get(self, url: str) -> Optional[str]:
        if not self.enabled or not self.dir:
            return None
        path = self.dir / self._key(url)
        if self._is_fresh(path):
            logging.debug(f"[CACHE HIT] {url}")
            return path.read_text(encoding="utf-8")
        return None

    def set(self, url: str, content: str):
        if not self.enabled or not self.dir:
            return
        path = self.dir / self._key(url)
        path.write_text(content, encoding="utf-8")
        logging.debug(f"[CACHE SET] {url}")

    def clear(self):
        if self.enabled and self.dir:
            count = 0
            for f in self.dir.glob("*.html"):
                f.unlink()
                count += 1
            logging.info(f"Caché limpiada ({count} archivos).")


# ============== VALIDACIÓN HTML ============
class HtmlValidator:
    @classmethod
    def validate_detail(cls, html: str, url: str) -> bool:
        if not html or len(html) < 500:
            return False
        if "INVALID SCORE" in html.upper():
            return False
        if "SCORE" not in html and "3D Renderer" not in html:
            return False
        return True


# ============== PARSING ============
class Parser:
    BENCH_TYPE_PATTERN = re.compile(
        r'(FurMark(?:\s+\w+)*\s*\((?:GL|VK)\))',
        re.IGNORECASE
    )

    @classmethod
    def extract_field(cls, html: str, label: str) -> str:
        pattern = (
            r'<th[^>]*>(?:\s*<[^>]+>)*\s*' + re.escape(label) +
            r'\s*(?:</[^>]+>\s*)*</th>\s*<td[^>]*>(?:\s*<[^>]+>)*\s*([^<]+?)\s*(?:<|$)'
        )
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            return re.sub(r"<[^>]+", "", m.group(1)).strip()
        return ""

    @classmethod
    def detect_benchmark_type(cls, html: str) -> str:
        m = cls.BENCH_TYPE_PATTERN.search(html)
        return m.group(1).strip() if m else ""

    @classmethod
    def parse_score_page(cls, html: str, score_id: str) -> Optional[Dict[str, Any]]:
        if not HtmlValidator.validate_detail(html, f"/scores/{score_id}"):
            return None

        data = {
            "score_id": score_id,
            "score": cls.extract_field(html, "SCORE"),
            "fps": cls.extract_field(html, "FPS"),
            "gpu": cls.extract_field(html, "3D Renderer"),
            "resolution": cls.extract_field(html, "Resolution"),
            "duration_ms": cls.extract_field(html, "Duration"),
            "cpu": cls.extract_field(html, "CPU"),
            "os": cls.extract_field(html, "Operating system"),
            "driver": cls.extract_field(html, "graphics driver"),
            "submitted_date": cls.extract_field(html, "Submitted"),
            "benchmark_type": cls.detect_benchmark_type(html),
        }
        if data["duration_ms"]:
            m = re.search(r"(\d+)", data["duration_ms"])
            if m:
                data["duration_ms"] = m.group(1)
        return data


# ============== FILTROS ============
def normalize_gpu_name(name: str) -> str:
    if not CONFIG.get("normalize_gpu_names", True):
        return name
    name = re.sub(r'/PCIe/SSE2$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'/OpenCL$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^AMD\s+Radeon\s+\(TM\)\s+', 'Radeon ', name, flags=re.IGNORECASE)
    name = re.sub(r'^AMD\s+Radeon\s+\(TM\)', 'Radeon', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+\(RADV\s+[^)]+\)', '', name, flags=re.IGNORECASE)
    return name.strip()


def parse_date(date_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d @ %H:%M:%S")
    except ValueError:
        return None


def build_date_filter(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    logging.warning(f"Formato de fecha no reconocido: {date_str}")
    return None


def matches_gpu_filter(gpu_name: str) -> bool:
    filters = CONFIG.get("gpu_filter", [])
    if not filters:
        return True

    mode = CONFIG.get("gpu_filter_mode", "substring")
    case_sensitive = CONFIG.get("gpu_filter_case_sensitive", False)
    flags = 0 if case_sensitive else re.IGNORECASE

    if mode == "exact":
        return gpu_name in filters
    elif mode == "substring":
        gpu_lower = gpu_name if case_sensitive else gpu_name.lower()
        for f in filters:
            f_lower = f if case_sensitive else f.lower()
            if f_lower in gpu_lower:
                return True
        return False
    elif mode == "regex":
        return any(re.search(p, gpu_name, flags) for p in filters)
    else:
        logging.warning(f"Modo de filtro desconocido: {mode}")
        return True


def matches_filters(row: Dict[str, str]) -> bool:
    gpu = row.get("gpu", "")
    if not matches_gpu_filter(gpu):
        return False

    try:
        score = int(row.get("score", "0"))
    except ValueError:
        score = 0
    if CONFIG.get("score_min") is not None and score < CONFIG["score_min"]:
        return False
    if CONFIG.get("score_max") is not None and score > CONFIG["score_max"]:
        return False

    bench_types = CONFIG.get("benchmark_types")
    if bench_types:
        bt = row.get("benchmark_type", "")
        if bt not in bench_types:
            return False

    row_date = parse_date(row.get("submitted_date", ""))
    date_from = build_date_filter(CONFIG.get("date_from"))
    date_to = build_date_filter(CONFIG.get("date_to"))
    if row_date:
        if date_from and row_date < date_from:
            return False
        if date_to and row_date > date_to:
            return False

    return True


# ============== EXPORTADORES ============
class Exporter:
    @staticmethod
    def to_csv(results: List[Dict], path: str, append: bool = False):
        fields = ["score_id", "benchmark_type", "submitted_date", "cpu", "gpu",
                  "score", "fps", "resolution", "duration_ms", "os", "driver", "url"]
        mode = "a" if append and os.path.exists(path) else "w"
        write_header = mode == "w" or not os.path.exists(path)
        with open(path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            if write_header:
                writer.writeheader()
            for row in results:
                writer.writerow({k: row.get(k, "") for k in fields})
        logging.info(f"CSV exportado: {path}")

    @staticmethod
    def to_json(results: List[Dict], path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logging.info(f"JSON exportado: {path}")

    @staticmethod
    def to_sqlite(results: List[Dict], path: str):
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                score_id TEXT PRIMARY KEY,
                benchmark_type TEXT,
                submitted_date TEXT,
                cpu TEXT,
                gpu TEXT,
                gpu_raw TEXT,
                score INTEGER,
                fps REAL,
                resolution TEXT,
                duration_ms INTEGER,
                os TEXT,
                driver TEXT,
                url TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for row in results:
            cursor.execute("""
                INSERT OR REPLACE INTO scores
                (score_id, benchmark_type, submitted_date, cpu, gpu, gpu_raw,
                 score, fps, resolution, duration_ms, os, driver, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("score_id"), row.get("benchmark_type"),
                row.get("submitted_date"), row.get("cpu"),
                row.get("gpu"), row.get("gpu_raw"),
                row.get("score"), row.get("fps"),
                row.get("resolution"), row.get("duration_ms"),
                row.get("os"), row.get("driver"), row.get("url")
            ))
        conn.commit()
        conn.close()
        logging.info(f"SQLite exportado: {path}")

    @staticmethod
    def to_markdown(results: List[Dict], path: str):
        lines = [
            "# GPU Magick Scores Report",
            f"\nGenerado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\nTotal scores: {len(results)}",
            "\n## Resumen por GPU\n",
            "| GPU | Count | Median | Avg |",
            "|-----|-------|--------|-----|",
        ]
        gpu_scores = defaultdict(list)
        for r in results:
            g = r.get("gpu", "?")
            try:
                gpu_scores[g].append(int(r.get("score", 0)))
            except ValueError:
                pass
        for g, scores in sorted(gpu_scores.items(), key=lambda x: -len(x[1])):
            med = int(statistics.median(scores))
            avg = int(statistics.mean(scores))
            lines.append(f"| {g} | {len(scores)} | {med} | {avg} |")

        lines.extend([
            "\n## Detalles\n",
            "| ID | GPU | Benchmark | Score | FPS | CPU | OS |",
            "|----|-----|-----------|-------|-----|-----|----|",
        ])
        for r in results[:100]:
            lines.append(
                f"| {r.get('score_id','')} | {r.get('gpu','')} | {r.get('benchmark_type','')} | "
                f"{r.get('score','')} | {r.get('fps','')} | {r.get('cpu','')} | {r.get('os','')} |"
            )
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        logging.info(f"Markdown exportado: {path}")


# ============== GRÁFICAS ASCII ============
class AsciiCharts:
    @staticmethod
    def bar_chart(data: Dict[str, int], title: str = "", max_width: int = 50) -> str:
        if not data:
            return "Sin datos"

        max_val = max(data.values())
        lines = [f"\n  {title}"] if title else []

        for label, val in sorted(data.items(), key=lambda x: -x[1]):
            bar_len = int((val / max_val) * max_width) if max_val > 0 else 0
            bar = "█" * bar_len
            pct = (val / sum(data.values()) * 100) if sum(data.values()) > 0 else 0
            lines.append(f"  {label:20s} │{bar:<{max_width}s}│ {val:>4} ({pct:5.1f}%)")

        return "\n".join(lines)

    @staticmethod
    def progress_bar(current: int, total: int, width: int = 40) -> str:
        if total == 0:
            return ""
        pct = current / total
        filled = int(width * pct)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {current}/{total} ({pct*100:5.1f}%)"


# ============== SCRAPER POR IDs ============
class GpuMagickIdScraper:
    def __init__(self):
        self.http = HttpClient()
        self.cache = Cache(
            CONFIG.get("cache_dir"),
            CONFIG.get("cache_ttl_hours", 24)
        )
        self.parser = Parser()
        self.exporter = Exporter()
        self.charts = AsciiCharts()
        self.robots = RobotsChecker(BASE_URL)
        self.stats = {
            "requests_total": 0,
            "requests_cached": 0,
            "requests_failed": 0,
            "ids_valid": 0,
            "ids_404": 0,
            "ids_filtered": 0,
            "ids_skipped": 0,
            "target_found": 0,
        }
        self.results: List[Dict] = []
        self.interrupted = False
        self.start_time = time.time()
        self.seen_ids: Set[int] = self._load_seen_ids()

    def _load_seen_ids(self) -> Set[int]:
        seen: Set[int] = set()
        sqlite_path = CONFIG.get("output_sqlite")
        if sqlite_path and Path(sqlite_path).exists():
            try:
                conn = sqlite3.connect(sqlite_path)
                rows = conn.execute("SELECT score_id FROM scores").fetchall()
                conn.close()
                seen = {int(r[0]) for r in rows}
                logging.info(f"DB: {len(seen)} IDs ya conocidos — se saltarán.")
            except Exception as e:
                logging.warning(f"No se pudieron cargar IDs de SQLite: {e}")
        return seen

    def _fetch(self, url: str) -> Tuple[Optional[str], Optional[int]]:
        self.stats["requests_total"] += 1
        cached = self.cache.get(url)
        if cached is not None:
            self.stats["requests_cached"] += 1
            return cached, 200

        html, success, status = self.http.get(url, timeout=CONFIG.get("timeout", 15))
        if not success:
            self.stats["requests_failed"] += 1
            return None, status

        self.cache.set(url, html)
        return html, status

    def _fetch_and_filter(self, score_id: int) -> Optional[Dict]:
        if score_id in self.seen_ids:
            self.stats["ids_skipped"] += 1
            return None

        url = f"{BASE_URL}/scores/{score_id}"
        html, status = self._fetch(url)

        if status == 404:
            self.stats["ids_404"] += 1
            return None

        if html is None:
            return None

        if "INVALID SCORE" in html.upper():
            self.stats["ids_404"] += 1
            return None

        data = self.parser.parse_score_page(html, str(score_id))
        if not data:
            return None

        self.stats["ids_valid"] += 1

        gpu = data.get("gpu", "")
        if matches_gpu_filter(gpu):
            self.stats["target_found"] += 1
        else:
            self.stats["ids_filtered"] += 1
            return None

        try:
            score = int(data.get("score", "0"))
        except ValueError:
            score = 0
        if CONFIG.get("score_min") is not None and score < CONFIG["score_min"]:
            return None
        if CONFIG.get("score_max") is not None and score > CONFIG["score_max"]:
            return None

        bench_types = CONFIG.get("benchmark_types")
        if bench_types:
            bt = data.get("benchmark_type", "")
            if bt not in bench_types:
                return None

        data["gpu"] = normalize_gpu_name(gpu)
        data["gpu_raw"] = gpu
        data["url"] = url
        self.seen_ids.add(score_id)

        return data

    def _print_progress(self, checked: int, total: int, results: List[Dict]):
        """Imprime progreso en tiempo real con gráfica."""
        elapsed = time.time() - self.start_time
        rate = checked / elapsed if elapsed > 0 else 0
        eta = (total - checked) / rate if rate > 0 else 0

        gpu_filter = CONFIG.get("gpu_filter", ["RX 580"])
        target_name = gpu_filter[0] if gpu_filter else "target"

        # Limpiar pantalla solo cada 50 actualizaciones para reducir parpadeo
        if checked % 50 == 0:
            print("\033[2J\033[H", end="")  # Clear screen
        else:
            # Volver al inicio de línea para sobreescribir
            print("\033[H", end="")

        banner(f"Scrapeando gpumagick.com - v14")

        print(f"\n  Buscando: {c(target_name, Colors.CYAN, bold=True)}")
        print(f"  Encontrados: {c(str(self.stats['target_found']), Colors.GREEN, bold=True)}")
        print(f"  IDs revisados: {checked:,} / {total:,}")
        print(f"  Saltados (ya en DB): {self.stats['ids_skipped']:,}")
        print(f"  Válidos totales: {self.stats['ids_valid']:,}")
        print(f"  404/Inválidos: {self.stats['ids_404']:,}")
        print(f"  Filtrados: {self.stats['ids_filtered']:,}")
        print(f"  Velocidad: {rate:.1f} IDs/segundo")
        print(f"  ETA: {timedelta(seconds=int(eta))}")
        print(f"  Delay actual: {self.http.get_delay():.1f}s")

        # Barra de progreso
        print(f"\n  {self.charts.progress_bar(checked, total)}")

        # Gráfica de GPUs encontradas (top 10)
        if results:
            gpu_counts = Counter(r.get("gpu", "?") for r in results)
            print(self.charts.bar_chart(dict(gpu_counts.most_common(10)), "GPUs encontradas:"))

        # Benchmarks
        if results:
            bench_counts = Counter(r.get("benchmark_type", "?") for r in results)
            print(self.charts.bar_chart(dict(bench_counts.most_common(5)), "Benchmarks:"))

        print(f"\n  {c('Presiona Ctrl+C para parar y exportar', Colors.YELLOW)}")
        self._write_status(checked, total)

    def _write_status(self, checked: int, total: int, status: str = "running"):
        elapsed = time.time() - self.start_time
        rate = checked / elapsed if elapsed > 0 else 0
        try:
            with open("status.json", "w", encoding="utf-8") as f:
                json.dump({
                    "pid": os.getpid(),
                    "status": status,
                    "checked": checked,
                    "total_ids": total,
                    "found": self.stats["target_found"],
                    "failed": self.stats["requests_failed"],
                    "skipped": self.stats["ids_skipped"],
                    "speed": round(rate, 2),
                }, f)
        except Exception:
            pass

    def _export_partial(self, results: List[Dict]):
        """Exporta resultados parciales."""
        if not results:
            return

        self.exporter.to_csv(results, CONFIG["output_csv"], CONFIG.get("append_mode", False))

        if CONFIG.get("output_json"):
            self.exporter.to_json(results, CONFIG["output_json"])

        if CONFIG.get("output_sqlite"):
            self.exporter.to_sqlite(results, CONFIG["output_sqlite"])

    def _signal_handler(self, signum, frame):
        """Maneja Ctrl+C exportando inmediatamente."""
        print(c("\n\n[!] Interrupción detectada. Exportando resultados...", Colors.YELLOW, bold=True))
        self.interrupted = True
        self._export_partial(self.results)
        self._print_final_stats()
        sys.exit(0)

    def _print_final_stats(self):
        """Imprime stats finales."""
        elapsed = time.time() - self.start_time

        section("RESULTADOS FINALES")

        gpu_filter = CONFIG.get("gpu_filter", ["RX 580"])
        target_name = gpu_filter[0] if gpu_filter else "target"

        print(f"  GPU buscada: {c(target_name, Colors.CYAN, bold=True)}")
        print(f"  Encontrados: {c(str(self.stats['target_found']), Colors.GREEN, bold=True)}")
        print(f"  IDs revisados: {self.stats['requests_total']:,}")
        print(f"  Tiempo total: {timedelta(seconds=int(elapsed))}")
        print(f"  Velocidad media: {self.stats['requests_total']/elapsed:.1f} IDs/segundo")

        if self.results:
            gpu_counts = Counter(r.get("gpu", "?") for r in self.results)
            print(self.charts.bar_chart(dict(gpu_counts.most_common(15)), "Distribución de GPUs:"))

            bench_counts = Counter(r.get("benchmark_type", "?") for r in self.results)
            print(self.charts.bar_chart(dict(bench_counts.most_common(5)), "Benchmarks:"))

            res_counts = Counter(r.get("resolution", "?") for r in self.results)
            print(self.charts.bar_chart(dict(res_counts.most_common(5)), "Resoluciones:"))

        print(f"\n  {c('Exportado a:', Colors.GREEN)} {CONFIG['output_csv']}")

    def run_scrape(self):
        banner("Scraper gpumagick.com v14.1 - Progreso en tiempo real (fix)")

        # Setup signal handler para Ctrl+C
        signal.signal(signal.SIGINT, self._signal_handler)

        allowed, crawl_delay = self.robots.check()
        if not allowed:
            print(c("[!] robots.txt prohíbe el scraping. Abortando.", Colors.RED, bold=True))
            return
        if crawl_delay:
            print(c(f"[i] robots.txt sugiere delay: {crawl_delay}s", Colors.YELLOW))
            self.http.current_delay = max(self.http.current_delay, crawl_delay)

        start_id = CONFIG.get("start_id")
        end_id = CONFIG.get("end_id")
        stride = CONFIG.get("stride", 100)

        # Auto-detectar start_id si no se especificó
        if start_id is None:
            print(c("[i] Auto-detectando ID inicial...", Colors.YELLOW))
            # Probar desde KNOWN_LAST_ID hacia arriba (por si hay uploads nuevos), luego bajar
            probe_ids = list(range(KNOWN_LAST_ID + 30000, KNOWN_LAST_ID - 1, -5000))
            for test_id in probe_ids:
                url = f"{BASE_URL}/scores/{test_id}"
                html, status = self._fetch(url)
                if html and "INVALID SCORE" not in html.upper():
                    start_id = test_id
                    print(c(f"[✓] ID inicial detectado: {start_id}", Colors.GREEN))
                    break
            if start_id is None:
                start_id = KNOWN_LAST_ID
                print(c(f"[!] No se pudo auto-detectar, usando último conocido: {start_id}", Colors.YELLOW))

        # Auto-detectar end_id si no se especificó
        if end_id is None:
            end_id = max(start_id - 500000, 1)
            print(c(f"[i] ID final auto-calculado: {end_id}", Colors.YELLOW))
        max_results = CONFIG["max_results"]
        auto_export = CONFIG.get("auto_export_every", 50)

        print(f"\n  Rango: {end_id:,} → {start_id:,}")
        print(f"  Stride: {stride}")
        print(f"  Max resultados: {max_results}")
        print(f"  Workers: {CONFIG['max_workers']}")
        print(f"  Delay: {self.http.get_delay():.1f}s")
        print("=" * 70)

        ids_range = range(start_id, end_id - 1, -stride)
        total_ids = len(ids_range)

        print(f"  IDs a verificar: {total_ids:,}")
        print(f"  Auto-export cada: {auto_export} resultados")
        print(f"  Chunk size: {CHUNK_SIZE}")
        print(f"  {c('Presiona Ctrl+C en cualquier momento para parar y exportar', Colors.YELLOW)}")
        print("\n" + "=" * 70)

        checked = 0
        last_export = 0
        done = False

        with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
            ids_iter = iter(ids_range)

            while not done and not self.interrupted:
                chunk = list(itertools.islice(ids_iter, CHUNK_SIZE))
                if not chunk:
                    break

                futures_map = {executor.submit(self._fetch_and_filter, sid): sid for sid in chunk}

                for f in as_completed(futures_map):
                    if self.interrupted:
                        for future in futures_map:
                            future.cancel()
                        done = True
                        break

                    sid = futures_map[f]
                    try:
                        data = f.result()
                    except Exception as e:
                        logging.debug(f"Error en future para ID {sid}: {e}")
                        data = None
                    checked += 1

                    if data:
                        self.results.append(data)

                    if checked % 10 == 0 or data:
                        self._print_progress(checked, total_ids, self.results)

                    if len(self.results) >= last_export + auto_export:
                        self._export_partial(self.results)
                        last_export = len(self.results)

                    if len(self.results) >= max_results:
                        print(c(f"\n✓ Límite de {max_results} resultados alcanzado.", Colors.GREEN))
                        for future in futures_map:
                            if not future.done():
                                future.cancel()
                        done = True
                        break

                # Adaptive workers: pausa entre chunks si hay errores consecutivos
                if not done and CONFIG.get("adaptive_workers", True) and self.http.should_reduce_workers():
                    logging.warning("Errores consecutivos detectados. Pausando 5s antes del siguiente chunk.")
                    time.sleep(5)

        # Export final
        self._export_partial(self.results)
        self._write_status(checked, total_ids, status="finished")
        self._print_final_stats()


# ============== CLI / CONFIG ============
def load_config_from_file(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_config(cli_args: argparse.Namespace, file_config: Optional[Dict] = None,
                 persistent: Optional[Dict] = None) -> Dict:
    cfg = dict(DEFAULT_CONFIG)
    if persistent:
        cfg.update(persistent)
    if file_config:
        cfg.update(file_config)

    if cli_args.vendor is not None:
        cfg["vendor_ids"] = cli_args.vendor
    if cli_args.preset is not None:
        cfg["preset"] = cli_args.preset[0] if len(cli_args.preset) == 1 else cli_args.preset
    if cli_args.workers is not None:
        cfg["max_workers"] = cli_args.workers
    if cli_args.max_results is not None:
        cfg["max_results"] = cli_args.max_results
    if cli_args.output is not None:
        cfg["output_csv"] = cli_args.output
    if cli_args.json_output is not None:
        cfg["output_json"] = cli_args.json_output
    if cli_args.sqlite_output is not None:
        cfg["output_sqlite"] = cli_args.sqlite_output
    if cli_args.md_output is not None:
        cfg["output_md"] = cli_args.md_output
    if cli_args.score_min is not None:
        cfg["score_min"] = cli_args.score_min
    if cli_args.score_max is not None:
        cfg["score_max"] = cli_args.score_max
    if cli_args.date_from is not None:
        cfg["date_from"] = cli_args.date_from
    if cli_args.date_to is not None:
        cfg["date_to"] = cli_args.date_to
    if cli_args.benchmark_type is not None:
        cfg["benchmark_types"] = cli_args.benchmark_type
    if cli_args.gpu_filter is not None:
        cfg["gpu_filter"] = cli_args.gpu_filter
    if cli_args.gpu_filter_mode is not None:
        cfg["gpu_filter_mode"] = cli_args.gpu_filter_mode
    if cli_args.delay is not None:
        cfg["delay_between_requests"] = cli_args.delay
    if cli_args.min_delay is not None:
        cfg["min_delay"] = cli_args.min_delay
    if cli_args.cache_ttl is not None:
        cfg["cache_ttl_hours"] = cli_args.cache_ttl
    if cli_args.no_cache:
        cfg["cache_dir"] = None
    if cli_args.append:
        cfg["append_mode"] = True
    if cli_args.no_color:
        cfg["colored_output"] = False
    if cli_args.no_check_robots_txt:
        cfg["check_robots_txt"] = False
    if cli_args.no_adaptive_workers:
        cfg["adaptive_workers"] = False
    if cli_args.no_user_agent_rotation:
        cfg["user_agent_rotation"] = False
    if cli_args.start_id is not None:
        cfg["start_id"] = cli_args.start_id
    if cli_args.end_id is not None:
        cfg["end_id"] = cli_args.end_id
    if cli_args.stride is not None:
        cfg["stride"] = cli_args.stride
    if cli_args.sample_mode:
        cfg["sample_mode"] = True
    if cli_args.auto_export_every is not None:
        cfg["auto_export_every"] = cli_args.auto_export_every
    cfg["log_level"] = cli_args.log_level

    return cfg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scraper de gpumagick.com v14 - Progreso en tiempo real",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EJEMPLOS:

  # Scrapeo con progreso en tiempo real
  python scrape_gpumagick_v14_1.py --start-id 2626300 --end-id 2126300 --stride 100 --workers 12 --delay 0.3

  # Auto-export cada 25 resultados
  python scrape_gpumagick_v14_1.py --auto-export-every 25 --max-results 500

  # Buscar RX 580 con gráfica en vivo
  python scrape_gpumagick_v14_1.py --gpu-filter "RX 580" --benchmark-type "FurMark (GL)"
        """
    )

    parser.add_argument("command", nargs="?", default="scrape",
                        choices=["scrape", "variants", "debug", "debug2", "clear-cache"],
                        help="Comando (default: scrape)")
    parser.add_argument("args", nargs="*", help="Argumentos adicionales")

    parser.add_argument("--edit", action="store_true", help="Editar config interactivamente")
    parser.add_argument("--show-config", action="store_true", help="Mostrar config actual")
    parser.add_argument("--reset-config", action="store_true", help="Resetear config")
    parser.add_argument("-c", "--config", type=str, help="Archivo JSON temporal")
    parser.add_argument("--gpu-filter", type=str, nargs="+", help="Filtro(s) GPU")
    parser.add_argument("--gpu-filter-mode", type=str, choices=["exact", "substring", "regex"],
                        help="Modo de filtro")
    parser.add_argument("-v", "--vendor", type=int, nargs="+", help="Vendor IDs")
    parser.add_argument("-p", "--preset", type=str, nargs="+", help="Preset(s)")
    parser.add_argument("-w", "--workers", type=int, help="Workers concurrentes")
    parser.add_argument("--max-results", type=int, dest="max_results", help="Máximo resultados")
    parser.add_argument("-o", "--output", type=str, help="Archivo CSV")
    parser.add_argument("--json-output", type=str, help="Archivo JSON")
    parser.add_argument("--sqlite-output", type=str, help="Archivo SQLite")
    parser.add_argument("--md-output", type=str, help="Archivo Markdown")
    parser.add_argument("--score-min", type=int, help="Score mínimo")
    parser.add_argument("--score-max", type=int, help="Score máximo")
    parser.add_argument("--date-from", type=str, help="Fecha desde")
    parser.add_argument("--date-to", type=str, help="Fecha hasta")
    parser.add_argument("--benchmark-type", type=str, nargs="+", help="Benchmarks")
    parser.add_argument("--delay", type=float, help="Delay entre requests")
    parser.add_argument("--min-delay", type=float, help="Delay mínimo")
    parser.add_argument("--cache-ttl", type=int, dest="cache_ttl", help="TTL caché")
    parser.add_argument("--no-cache", action="store_true", help="Sin caché")
    parser.add_argument("--append", action="store_true", help="Modo append")
    parser.add_argument("--no-color", action="store_true", help="Sin colores")
    parser.add_argument("--no-check-robots-txt", action="store_true", help="Ignorar robots.txt")
    parser.add_argument("--no-adaptive-workers", action="store_true", help="Sin workers adaptativos")
    parser.add_argument("--no-user-agent-rotation", action="store_true", help="Sin rotación UA")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--start-id", type=int, help="ID inicial (más alto)")
    parser.add_argument("--end-id", type=int, help="ID final (más bajo)")
    parser.add_argument("--stride", type=int, help="Saltar N IDs")
    parser.add_argument("--sample-mode", action="store_true", help="Modo muestreo")
    parser.add_argument("--auto-export-every", type=int, help="Exportar parcial cada N resultados")

    return parser


# ============== MAIN ============
CONFIG: Dict[str, Any] = {}


def main():
    global CONFIG

    parser = build_parser()
    cli_args = parser.parse_args()

    if cli_args.edit:
        edit_config_interactive()
        return
    if cli_args.show_config:
        persistent = load_persistent_config()
        cfg = merge_config(cli_args, persistent=persistent)
        show_config(cfg)
        return
    if cli_args.reset_config:
        reset_persistent_config()
        return

    file_config = None
    if cli_args.config:
        file_config = load_config_from_file(cli_args.config)

    persistent = load_persistent_config()
    CONFIG = merge_config(cli_args, file_config=file_config, persistent=persistent)

    logging.basicConfig(
        level=getattr(logging, CONFIG.get("log_level", "INFO")),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    scraper = GpuMagickIdScraper()
    command = cli_args.command
    extra_args = cli_args.args

    if command == "variants":
        print(c("[!] Modo 'variants' no disponible en v14. Usa debug2 para IDs individuales.", Colors.YELLOW))
    elif command == "debug":
        print(c("[!] Modo 'debug' no disponible en v14. Usa debug2 <score_id>.", Colors.YELLOW))
    elif command == "debug2":
        if not extra_args:
            print(c("Uso: python script.py debug2 <score_id>", Colors.RED))
            sys.exit(1)
        temp = GpuMagickIdScraper()
        url = f"{BASE_URL}/scores/{extra_args[0]}"
        html, status = temp._fetch(url)
        if html:
            data = temp.parser.parse_score_page(html, extra_args[0])
            if data:
                for k, v in data.items():
                    print(f"  {k:>15} : {v!r}")
            else:
                print(c("No se pudo parsear", Colors.RED))
        else:
            print(c(f"Error: HTTP {status}", Colors.RED))
    elif command == "clear-cache":
        Cache(CONFIG.get("cache_dir"), CONFIG.get("cache_ttl_hours", 24)).clear()
    else:
        scraper.run_scrape()


if __name__ == "__main__":
    main()
