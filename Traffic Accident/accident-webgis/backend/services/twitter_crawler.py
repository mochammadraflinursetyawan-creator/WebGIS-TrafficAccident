import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Konfigurasi Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TwitterCrawler")


def extract_tweet_media(article) -> List[Dict[str, str]]:
    """Extract attached tweet photos and CCTV/video thumbnails while excluding profile/avatar images."""
    media = []
    seen_urls = set()

    # 1. Foto statis tweet
    try:
        images = article.find_elements(
            "css selector", '[data-testid="tweetPhoto"] img'
        )
        for image in images:
            image_url = image.get_attribute("src") or image.get_attribute("currentSrc")
            if not image_url or image_url in seen_urls:
                continue

            parsed_url = urlparse(image_url)
            if parsed_url.scheme != "https" or parsed_url.hostname != "pbs.twimg.com":
                continue
            if "profile_images" in parsed_url.path:
                continue

            seen_urls.add(image_url)
            media.append({"url": image_url, "alt_text": image.get_attribute("alt") or ""})
    except Exception:
        pass

    # 2. Thumbnail / poster video CCTV (misal rekaman cctv laka)
    try:
        videos = article.find_elements("css selector", "video")
        for video in videos:
            poster_url = video.get_attribute("poster")
            if not poster_url or poster_url in seen_urls:
                continue

            parsed_url = urlparse(poster_url)
            if parsed_url.scheme != "https" or parsed_url.hostname != "pbs.twimg.com":
                continue

            seen_urls.add(poster_url)
            media.append({"url": poster_url, "alt_text": "Rekaman CCTV / Video Laka"})
    except Exception:
        pass

    return media

class TwitterCrawlerWorker:
    """
    Headless Browser Crawler untuk X (Twitter)
    Menggunakan cookie sesi pengguna (auth_token) untuk membaca cuitan terbaru dari akun target.
    """

    def __init__(self):
        self.auth_token = os.getenv("TWITTER_AUTH_TOKEN", "")
        self.target_account = os.getenv("TARGET_TWITTER_ACCOUNT", "Merapi_Uncover")

    def _create_driver(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        options = Options()
        # Headless mode baru Chrome
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)
        return driver

    def fetch_latest_tweets(self, max_tweets: int = 35) -> List[Dict[str, Any]]:
        """
        Buka X.com, injeksikan cookie sesi, buka akun target, dan ambil teks tweet terbaru.
        """
        if not self.auth_token:
            logger.warning("TWITTER_AUTH_TOKEN belum diisi di .env")
            return []

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        driver = None
        collected_tweets = []

        try:
            logger.info("Memulai browser headless...")
            driver = self._create_driver()

            # 1. Buka domain x.com terlebih dahulu agar bisa menyetel cookie
            logger.info("Membuka x.com untuk menyuntikkan cookie sesi...")
            driver.get("https://x.com")
            time.sleep(2)

            # 2. Suntikkan cookie auth_token
            cookie_dict = {
                "name": "auth_token",
                "value": self.auth_token,
                "domain": ".x.com",
                "path": "/",
                "secure": True,
                "httpOnly": True
            }
            driver.add_cookie(cookie_dict)

            # 3. Arahkan ke profil target
            target_url = f"https://x.com/{self.target_account}"
            logger.info(f"Membuka timeline target: {target_url}")
            driver.get(target_url)

            # Tunggu hingga elemen cuitan (tweetText) termuat di halaman (maks 10 detik)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@data-testid="tweetText"]'))
                )
            except Exception:
                logger.warning("Elemen tweetText belum muncul atau akun memerlukan verifikasi lanjutan.")

            # Ambil elemen teks cuitan dengan scrolling bertahap lebih dalam
            collected_texts = set()
            scroll_attempts = 0
            max_scrolls = 15

            while len(collected_tweets) < max_tweets and scroll_attempts <= max_scrolls:
                tweet_elements = driver.find_elements(By.XPATH, '//div[@data-testid="tweetText"]')
                for el in tweet_elements:
                    try:
                        text = el.text.strip()
                        if text and len(text) > 10 and text not in collected_texts:
                            collected_texts.add(text)
                            article = None
                            posted_at = None
                            try:
                                article = el.find_element(By.XPATH, "./ancestor::article[1]")
                            except Exception:
                                pass
                            if article:
                                try:
                                    time_element = article.find_element(By.XPATH, ".//time[@datetime]")
                                    posted_at = time_element.get_attribute("datetime")
                                except Exception:
                                    pass
                            tweet_media = extract_tweet_media(article) if article else []
                            collected_tweets.append({
                                "raw_text": text,
                                "author": f"@{self.target_account}",
                                "posted_at": posted_at,
                                "media": tweet_media,
                                "crawled_at": time.time()
                            })
                            if len(collected_tweets) >= max_tweets:
                                break
                    except Exception:
                        pass
                
                scroll_attempts += 1
                if len(collected_tweets) < max_tweets:
                    driver.execute_script("window.scrollBy(0, 1200);")
                    time.sleep(1.2)

            logger.info(f"Berhasil mengumpulkan {len(collected_tweets)} cuitan unik dari @{self.target_account}.")

        except Exception as e:
            logger.error(f"Terjadi error saat crawling: {e}")
        finally:
            if driver:
                driver.quit()
                logger.info("Browser headless ditutup.")

        return collected_tweets

    def run_ingestion_cycle(self, db_session, pipeline) -> List[Dict[str, Any]]:
        """
        Ambil cuitan live -> filter duplikasi database -> proses lewat NLP & Geocoder -> simpan PostGIS
        """
        from backend.models import Accident, Source
        from backend.services.ingestion import resolve_tweet_datetime
        from backend.services.media import persist_tweet_media

        tweets = self.fetch_latest_tweets(max_tweets=35)
        results = []

        for item in tweets:
            raw_text = item["raw_text"]
            posted_at = item.get("posted_at")
            posted_datetime = None
            if posted_at:
                try:
                    posted_datetime = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning("Timestamp cuitan tidak valid: %s", posted_at)

            # Cek apakah teks ini sudah pernah diproses di tabel sources
            existing = db_session.query(Source).filter(Source.raw_text == raw_text).first()
            if existing:
                accident = (
                    db_session.query(Accident)
                    .filter(Accident.source_id == existing.source_id)
                    .first()
                )
                if accident:
                    if posted_datetime:
                        event_datetime = resolve_tweet_datetime(
                            raw_text,
                            fallback_datetime=posted_datetime,
                        )
                        accident.event_date = event_datetime.date()
                        accident.event_time = event_datetime.time().replace(tzinfo=None)
                        db_session.add(accident)
                        db_session.commit()
                    persist_tweet_media(db_session, accident.accident_id, item.get("media", []))
                results.append({
                    "raw_text": raw_text[:50] + "...",
                    "status": "DUPLICATE_SKIPPED",
                    "detail": "Cuitan ini sudah pernah diproses sebelumnya."
                })
                continue

            # Jalankan pipeline NLP & Geocoding
            proc_result = pipeline.process_tweet(
                raw_tweet=raw_text,
                author=item["author"],
                db=db_session,
                fallback_datetime=posted_datetime,
            )
            if proc_result.get("success") and proc_result.get("accident_id"):
                proc_result["media_count"] = persist_tweet_media(
                    db_session,
                    proc_result["accident_id"],
                    item.get("media", []),
                )
            results.append(proc_result)

        return results
