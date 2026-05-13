from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class GpuScore:
    score_id: str
    benchmark_type: str
    submitted_date: str
    cpu: str
    gpu: str
    gpu_raw: str
    score: int
    fps: float
    resolution: str
    duration_ms: Optional[int]
    os: str
    driver: str
    url: str
    scraped_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)
