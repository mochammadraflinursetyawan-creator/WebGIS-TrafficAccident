from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Accident, Source
from backend.schemas import AccidentDetail
from backend.services import media as media_service
from backend.services.twitter_crawler import TwitterCrawlerWorker, extract_tweet_media


class FakeImage:
    def __init__(self, src, alt=""):
        self.src = src
        self.alt = alt

    def get_attribute(self, name):
        if name in {"src", "currentSrc"}:
            return self.src
        if name == "alt":
            return self.alt
        return None


class FakeArticle:
    def __init__(self, images):
        self.images = images

    def find_elements(self, by, selector):
        assert by == "css selector"
        assert selector == '[data-testid="tweetPhoto"] img'
        return self.images


def test_extract_tweet_media_keeps_attached_photos_only():
    article = FakeArticle([
        FakeImage("https://pbs.twimg.com/media/accident.jpg", "Road damage"),
        FakeImage("https://pbs.twimg.com/profile_images/avatar.jpg"),
        FakeImage("https://example.com/external.jpg"),
    ])

    assert extract_tweet_media(article) == [{
        "url": "https://pbs.twimg.com/media/accident.jpg",
        "alt_text": "Road damage",
    }]


def test_extract_tweet_media_deduplicates_photo_urls():
    url = "https://pbs.twimg.com/media/accident.jpg"

    assert extract_tweet_media(FakeArticle([FakeImage(url), FakeImage(url)])) == [{
        "url": url,
        "alt_text": "",
    }]


class FakeHeaders:
    def get_content_type(self):
        return "image/jpeg"


class FakeResponse:
    headers = FakeHeaders()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, limit):
        return b"\xff\xd8\xfftest-image"


def test_store_tweet_image_saves_supported_x_photo(monkeypatch, tmp_path):
    monkeypatch.setattr(media_service, "urlopen", lambda request, timeout: FakeResponse())

    media_url = media_service.store_tweet_image(
        "https://pbs.twimg.com/media/report.jpg?format=jpg&name=small",
        tmp_path,
    )

    saved_file = tmp_path / media_url.rsplit("/", 1)[-1]
    assert media_url.startswith("/media/")
    assert saved_file.suffix == ".jpg"
    assert saved_file.read_bytes() == b"\xff\xd8\xfftest-image"


def test_store_tweet_image_rejects_untrusted_hosts(tmp_path):
    with pytest.raises(ValueError, match="pbs.twimg.com"):
        media_service.store_tweet_image("https://example.com/photo.jpg", tmp_path)


def test_persist_tweet_media_links_files_to_accident_and_deduplicates(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    accident = Accident(
        event_date=date(2026, 10, 5),
        event_time=time(22, 55),
        accident_type="Motorcycle",
        description="Accident with photo",
        location_text="Ring Road Barat",
        latitude=-7.7923,
        longitude=110.3304,
        source_type="twitter",
        confidence=0.8,
        status="DETECTED",
    )
    session.add(accident)
    session.commit()
    monkeypatch.setattr(media_service, "store_tweet_image", lambda url: "/media/test.jpg")
    image = {"url": "https://pbs.twimg.com/media/report.jpg", "alt_text": "Damage"}

    assert media_service.persist_tweet_media(session, accident.accident_id, [image]) == 1
    assert media_service.persist_tweet_media(session, accident.accident_id, [image]) == 0
    session.refresh(accident)
    assert len(accident.media) == 1
    assert accident.media[0].media_url == "/media/test.jpg"
    assert accident.media[0].alt_text == "Damage"
    detail = AccidentDetail.model_validate(accident)
    assert detail.media[0].media_url == "/media/test.jpg"
    assert detail.media[0].alt_text == "Damage"

    session.close()
    engine.dispose()


def test_crawler_attaches_tweet_photo_to_new_accident(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    worker = TwitterCrawlerWorker()
    image = {
        "url": "https://pbs.twimg.com/media/new-report.jpg",
        "alt_text": "Broken glass",
    }
    worker.fetch_latest_tweets = lambda max_tweets=35: [{
        "raw_text": "Kecelakaan di Ring Road Barat pukul 22:55",
        "author": "@Merapi_Uncover",
        "posted_at": None,
        "media": [image],
    }]
    monkeypatch.setattr(media_service, "store_tweet_image", lambda url: "/media/new-report.jpg")

    class FakePipeline:
        def process_tweet(self, raw_tweet, author, db, fallback_datetime):
            source = Source(source_type="twitter", raw_text=raw_tweet)
            db.add(source)
            db.commit()
            db.refresh(source)
            accident = Accident(
                event_date=date(2026, 10, 5),
                event_time=time(22, 55),
                accident_type="Motorcycle",
                description=raw_tweet,
                location_text="Ring Road Barat",
                latitude=-7.7923,
                longitude=110.3304,
                source_type="twitter",
                source_id=source.source_id,
                confidence=0.8,
                status="DETECTED",
            )
            db.add(accident)
            db.commit()
            db.refresh(accident)
            return {"success": True, "accident_id": accident.accident_id}

    results = worker.run_ingestion_cycle(session, FakePipeline())
    accident = session.query(Accident).first()

    assert results[0]["media_count"] == 1
    assert len(accident.media) == 1
    assert accident.media[0].alt_text == "Broken glass"

    session.close()
    engine.dispose()