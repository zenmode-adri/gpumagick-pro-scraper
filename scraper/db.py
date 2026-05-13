import aiosqlite
import logging
from typing import List, Optional, Set
from .models import GpuScore

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
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
            await db.commit()

    async def save_score(self, score: GpuScore):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO scores
                (score_id, benchmark_type, submitted_date, cpu, gpu, gpu_raw,
                 score, fps, resolution, duration_ms, os, driver, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score.score_id, score.benchmark_type, score.submitted_date,
                score.cpu, score.gpu, score.gpu_raw, score.score, score.fps,
                score.resolution, score.duration_ms, score.os, score.driver, score.url
            ))
            await db.commit()

    async def save_scores_batch(self, scores: List[GpuScore]):
        if not scores:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany("""
                INSERT OR REPLACE INTO scores
                (score_id, benchmark_type, submitted_date, cpu, gpu, gpu_raw,
                 score, fps, resolution, duration_ms, os, driver, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (s.score_id, s.benchmark_type, s.submitted_date,
                 s.cpu, s.gpu, s.gpu_raw, s.score, s.fps,
                 s.resolution, s.duration_ms, s.os, s.driver, s.url)
                for s in scores
            ])
            await db.commit()

    async def get_seen_ids(self) -> Set[int]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT score_id FROM scores") as cursor:
                    rows = await cursor.fetchall()
                    return {int(r[0]) for r in rows}
        except Exception as e:
            logging.warning(f"No se pudieron cargar IDs de SQLite: {e}")
            return set()
