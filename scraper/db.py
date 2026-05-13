from typing import List, Set
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from .models import GpuScore

class DatabaseManager:
    def __init__(self, db_path: str):
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initialize(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(GpuScore.metadata.create_all)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints_v2 (
                    filter_key TEXT PRIMARY KEY,
                    min_id INTEGER,
                    max_id INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def save_checkpoint(self, filter_key: str, min_id: int, max_id: int):
        async with self.async_session() as session:
            # Actualizar el rango existente: expandir si los nuevos límites son más amplios
            await session.execute("""
                INSERT INTO checkpoints_v2 (filter_key, min_id, max_id, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(filter_key) DO UPDATE SET
                    min_id = MIN(checkpoints_v2.min_id, excluded.min_id),
                    max_id = MAX(checkpoints_v2.max_id, excluded.max_id),
                    updated_at = CURRENT_TIMESTAMP
            """, (filter_key, min_id, max_id))
            await session.commit()

    async def get_checkpoint_range(self, filter_key: str) -> Optional[tuple]:
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    "SELECT min_id, max_id FROM checkpoints_v2 WHERE filter_key = ?", (filter_key,)
                )
                return result.fetchone()
        except Exception:
            return None

    async def save_score(self, score: GpuScore):
        async with self.async_session() as session:
            await session.merge(score)
            await session.commit()

    async def save_scores_batch(self, scores: List[GpuScore]):
        if not scores: return
        async with self.async_session() as session:
            for s in scores:
                await session.merge(s)
            await session.commit()

    async def get_seen_ids(self) -> Set[int]:
        try:
            async with self.async_session() as session:
                statement = select(GpuScore.score_id)
                results = await session.execute(statement)
                # results.all() returns list of rows (tuples)
                return {int(r[0]) for r in results.all()}
        except Exception:
            return set()
