from datetime import datetime

from backend.services.ingestion import resolve_tweet_datetime


def test_resolve_tweet_datetime_uses_indonesia_local_time():
    raw = "Selamat malam Min Mohon Identitas. Saya izin melaporkan barusan saya di jam 17.55 tadi terjadi kecelakaan ada orang yang melawan arah dari utara daerah lampu merah UKDW sementara saya dari arah barat mau ke utara belok kiri jalan terus waktu tadi lampu utara warna hijau"
    dt = resolve_tweet_datetime(raw, fallback_datetime=datetime(2026, 10, 5, 6, 56))

    assert dt.year == 2026
    assert dt.month == 10
    assert dt.day == 4
    assert dt.hour == 17
    assert dt.minute == 55


def test_resolve_tweet_datetime_uses_yesterday_for_kemarin():
    raw = "Kemarin jam 15.25-15.30 terjadi kecelakaan di dekat SMP Kanisius"

    dt = resolve_tweet_datetime(raw, fallback_datetime=datetime(2026, 10, 5, 18, 0))

    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 10, 4, 15, 25)


def test_resolve_tweet_datetime_uses_tweet_date_when_report_has_no_date():
    raw = "00:23 kecelakaan di samping SMP Kanisius Gayam"

    dt = resolve_tweet_datetime(raw, fallback_datetime=datetime(2026, 10, 4, 1, 0))

    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 10, 4, 0, 23)


def test_resolve_tweet_datetime_rolls_back_barusan_time_past_midnight():
    raw = "Barusan terjadi kecelakaan jam 17.55 tadi"

    dt = resolve_tweet_datetime(raw, fallback_datetime=datetime(2026, 10, 5, 6, 56))

    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 10, 4, 17, 55)
