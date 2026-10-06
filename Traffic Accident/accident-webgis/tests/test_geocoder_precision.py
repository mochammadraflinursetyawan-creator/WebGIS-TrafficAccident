from datetime import date, time

from backend.services.geocoder import GeocodingService
from backend.database import Base
from backend.models import Accident
from backend.services.ingestion import repair_existing_accidents
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_geocode_keeps_cebongan_in_sleman_area():
    service = GeocodingService()

    loc = service.extract_location_text("depan Rahayu Cebongan, dekat Sleman")
    assert loc == "rahayu cebongan"

    lat, lon, display_name, precision, radius = service.geocode(loc)

    assert abs(lat - (-7.7305592)) < 0.05
    assert abs(lon - 110.3316290) < 0.05
    assert precision == "HIGH"
    assert "Cebongan" in display_name or "Sleman" in display_name


def test_geocode_accepts_store_alias_near_cebongan():
    service = GeocodingService()

    loc = service.extract_location_text("Rahayu Elektronik & Furniture, Cebongan, Mlati")
    assert loc == "rahayu elektronik and furniture" or loc == "rahayu elektronik & furniture"

    lat, lon, display_name, precision, radius = service.geocode(loc)

    assert abs(lat - (-7.7305592)) < 0.05
    assert abs(lon - 110.3316290) < 0.05
    assert precision == "HIGH"
    assert "Sleman" in display_name or "Cebongan" in display_name


def test_ukdw_report_resolves_to_the_campus_instead_of_yogyakarta_center():
    service = GeocodingService()

    loc = service.extract_location_text(
        "kecelakaan di daerah lampu merah UKDW arah utara Kota Yogyakarta"
    )
    lat, lon, display_name, precision, radius = service.geocode(loc)

    assert loc == "ukdw"
    assert abs(lat - (-7.7860984)) < 0.001
    assert abs(lon - 110.3784035) < 0.001
    assert precision == "HIGH"
    assert "Universitas Kristen Duta Wacana" in display_name


def test_kanisius_gayam_report_resolves_to_the_school_area():
    service = GeocodingService()

    loc = service.extract_location_text(
        "kecelakaan di samping SMP Kanisius Gayam Yogyakarta"
    )
    lat, lon, display_name, precision, radius = service.geocode(loc)

    assert loc == "smp kanisius gayam"
    assert abs(lat - (-7.7975696)) < 0.001
    assert abs(lon - 110.3780723) < 0.001
    assert precision == "HIGH"


def test_sorosutan_area_is_marked_as_estimated():
    service = GeocodingService()

    loc = service.extract_location_text("kecelakaan di Gapura Sorosutan, Umbulharjo")
    lat, lon, display_name, precision, radius = service.geocode(loc)

    assert loc == "gapura sorosutan"
    assert precision == "ESTIMATED"
    assert radius == 1200
    assert "Sorosutan" in display_name


def test_missing_location_fallback_is_not_reported_as_high_precision():
    service = GeocodingService()

    lat, lon, display_name, precision, radius = service.geocode("Wilayah Yogyakarta")

    assert abs(lat - (-7.7956)) < 0.001
    assert abs(lon - 110.3695) < 0.001
    assert precision == "ESTIMATED"
    assert radius == 3000
    assert "Perkiraan" in display_name


def test_ringroad_barat_alias_resolves_to_west_yogyakarta_with_uncertainty():
    service = GeocodingService()

    loc = service.extract_location_text(
        "[Breaking News] kecelakaan di ringroad barat yogyakarta mobil masuk ke kiri"
    )
    lat, lon, display_name, precision, radius = service.geocode(loc)

    assert loc == "ringroad barat"
    assert abs(lat - (-7.7923181)) < 0.001
    assert abs(lon - 110.3304780) < 0.001
    assert precision == "ESTIMATED"
    assert radius == 3000
    assert "Gamping" in display_name


def test_startup_repair_moves_ringroad_barat_report_from_city_center():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    accident = Accident(
        accident_id=41,
        event_date=date(2026, 10, 5),
        event_time=time(22, 55),
        accident_type="Motorcycle",
        description="[Breaking News] 22:55 kak ada kecelakaan di ringroad barat yogyakarta mobilnya masuk ke sebelah kiri",
        location_text="Kota Yogyakarta, Daerah Istimewa Yogyakarta",
        latitude=-7.7956,
        longitude=110.3695,
        source_type="twitter",
        confidence=0.7,
        precision="ESTIMATED",
        uncertainty_radius=3000,
        status="DETECTED",
    )
    session.add(accident)
    session.commit()

    repair_existing_accidents(session)
    session.refresh(accident)

    assert abs(accident.latitude - (-7.7923181)) < 0.001
    assert abs(accident.longitude - 110.3304780) < 0.001
    assert "Gamping" in accident.location_text
    assert accident.precision == "ESTIMATED"
    assert accident.uncertainty_radius == 3000

    session.close()
    engine.dispose()


def test_parangtritis_km10_resolves_to_sewon_not_coastal_town():
    service = GeocodingService()
    raw_text = (
        "[Video] Sekitar pukul 05:40an terjadi kecelakaan di jalan "
        "Parangtritis km 10, tetap hati hati saat berkendara"
    )

    location = service.extract_location_text(raw_text)
    lat, lon, display_name, precision, radius = service.geocode(location)

    assert location == "jalan parangtritis km 10"
    assert abs(lat - (-7.8664525)) < 0.001
    assert abs(lon - 110.3520141) < 0.001
    assert precision == "ESTIMATED"
    assert radius == 500
    assert "Sewon" in display_name


def test_startup_repair_moves_parangtritis_km10_from_coastal_town():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    accident = Accident(
        accident_id=44,
        event_date=date(2026, 10, 6),
        event_time=time(5, 40),
        accident_type="Car",
        description="[Video] Sekitar pukul 05:40an terjadi kecelakaan di jalan Parangtritis km 10.",
        location_text="Parangtritis, Kretek, Bantul",
        latitude=-8.0208,
        longitude=110.3287,
        source_type="twitter",
        confidence=0.7,
        precision="HIGH",
        uncertainty_radius=150,
        status="DETECTED",
    )
    session.add(accident)
    session.commit()

    repair_existing_accidents(session)
    session.refresh(accident)

    assert abs(accident.latitude - (-7.8664525)) < 0.001
    assert abs(accident.longitude - 110.3520141) < 0.001
    assert "Sewon" in accident.location_text
    assert accident.precision == "ESTIMATED"
    assert accident.uncertainty_radius == 500

    session.close()
    engine.dispose()


def test_startup_repair_corrects_stale_rahayu_cebongan_coordinates():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    accident = Accident(
        accident_id=39,
        event_date=date(2026, 10, 4),
        event_time=time(17, 9),
        accident_type="Motorcycle",
        description="17:09 Info awal terjadi kecelakaan di depan Rahayu Cebongan.",
        location_text="Bank Rakyat Indonesia, Jalan Parangtritis, Kretek, Bantul",
        latitude=-7.979772,
        longitude=110.3167584,
        source_type="twitter",
        confidence=0.7,
        precision="MEDIUM",
        uncertainty_radius=400,
        status="DETECTED",
    )
    session.add(accident)
    session.commit()

    repair_existing_accidents(session)
    session.refresh(accident)

    assert abs(accident.latitude - (-7.7305592)) < 0.001
    assert abs(accident.longitude - 110.3316290) < 0.001
    assert accident.precision == "HIGH"
    assert "Sleman" in accident.location_text

    session.close()
    engine.dispose()


def test_startup_repair_updates_estimated_sorosutan_area():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    accident = Accident(
        accident_id=40,
        event_date=date(2026, 10, 4),
        event_time=time(15, 25),
        accident_type="Motorcycle",
        description="Kecelakaan di Gapura Sorosutan, Umbulharjo.",
        location_text="Kota Yogyakarta, Daerah Istimewa Yogyakarta",
        latitude=-7.7956,
        longitude=110.3695,
        source_type="twitter",
        confidence=0.7,
        precision="ESTIMATED",
        uncertainty_radius=3000,
        status="DETECTED",
    )
    session.add(accident)
    session.commit()

    repair_existing_accidents(session)
    session.refresh(accident)

    assert abs(accident.latitude - (-7.8261615)) < 0.001
    assert abs(accident.longitude - 110.3823526) < 0.001
    assert accident.precision == "ESTIMATED"
    assert accident.uncertainty_radius == 1200

    session.close()
    engine.dispose()
