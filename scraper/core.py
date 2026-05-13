import asyncio
import json
import logging
import time
import os
from typing import List, Optional
from .network import AsyncHttpClient
from .parser import GpuMagickParser
from .db import DatabaseManager
from .models import GpuScore

class ScraperOrchestrator:
    def __init__(self, 
                 start_id: int, 
                 end_id: int, 
                 stride: int = 1, 
                 max_concurrent: int = 1,
                 base_delay: float = 10.0,
                 db_path: str = "gpumagick.db",
                 status_file: str = "status.json"):
        self.start_id = start_id
        self.end_id = end_id
        self.stride = stride
        self.max_concurrent = max_concurrent
        self.base_delay = base_delay
        self.db = DatabaseManager(db_path)
        self.status_file = status_file
        
        self.stats = {
            "total_ids": 0,
            "checked": 0,
            "found": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": time.time(),
            "status": "idle"
        }
        self.interrupted = False

    def _save_status(self):
        # Escritura atómica para evitar colisiones con Streamlit
        temp_file = self.status_file + ".tmp"
        try:
            with open(temp_file, "w") as f:
                elapsed = time.time() - self.stats["start_time"]
                self.stats["elapsed"] = elapsed
                self.stats["speed"] = self.stats["checked"] / elapsed if elapsed > 0 else 0
                self.stats["pid"] = os.getpid()
                json.dump(self.stats, f)
            if os.path.exists(self.status_file): os.remove(self.status_file)
            os.rename(temp_file, self.status_file)
        except Exception as e:
            logging.error(f"Error guardando status: {e}")

    async def auto_detect_start_id(self, base_id: int, window: int = 30000, step: int = 5000) -> int:
        """Sondea IDs superiores al base para ver si hay nuevas subidas."""
        self.stats["status"] = "probing"
        self._save_status()
        
        async with AsyncHttpClient(max_concurrent=5) as client:
            # Probar de más alto a más bajo
            probe_range = range(base_id + window, base_id - 1, -step)
            for test_id in probe_range:
                url = f"https://gpumagick.com/scores/{test_id}"
                html, status = await client.fetch(url)
                if html and "INVALID SCORE" not in html.upper():
                    return test_id
        return base_id

    async def run(self, gpu_filter: Optional[List[str]] = None, max_results: int = 2000, benchmark_types: Optional[List[str]] = None):
        try:
            self.stats["status"] = "probing"
            self._save_status()
            
            # Auto-detección obligatoria antes de empezar
            self.start_id = await self.auto_detect_start_id(self.start_id)
                
            self.stats["status"] = "running"
            self.stats["start_time"] = time.time()
            self._save_status()
            await self.db.initialize()
            seen_ids = await self.db.get_seen_ids()

            ids_to_check = range(self.start_id, self.end_id - 1, -self.stride)
            self.stats["total_ids"] = len(ids_to_check)
            self._save_status()

            async with AsyncHttpClient(self.max_concurrent, self.base_delay) as client:
                tasks = []
                for score_id in ids_to_check:
                    if self.interrupted or self.stats["found"] >= max_results:
                        break
                    
                    if score_id in seen_ids:
                        self.stats["skipped"] += 1
                        self.stats["checked"] += 1
                        if self.stats["checked"] % 20 == 0:
                            self._save_status()
                        continue

                    tasks.append(self._process_id(client, score_id, gpu_filter, benchmark_types))
                    
                    if len(tasks) >= self.max_concurrent:
                        await asyncio.gather(*tasks)
                        tasks = []
                        self._save_status()
                        if self.stats["found"] >= max_results:
                            break

                if tasks and self.stats["found"] < max_results:
                    await asyncio.gather(*tasks)
                    self._save_status()

            self.stats["status"] = "finished"
        except Exception as e:
            logging.error(f"FATAL_ERROR: {e}")
            self.stats["status"] = f"crashed: {str(e)}"
        finally:
            self._save_status()

    async def _process_id(self, client: AsyncHttpClient, score_id: int, gpu_filter: Optional[List[str]], benchmark_types: Optional[List[str]]):
        url = f"https://gpumagick.com/scores/{score_id}"
        html, status = await client.fetch(url)
        self.stats["checked"] += 1

        if html:
            score_data = GpuMagickParser.parse_score_page(html, str(score_id))
            if score_data:
                # Filtro por Benchmark Type
                if benchmark_types and score_data.benchmark_type not in benchmark_types:
                    return

                # Aplicar filtro de GPU si existe
                if gpu_filter:
                    match = False
                    for f in gpu_filter:
                        if f.lower() in score_data.gpu.lower():
                            match = True
                            break
                    if not match:
                        return

                await self.db.save_score(score_data)
                self.stats["found"] += 1
        elif status != 404:
            self.stats["failed"] += 1
