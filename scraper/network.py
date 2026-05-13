import asyncio
import random
import time
import logging
import aiohttp
from typing import Optional, Tuple, Dict

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
    "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
]

class AsyncHttpClient:
    def __init__(self, max_concurrent: int = 1, base_delay: float = 10.0):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.base_delay = base_delay
        self.current_delay = base_delay
        self.consecutive_errors = 0
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Referer": "https://gpumagick.com/scores/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        return {"User-Agent": random.choice(USER_AGENTS)}

    async def fetch(self, url: str) -> Tuple[Optional[str], int]:
        async with self.semaphore:
            # Jitter: Variación aleatoria del 20% para parecer humano
            jitter = self.current_delay * random.uniform(-0.2, 0.2)
            wait_time = max(0.5, self.current_delay + jitter)
            await asyncio.sleep(wait_time)
            
            try:
                async with self.session.get(url, headers=self._get_headers(), timeout=15) as response:
                    status = response.status
                    if status == 200:
                        self.consecutive_errors = 0
                        # Recuperación gradual del delay
                        self.current_delay = max(self.base_delay, self.current_delay * 0.95)
                        return await response.text(), status
                    elif status == 429:
                        self.current_delay = min(self.current_delay * 1.5, 30.0)
                        logging.warning(f"Rate limit (429) en {url}. Delay aumentado a {self.current_delay:.1f}s")
                    else:
                        self.consecutive_errors += 1
                        logging.warning(f"HTTP {status} en {url}")
                    
                    return None, status
            except Exception as e:
                self.consecutive_errors += 1
                logging.error(f"Error en {url}: {e}")
                return None, 0
