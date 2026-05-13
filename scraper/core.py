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
        self.buffer = []
        self.buffer_size = 10 # Guardar cada 10 hallazgos
        self._db_lock = asyncio.Lock()

    def _save_status(self):
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
        self.stats["status"] = "probing"
        self._save_status()
        
        async with AsyncHttpClient(max_concurrent=5) as client:
            probe_range = list(range(base_id + window, base_id - 1, -step))
            tasks = [client.fetch(f"https://gpumagick.com/scores/{tid}") for tid in probe_range]
            results = await asyncio.gather(*tasks)
            
            for i, (html, status) in enumerate(results):
                if html and "INVALID SCORE" not in html.upper():
                    logging.info(f"Nuevo ID detectado: {probe_range[i]}")
                    return probe_range[i]
        return base_id

    async def _worker(self, queue: asyncio.Queue, client: AsyncHttpClient, gpu_filter, benchmark_types, max_results):
        while not self.interrupted:
            if self.stats["found"] >= max_results:
                break
                
            try:
                score_id = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if score_id is None:
                queue.task_done()
                break

            try:
                await self._process_id(client, score_id, gpu_filter, benchmark_types)
                if self.stats["checked"] % 5 == 0:
                    self._save_status()
            except Exception as e:
                logging.error(f"Error en worker para ID {score_id}: {e}")
            finally:
                queue.task_done()

    async def run(self, gpu_filter: Optional[List[str]] = None, max_results: int = 2000, benchmark_types: Optional[List[str]] = None):
        try:
            self.stats["status"] = "probing"
            self._save_status()
            self.start_id = await self.auto_detect_start_id(self.start_id)
                
            self.stats["status"] = "running"
            self.stats["start_time"] = time.time()
            self._save_status()
            
            await self.db.initialize()
            seen_ids = await self.db.get_seen_ids()

            # 2. Doble Marca de Rango: ¿Qué zona de la cueva ya exploramos?
            filter_key = ",".join(sorted(gpu_filter)) if gpu_filter else "ALL"
            explored_range = await self.db.get_checkpoint_range(filter_key)
            min_expl, max_expl = explored_range if explored_range else (None, None)
            
            ids_to_check = range(self.start_id, self.end_id - 1, -self.stride)
            self.stats["total_ids"] = len(ids_to_check)
            self._save_status()

            queue = asyncio.Queue()
            async with AsyncHttpClient(self.max_concurrent, self.base_delay) as client:
                workers = []
                stagger_delay = self.base_delay / self.max_concurrent if self.max_concurrent > 0 else 0
                
                for i in range(self.max_concurrent):
                    workers.append(asyncio.create_task(
                        self._worker(queue, client, gpu_filter, benchmark_types, max_results)
                    ))
                    if stagger_delay > 0:
                        await asyncio.sleep(min(stagger_delay, 2.0))

                # Llenar la cola con la sabiduría de la Doble Marca
                current_session_min = self.start_id
                current_session_max = self.start_id

                for score_id in ids_to_check:
                    if self.interrupted or self.stats["found"] >= max_results:
                        break
                    
                    # REGLA DE ORO: Si el ID está entre MIN y MAX explorados, y NO está en seen_ids,
                    # significa que ya lo procesamos antes y no contenía nuestra GPU. ¡SALTAR!
                    if min_expl is not None and max_expl is not None:
                        if min_expl <= score_id <= max_expl:
                            if score_id not in seen_ids:
                                self.stats["skipped"] += 1
                                self.stats["checked"] += 1
                                continue

                    if score_id in seen_ids:
                        self.stats["skipped"] += 1
                        self.stats["checked"] += 1
                        continue

                    await queue.put(score_id)
                    current_session_min = min(current_session_min, score_id)
                    current_session_max = max(current_session_max, score_id)

                while not queue.empty() and not self.interrupted and self.stats["found"] < max_results:
                    await asyncio.sleep(1)
                
                for _ in range(self.max_concurrent):
                    await queue.put(None)
                await asyncio.gather(*workers, return_exceptions=True)
                
                # Actualizar el mapa de la cueva al terminar
                if not self.interrupted and self.stats["checked"] > self.stats["skipped"]:
                    await self.db.save_checkpoint(filter_key, current_session_min, current_session_max)

            self.stats["status"] = "finished"
        except Exception as e:
            logging.error(f"FATAL_ERROR: {e}")
            self.stats["status"] = f"crashed: {str(e)}"
        finally:
            async with self._db_lock:
                if self.buffer:
                    await self.db.save_scores_batch(self.buffer)
                    self.buffer = []
            self.stats["end_time"] = time.time()
            self._save_status()

    async def _process_id(self, client: AsyncHttpClient, score_id: int, gpu_filter: Optional[List[str]], benchmark_types: Optional[List[str]]):
        url = f"https://gpumagick.com/scores/{score_id}"
        html, status = await client.fetch(url)
        self.stats["checked"] += 1

        if html:
            score_data = GpuMagickParser.parse_score_page(html, str(score_id))
            if score_data:
                if benchmark_types and score_data.benchmark_type not in benchmark_types:
                    return
                if gpu_filter:
                    match = False
                    for f in gpu_filter:
                        if f.lower() in score_data.gpu.lower():
                            match = True
                            break
                    if not match: return

                async with self._db_lock:
                    self.buffer.append(score_data)
                    if len(self.buffer) >= self.buffer_size:
                        await self.db.save_scores_batch(self.buffer)
                        self.buffer = []
                self.stats["found"] += 1
        elif status != 404:
            self.stats["failed"] += 1
