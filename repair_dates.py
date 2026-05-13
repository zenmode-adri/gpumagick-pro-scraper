import asyncio
import os
import duckdb
import logging
from scraper.core import AsyncHttpClient
from scraper.parser import GpuMagickParser
from scraper.db import DatabaseManager

DB_PATH = "gpumagick.db"

async def repair_dates():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("--- INICIANDO REPARACIÓN DE FECHAS ---")
    db = DatabaseManager(DB_PATH)
    await db.initialize()
    
    # Gruk usa DuckDB para ver cuántos registros no tienen fecha
    con = duckdb.connect(':memory:')
    con.execute("INSTALL sqlite; LOAD sqlite;")
    con.execute(f"CALL sqlite_attach('{DB_PATH}');")
    
    missing_ids = con.execute("SELECT score_id FROM scores WHERE submitted_date = ''").df()['score_id'].tolist()
    con.close()
    
    logging.info(f"Gruk encontró {len(missing_ids)} IDs sin fecha.")
    
    if not missing_ids:
        logging.info("¡No hay nada que reparar! Gruk vuelve a la hoguera.")
        return

    # Limitar a 500 para no cansar al jefe, jefe puede correrlo más veces
    to_repair = missing_ids[:500]
    logging.info(f"Reparando los primeros {len(to_repair)}...")

    async with AsyncHttpClient(max_concurrent=5, base_delay=1.0) as client:
        for score_id in to_repair:
            url = f"https://gpumagick.com/scores/{score_id}"
            html, status = await client.fetch(url)
            if html:
                score_data = GpuMagickParser.parse_score_page(html, str(score_id))
                if score_data and score_data.submitted_date:
                    logging.info(f"ID {score_id} -> {score_data.submitted_date}")
                    await db.save_score(score_data)
                else:
                    logging.warning(f"ID {score_id} -> No se pudo obtener fecha.")
            else:
                logging.error(f"ID {score_id} -> Error HTTP {status}")
            
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(repair_dates())
