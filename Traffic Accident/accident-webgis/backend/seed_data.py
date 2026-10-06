from datetime import date, time
from backend.database import engine, Base, SessionLocal
from backend.models import Accident, Source


def seed_database():
    """
    Pastikan database punya data awal agar peta tidak kosong saat live crawler belum berhasil.
    Data default ini berfungsi sebagai fallback demo/seed agar frontend tetap bisa terisi.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Accident).count() > 0:
            return

        source = db.query(Source).filter(Source.source_type == "twitter").first()
        if not source:
            source = Source(
                source_type="twitter",
                external_id="Merapi_Uncover",
                source_url="https://x.com/Merapi_Uncover",
                raw_text="Fallback seed data untuk demo WebGIS.",
            )
            db.add(source)
            db.commit()
            db.refresh(source)

        fallback_accidents = [
            {
                "event_date": date(2026, 10, 3),
                "event_time": time(18, 49, 39),
                "accident_type": "Truck",
                "description": "Truk muatan terguling dan memblokir jalur utama di sekitar Nologaten.",
                "location_text": "Nologaten (Dekat Selokan Mataram), Depok, Sleman",
                "latitude": -7.776,
                "longitude": 110.398,
                "source_type": "twitter",
                "source_id": source.source_id,
                "confidence": 0.88,
                "status": "VERIFIED",
                "precision": "HIGH",
                "uncertainty_radius": 150,
            },
            {
                "event_date": date(2026, 10, 3),
                "event_time": time(19, 2, 23),
                "accident_type": "Motorcycle",
                "description": "Kecelakaan motor di sekitar TPB Jalan Pramuka, arus lalu lintas terganggu.",
                "location_text": "TPB Jl. Pramuka, Jalan Pramuka, Gambiran, Pandeyan, Umbulharjo, Kota Yogyakarta, Berbah, Daerah Istimewa Yogyakarta, 55161, Indonesia",
                "latitude": -7.818463,
                "longitude": 110.3873192,
                "source_type": "twitter",
                "source_id": source.source_id,
                "confidence": 0.89,
                "status": "VERIFIED",
                "precision": "HIGH",
                "uncertainty_radius": 150,
            },
            {
                "event_date": date(2026, 10, 3),
                "event_time": time(19, 8, 28),
                "accident_type": "Motorcycle",
                "description": "Motor menabrak trotoar di area Langensari, korban luka ringan dan lalu lintas macet sebentar.",
                "location_text": "Jl. Langensari (Utara Balai Yasa), Klitren, Gondokusuman, Kota Yogyakarta",
                "latitude": -7.7862,
                "longitude": 110.384,
                "source_type": "twitter",
                "source_id": source.source_id,
                "confidence": 0.86,
                "status": "VERIFIED",
                "precision": "MEDIUM",
                "uncertainty_radius": 200,
            },
        ]

        for item in fallback_accidents:
            db.add(Accident(**item))

        db.commit()
    finally:
        db.close()
