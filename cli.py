import asyncio
import argparse
import logging
from scraper.core import ScraperOrchestrator

def main():
    parser = argparse.ArgumentParser(description="GPU Magick Async Scraper CLI")
    parser.add_argument("--start-id", type=int, required=True)
    parser.add_argument("--end-id", type=int, required=True)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--delay", type=float, default=10.0)

    parser.add_argument("--gpu-filter", type=str, nargs="+")
    parser.add_argument("--db", type=str, default="gpumagick.db")
    parser.add_argument("--max-results", type=int, default=2000)
    parser.add_argument("--benchmark-types", type=str, nargs="+")
    
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    orchestrator = ScraperOrchestrator(
        start_id=args.start_id,
        end_id=args.end_id,
        stride=args.stride,
        max_concurrent=args.workers,
        base_delay=args.delay,
        db_path=args.db
    )

    try:
        asyncio.run(orchestrator.run(
            gpu_filter=args.gpu_filter, 
            max_results=args.max_results,
            benchmark_types=args.benchmark_types
        ))
    except KeyboardInterrupt:
        print("\nInterrupción detectada. Saliendo...")
        orchestrator.interrupted = True

if __name__ == "__main__":
    main()
