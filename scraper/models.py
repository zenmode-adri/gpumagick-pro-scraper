from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Index

class GpuScore(SQLModel, table=True):
    __tablename__ = "scores"
    __table_args__ = (
        Index("idx_gpu_bench", "gpu", "benchmark_type"),
        Index("idx_cpu", "cpu"),
        Index("idx_resolution", "resolution"),
    )

    score_id: str = Field(primary_key=True)
    benchmark_type: str
    submitted_date: datetime
    cpu: str
    gpu: str
    gpu_raw: str
    score: int
    fps: float
    resolution: str
    duration_ms: Optional[int] = None
    os: str
    driver: str
    url: str
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
