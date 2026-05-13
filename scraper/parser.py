import re
import logging
from typing import Optional, Dict, Any
from .models import GpuScore

class GpuMagickParser:
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
    def normalize_gpu_name(cls, name: str) -> str:
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
        
        gpu_raw = cls.extract_field(html, "3D Renderer")
        if not gpu_raw:
            return None

        duration_str = cls.extract_field(html, "Duration")
        duration_ms = None
        if duration_str:
            m = re.search(r"(\d+)", duration_str)
            if m: duration_ms = int(m.group(1))

        # Gruk caza la fecha en el encabezado porque no está en la tabla
        # Ejemplo: Submitted by anonymous on Apr 28, 2026 @ 15:46:19
        submitted_date = ""
        m_date = re.search(r"Submitted by .*? on (.*? @ .*?)</th>", html, re.IGNORECASE | re.DOTALL)
        if m_date:
            submitted_date = m_date.group(1).strip()
        else:
            # Plan B por si acaso
            submitted_date = cls.extract_field(html, "Submitted")

        try:
            score_val = int(cls.extract_field(html, "SCORE") or 0)
            fps_val = float(cls.extract_field(html, "FPS") or 0.0)
        except ValueError:
            score_val = 0
            fps_val = 0.0

        return GpuScore(
            score_id=str(score_id),
            score=score_val,
            fps=fps_val,
            gpu=cls.normalize_gpu_name(gpu_raw),
            gpu_raw=gpu_raw,
            resolution=cls.extract_field(html, "Resolution"),
            duration_ms=duration_ms,
            cpu=cls.extract_field(html, "CPU"),
            os=cls.extract_field(html, "Operating system"),
            driver=cls.extract_field(html, "graphics driver"),
            submitted_date=submitted_date,
            benchmark_type=cls.detect_benchmark_type(html),
            url=f"https://gpumagick.com/scores/{score_id}"
        )
