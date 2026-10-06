import sys
import os
from datetime import date, time
from backend.database import engine, Base, SessionLocal
from backend.models import Accident, Source, Comment

def populate_2026_comprehensive_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Pastikan data sumber @Merapi_Uncover utama ada
    src_merapi = db.query(Source).filter(Source.source_type == "twitter").first()
    if not src_merapi:
        src_merapi = Source(
            source_type="twitter",
            external_id="171029384920",
            source_url="https://x.com/Merapi_Uncover",
            raw_text="[Min @Merapi_Uncover] Pusat Informasi Laka Lantas Yogyakarta Real-Time."
        )
        db.add(src_merapi)
        db.commit()
        db.refresh(src_merapi)

    # Dataset komprehensif Januari 2026 - Oktober 2026 (Real-Time)
    historical_accidents = [
        # --- JANUARI 2026 ---
        {
            "event_date": date(2026, 1, 8),
            "event_time": time(6, 45),
            "accident_type": "Motorcycle",
            "description": "[Breaking News] Terjadi laka tunggal pengendara motor tergelincir tumpahan solar di Ring Road Utara dekat simpang Monjali arah barat. Korban lecet ditolong ojol.",
            "location_text": "Ring Road Utara (Simpang Monjali), Sleman",
            "latitude": -7.7554,
            "longitude": 110.3698,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.88,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 1, 19),
            "event_time": time(14, 20),
            "accident_type": "Car",
            "description": "Laka lantas mobil sedan menabrak tiang lampu pembatas jalan di Jl. Kaliurang KM 8.5 depan gardu PLN. Arus padat merayap.",
            "location_text": "Jl. Kaliurang KM 8.5, Ngaglik, Sleman",
            "latitude": -7.7345,
            "longitude": 110.3951,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.92,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 1, 27),
            "event_time": time(21, 10),
            "accident_type": "Truck",
            "description": "Truk muatan pasir terguling melintang di tikungan tajem Jl. Magelang KM 12 dekat Tempel. Arus dialihkan ke jalur alternatif.",
            "location_text": "Jl. Magelang KM 12, Tempel, Sleman",
            "latitude": -7.6712,
            "longitude": 110.3340,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.95,
            "status": "VERIFIED",
            "precision": "MEDIUM",
            "uncertainty_radius": 400
        },

        # --- FEBRUARI 2026 ---
        {
            "event_date": date(2026, 2, 5),
            "event_time": time(8, 15),
            "accident_type": "Multiple Vehicle",
            "description": "Tabrakan beruntun mobil avanza, calya dan satu motor di lampu merah Gejayan Ring Road. Jalur lambat tersendat.",
            "location_text": "Simpang Empat Gejayan, Condongcatur",
            "latitude": -7.7598,
            "longitude": 110.3934,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.94,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 2, 14),
            "event_time": time(19, 40),
            "accident_type": "Motorcycle",
            "description": "Laka pemotor vario menabrak anjing menyeberang di Jl. Godean KM 6 dekat jembatan kali bedog. Korban dibawa ambulans PMI.",
            "location_text": "Jl. Godean KM 6, Sidoarum, Godean",
            "latitude": -7.7812,
            "longitude": 110.3245,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.85,
            "status": "VERIFIED",
            "precision": "MEDIUM",
            "uncertainty_radius": 400
        },
        {
            "event_date": date(2026, 2, 23),
            "event_time": time(11, 30),
            "accident_type": "Pedestrian",
            "description": "Penyebrang jalan lansia tersenggol mobil pickup di area pasar Kolombo Jl. Kaliurang KM 7. Korban luka ringan di kaki.",
            "location_text": "Pasar Kolombo, Jl. Kaliurang KM 7",
            "latitude": -7.7502,
            "longitude": 110.3905,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.90,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },

        # --- MARET 2026 ---
        {
            "event_date": date(2026, 3, 3),
            "event_time": time(7, 10),
            "accident_type": "Motorcycle",
            "description": "Laka senggolan sesama motor beat vs scoopy di simpang Pingit Jetis saat jam berangkat kerja. Sudah diselesaikan secara kekeluargaan.",
            "location_text": "Perempatan Pingit, Jetis, Kota Yogyakarta",
            "latitude": -7.7816,
            "longitude": 110.3601,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.89,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 3, 15),
            "event_time": time(16, 50),
            "accident_type": "Bus",
            "description": "Bus pariwisata serempetan dengan truk engkel di Jl. Solo KM 11 dekat Cupuwatu Kalasan. Ekor antrean sampai bandara.",
            "location_text": "Jl. Solo KM 11, Kalasan, Sleman",
            "latitude": -7.7815,
            "longitude": 110.4420,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.93,
            "status": "VERIFIED",
            "precision": "MEDIUM",
            "uncertainty_radius": 400
        },
        {
            "event_date": date(2026, 3, 28),
            "event_time": time(23, 15),
            "accident_type": "Car",
            "description": "Mobil brio hilang kendali masuk selokan mataram di dekat Pogung Dalangan Mlati. Pengemudi selamat, proses derek berlangsung.",
            "location_text": "Selokan Mataram (Pogung), Mlati",
            "latitude": -7.7610,
            "longitude": 110.3755,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.91,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },

        # --- APRIL 2026 ---
        {
            "event_date": date(2026, 4, 9),
            "event_time": time(9, 30),
            "accident_type": "Motorcycle",
            "description": "Laka tunggal pemotor oleng jatuh di turunan tajam Bukit Bintang Jl. Wonosari Piyungan. Korban dibawa ke Puskesmas Piyungan.",
            "location_text": "Bukit Bintang, Jl. Wonosari, Piyungan",
            "latitude": -7.8465,
            "longitude": 110.4812,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.92,
            "status": "VERIFIED",
            "precision": "MEDIUM",
            "uncertainty_radius": 400
        },
        {
            "event_date": date(2026, 4, 21),
            "event_time": time(17, 25),
            "accident_type": "Multiple Vehicle",
            "description": "Laka karambol 3 mobil di Ring Road Barat simpang Demak Ijo Banyuraden Gamping. Arus arah utara macet total.",
            "location_text": "Simpang Demak Ijo, Ring Road Barat, Gamping",
            "latitude": -7.7765,
            "longitude": 110.3378,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.96,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },

        # --- MEI 2026 ---
        {
            "event_date": date(2026, 5, 6),
            "event_time": time(12, 10),
            "accident_type": "Motorcycle",
            "description": "Laka adu banteng motor vs motor di Jl. Palagan Tentara Pelajar KM 9 dekat Hyatt Regency. Dua korban luka dilarikan ke RS Sardjito.",
            "location_text": "Jl. Palagan Tentara Pelajar KM 9, Ngaglik",
            "latitude": -7.7120,
            "longitude": 110.3802,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.94,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 5, 18),
            "event_time": time(20, 5),
            "accident_type": "Truck",
            "description": "Truk tronton bermuatan semen mogok dan patah as di tanjakan Playen perbatasan Bantul-Gunungkidul.",
            "location_text": "Jl. Yogyakarta - Wonosari KM 16",
            "latitude": -7.8620,
            "longitude": 110.5120,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.88,
            "status": "VERIFIED",
            "precision": "ESTIMATED",
            "uncertainty_radius": 1500
        },
        {
            "event_date": date(2026, 5, 29),
            "event_time": time(15, 45),
            "accident_type": "Car",
            "description": "Kecelakaan mobil pick up muatan sayur terguling di Ring Road Selatan Dongkelan Sewon. Muatan tercecer di aspal jalan.",
            "location_text": "Ring Road Selatan (Dongkelan), Sewon, Bantul",
            "latitude": -7.8285,
            "longitude": 110.3541,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.91,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },

        # --- JUNI 2026 ---
        {
            "event_date": date(2026, 6, 7),
            "event_time": time(8, 30),
            "accident_type": "Motorcycle",
            "description": "Laka pemotor tertabrak mobil saat putar balik di U-Turn Ring Road Utara dekat Kampus UPN Veteran Condongcatur.",
            "location_text": "Ring Road Utara (UPN Veteran), Sleman",
            "latitude": -7.7601,
            "longitude": 110.4082,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.93,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 6, 20),
            "event_time": time(18, 50),
            "accident_type": "Motorcycle",
            "description": "Kecelakaan motor vs sepeda ontel di Jl. Bantul KM 7 Sewon. Pengayuh sepeda dilarikan ke RS PKU Bantul.",
            "location_text": "Jl. Bantul KM 7, Pendowoharjo, Sewon",
            "latitude": -7.8540,
            "longitude": 110.3420,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.89,
            "status": "VERIFIED",
            "precision": "MEDIUM",
            "uncertainty_radius": 400
        },

        # --- JULI 2026 ---
        {
            "event_date": date(2026, 7, 4),
            "event_time": time(13, 15),
            "accident_type": "Car",
            "description": "Laka beruntun mobil avanza menabrak bagian belakang truk tronton di Flyover Jombor arah Magelang. Arus lalin tersendat 1 km.",
            "location_text": "Flyover Jombor, Sinduadi, Mlati",
            "latitude": -7.7478,
            "longitude": 110.3621,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.95,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 7, 19),
            "event_time": time(22, 40),
            "accident_type": "Motorcycle",
            "description": "Pemotor rx king menabrak trotoar pembatas jalan di Simpang Tugu Jogja. Korban ditolong relawan ambulans.",
            "location_text": "Simpang Tugu Pal Putih, Kota Yogyakarta",
            "latitude": -7.7828,
            "longitude": 110.3670,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.90,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },

        # --- AGUSTUS 2026 ---
        {
            "event_date": date(2026, 8, 12),
            "event_time": time(11, 00),
            "accident_type": "Truck",
            "description": "Truk pengangkut galon air terguling di perempatan Ring Road Kronggahan Gamping. Puluhan galon pecah di jalan.",
            "location_text": "Simpang Kronggahan, Trihanggo, Gamping",
            "latitude": -7.7510,
            "longitude": 110.3450,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.94,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 8, 25),
            "event_time": time(17, 35),
            "accident_type": "Motorcycle",
            "description": "Laka pemotor vario terperosok pasir proyek galian di Jl. Parangtritis KM 8 Sewon Bantul. Korban sadar lecet di tangan.",
            "location_text": "Jl. Parangtritis KM 8, Sewon, Bantul",
            "latitude": -7.8680,
            "longitude": 110.3640,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.87,
            "status": "VERIFIED",
            "precision": "MEDIUM",
            "uncertainty_radius": 400
        },

        # --- SEPTEMBER 2026 ---
        {
            "event_date": date(2026, 9, 10),
            "event_time": time(14, 15),
            "accident_type": "Car",
            "description": "Mobil innova tertabrak bus trans jogja di persimpangan Jl. Gejayan Affandi dekat pasar Colombo.",
            "location_text": "Jl. Affandi (Gejayan), Caturtunggal, Depok",
            "latitude": -7.7650,
            "longitude": 110.3910,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.96,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 9, 28),
            "event_time": time(7, 30),
            "accident_type": "Motorcycle",
            "description": "Laka motor vs motor di Jalan Kaliurang KM 12 arah Jogja. Arus lalin tersendat, sudah ditangani warga sekitar.",
            "location_text": "Jalan Kaliurang KM 12, Sleman",
            "latitude": -7.7012,
            "longitude": 110.4132,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.88,
            "status": "DETECTED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 9, 29),
            "event_time": time(14, 15),
            "accident_type": "Car",
            "description": "Mobil sedan menabrak pembatas jalan di Ring Road Utara dekat UPN Condongcatur.",
            "location_text": "Ring Road Utara, Condongcatur, Sleman",
            "latitude": -7.7601,
            "longitude": 110.4082,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 1.0,
            "status": "VERIFIED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 9, 30),
            "event_time": time(8, 45),
            "accident_type": "Multiple Vehicle",
            "description": "Tabrakan beruntun 3 kendaraan dekat flyover Jombor arah utara, lajur kanan ditutup sementara.",
            "location_text": "Jl. Magelang KM 6 (Flyover Jombor)",
            "latitude": -7.7478,
            "longitude": 110.3621,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.92,
            "status": "UNDER REVIEW",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },

        # --- OKTOBER 2026 (REAL-TIME AKTIF) ---
        {
            "event_date": date(2026, 10, 1),
            "event_time": time(6, 10),
            "accident_type": "Truck",
            "description": "Truk muatan material patah as roda di lajur kiri Jl. Solo dekat Bandara Adisutjipto.",
            "location_text": "Jl. Solo KM 10, Kalasan",
            "latitude": -7.7825,
            "longitude": 110.4328,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.95,
            "status": "VERIFIED",
            "precision": "MEDIUM",
            "uncertainty_radius": 400
        },
        {
            "event_date": date(2026, 10, 1),
            "event_time": time(11, 40),
            "accident_type": "Motorcycle",
            "description": "Kecelakaan tunggal sepeda motor tergelincir pasir di tikungan Jl. Palagan.",
            "location_text": "Jl. Palagan Tentara Pelajar KM 8",
            "latitude": -7.7180,
            "longitude": 110.3792,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.80,
            "status": "DETECTED",
            "precision": "ESTIMATED",
            "uncertainty_radius": 1500
        },
        {
            "event_date": date(2026, 10, 2),
            "event_time": time(13, 5),
            "accident_type": "Pedestrian",
            "description": "Pejalan kaki tersenggol pengendara saat menyeberang di area pasar Dongkelan.",
            "location_text": "Jl. Bantul KM 5, Dongkelan",
            "latitude": -7.8285,
            "longitude": 110.3541,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 1.0,
            "status": "VERIFIED",
            "precision": "MEDIUM",
            "uncertainty_radius": 400
        },
        {
            "event_date": date(2026, 10, 2),
            "event_time": time(17, 18),
            "accident_type": "Motorcycle",
            "description": "Kejadian tadi pagi jam 06.33 telah terjadi kecelakaan 2 unit motor loaksi pom piyungan jalan piyungan Prambanan kayaknya korban ada 3 yang 1 boncengan yang 1 sendiri korban ada anak sekolah di himbau selalu hati hati dalam perjalanan jika mau kerja, sekolah, atau mau berpergian",
            "location_text": "Jl. Raya Piyungan - Prambanan (Dekat SPBU Piyungan)",
            "latitude": -7.8120,
            "longitude": 110.4780,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 1.0,
            "status": "VERIFIED",
            "precision": "ESTIMATED",
            "uncertainty_radius": 1500
        },
        {
            "event_date": date(2026, 10, 2),
            "event_time": time(21, 8),
            "accident_type": "Truck",
            "description": "[Breaking News] 20:59 terjadi kecelakaan lalu lintas malam ini , truk terguling di tikungan bokong semar jalan wonosari\n\nmfmmar_",
            "location_text": "Jl. Wonosari, Piyungan",
            "latitude": -7.8250,
            "longitude": 110.4350,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.90,
            "status": "DETECTED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 10, 3),
            "event_time": time(0, 54),
            "accident_type": "Car",
            "description": "[Breaking News] 00:54 terjadi kecelakaan lalu lintas , mobil naik pembatas jalan malam ini di Ring road dongkelan (3/10/2026) \n\n#Jogja #Yogyakarta #Merapiuncover #Merapinews\nyuspiiin_",
            "location_text": "Ring road dongkelan (3/10/2026) (Perkiraan Yogyakarta)",
            "latitude": -7.7956,
            "longitude": 110.3695,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.92,
            "status": "DETECTED",
            "precision": "ESTIMATED",
            "uncertainty_radius": 1500
        },
        {
            "event_date": date(2026, 10, 3),
            "event_time": time(9, 15),
            "accident_type": "Motorcycle",
            "description": "[Min @Merapi_Uncover] Baru saja laka adu banteng Beat vs Vario di simpang Monjali sisi selatan, lalin padat merayap. Sudah dalam penanganan PMI dan relawan.",
            "location_text": "Simpang Monjali (Sisi Selatan), Sinduadi, Mlati",
            "latitude": -7.7562,
            "longitude": 110.3690,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.95,
            "status": "DETECTED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 10, 3),
            "event_time": time(14, 40),
            "accident_type": "Multiple Vehicle",
            "description": "[Min @Merapi_Uncover] Laka tabrakan beruntun mobil dan dua motor di Jl. Kaliurang KM 13 depan Kampus Terpadu UII. Korban selamat luka ringan, proses evakuasi.",
            "location_text": "Jl. Kaliurang KM 13, Ngemplak, Sleman",
            "latitude": -7.6910,
            "longitude": 110.4140,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.94,
            "status": "UNDER REVIEW",
            "precision": "HIGH",
            "uncertainty_radius": 150
        },
        {
            "event_date": date(2026, 10, 3),
            "event_time": time(16, 20),
            "accident_type": "Motorcycle",
            "description": "[Min @Merapi_Uncover] Terjadi laka tunggal pemotor terpeleset tumpahan minyak di tikungan Kentungan Ring Road Utara. Hati-hati melintas.",
            "location_text": "Ring Road Utara (Simpang Kentungan), Depok, Sleman",
            "latitude": -7.7580,
            "longitude": 110.3850,
            "source_type": "twitter",
            "source_id": src_merapi.source_id,
            "confidence": 0.88,
            "status": "DETECTED",
            "precision": "HIGH",
            "uncertainty_radius": 150
        }
    ]

    # Bersihkan data lama jika perlu atau sinkronkan
    db.query(Accident).delete()
    db.commit()

    count = 0
    for acc in historical_accidents:
        accident_obj = Accident(
            event_date=acc["event_date"],
            event_time=acc["event_time"],
            accident_type=acc["accident_type"],
            description=acc["description"],
            location_text=acc["location_text"],
            latitude=acc["latitude"],
            longitude=acc["longitude"],
            source_type=acc["source_type"],
            source_id=acc["source_id"],
            confidence=acc["confidence"],
            status=acc["status"],
            precision=acc.get("precision", "HIGH"),
            uncertainty_radius=acc.get("uncertainty_radius", 150)
        )
        db.add(accident_obj)
        count += 1

    db.commit()
    print(f"Berhasil men-seed {count} data kecelakaan komprehensif Januari - Oktober 2026!")
    db.close()

if __name__ == "__main__":
    populate_2026_comprehensive_data()
