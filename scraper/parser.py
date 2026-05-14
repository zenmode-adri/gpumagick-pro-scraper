import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from selectolax.lexbor import LexborHTMLParser
from .models import GpuScore

class GpuMagickParser:
    @classmethod
    def parse_date(cls, date_str: str) -> datetime:
        """Convierte 'Apr 28, 2026 @ 15:46:19' en objeto datetime."""
        if not date_str:
            return datetime.utcnow()
        try:
            clean_date = date_str.strip()
            return datetime.strptime(clean_date, "%b %d, %Y @ %H:%M:%S")
        except Exception as e:
            logging.warning(f"No se pudo parsear fecha '{date_str}': {e}")
            return datetime.utcnow()

    @classmethod
    def normalize_gpu_name(cls, name: str) -> str:
        if not name: return ""
        name = re.sub(r'/PCIe/SSE2$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'/OpenCL$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^AMD\s+Radeon\s+\(TM\)\s+', 'Radeon ', name, flags=re.IGNORECASE)
        name = re.sub(r'^AMD\s+Radeon\s+\(TM\)', 'Radeon', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+\(RADV\s+[^)]+\)', '', name, flags=re.IGNORECASE)
        return name.strip()

    @classmethod
    def parse_score_page(cls, html: str, score_id: str) -> Optional[GpuScore]:
        if not html or len(html) < 500 or "INVALID SCORE" in html.upper():
            return None
        
        parser = LexborHTMLParser(html)
        
        # Mapear la tabla principal a un diccionario
        data = {}
        # El encabezado está en un <th> que ocupa 2 columnas
        header_node = parser.css_first("table.scores_table th[colspan='2']")
        
        # El tipo de benchmark suele estar dentro de una etiqueta <font size="6"> o similar
        benchmark_type = ""
        if header_node:
            font_node = header_node.css_first("font")
            if font_node:
                benchmark_type = font_node.text().strip()
            
            # Fecha de envío: Submitted by anonymous on Apr 28, 2026 @ 15:46:19
            header_text = header_node.text()
            m_date = re.search(r"on\s+(.*? @ .*?)$", header_text, re.IGNORECASE | re.MULTILINE)
            if m_date:
                data["submitted_date"] = m_date.group(1).strip()

        # Extraer filas de la tabla
        for row in parser.css("table.scores_table tr"):
            th = row.css_first("th")
            td = row.css_first("td")
            if th and td:
                key = th.text().strip().upper()
                val = td.text().strip()
                data[key] = val

        gpu_raw = data.get("3D RENDERER") or data.get("GPU0")
        if not gpu_raw:
            return None

        # Duración
        duration_ms = None
        duration_str = data.get("DURATION")
        if duration_str:
            m = re.search(r"(\d+)", duration_str)
            if m: duration_ms = int(m.group(1))

        cpu_val = data.get("CPU", "").strip()
        if not cpu_val:
            logging.warning(f"Missing CPU field for score_id {score_id}, skipping")
            return None

        try:
            score_val = int(data.get("SCORE") or 0)
            fps_val = float(data.get("FPS") or 0.0)
        except ValueError:
            score_val = 0
            fps_val = 0.0

        if score_val < 0:
            score_val = 0
        if fps_val < 0 or fps_val > 50000:
            fps_val = 0.0

        return GpuScore(
            score_id=str(score_id),
            score=score_val,
            fps=fps_val,
            gpu=cls.normalize_gpu_name(gpu_raw),
            gpu_raw=gpu_raw,
            resolution=data.get("RESOLUTION", ""),
            duration_ms=duration_ms,
            cpu=cpu_val,
            os=data.get("OPERATING SYSTEM", ""),
            driver=data.get("GRAPHICS DRIVER", ""),
            submitted_date=cls.parse_date(data.get("submitted_date", "")),
            benchmark_type=benchmark_type,
            url=f"https://gpumagick.com/scores/{score_id}"
        )

