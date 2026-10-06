import os
import sys
import logging

# Pastikan path root terdaftar
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.database import SessionLocal, Base, engine
from backend.services.twitter_crawler import TwitterCrawlerWorker
from backend.services.ingestion import SocialMediaIngestionPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("StandaloneCrawler")

def run():
    logger.info("Memulai proses crawling standalone X (@Merapi_Uncover)...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    pipeline = SocialMediaIngestionPipeline()
    worker = TwitterCrawlerWorker()

    try:
        results = worker.run_ingestion_cycle(db_session=db, pipeline=pipeline)
        new_accidents = [r for r in results if r.get("success") and r.get("accident_id")]
        logger.info(f"Selesai! Ditemukan {len(results)} cuitan, {len(new_accidents)} laka baru berhasil disimpan.")
        for item in new_accidents:
            logger.info(f"-> Laka #{item.get('accident_id')}: {item.get('location_text')} (Media: {item.get('media_count', 0)})")
        return len(new_accidents)
    finally:
        db.close()

if __name__ == "__main__":
    run()
