import os
from typing import Optional, List, Dict, Any
from datetime import date, timedelta, datetime
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.database import engine, Base, get_db
from backend.models import Accident, Comment, Review, Source
from backend.schemas import (
    AccidentCreate, 
    AccidentDetail, 
    GeoJSONFeatureCollection, 
    GeoJSONFeature, 
    GeoJSONGeometry,
    CommentCreate,
    CommentResponse,
    ReviewCreate,
    ReviewResponse,
    AccidentLocationUpdate
)
from backend.seed_data import seed_database
from backend.services.media import MEDIA_DIR

# Inisialisasi tabel database & seed data awal
Base.metadata.create_all(bind=engine)
seed_database()

app = FastAPI(
    title="Traffic Accident WebGIS API",
    description="Backend API untuk Real-Time & Crowdsourced Traffic Accident Mapping",
    version="1.0.0"
)

# CORS middleware agar frontend bisa memanggil API tanpa hambatan
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 1. SLICE 1: Visualisasi Peta (GeoJSON Endpoint)
# -------------------------------------------------------------
@app.get("/api/accidents", response_model=GeoJSONFeatureCollection)
def get_accidents(
    status: Optional[str] = Query(None, description="Filter status, misal: VERIFIED, DETECTED, REPORTED"),
    accident_type: Optional[str] = Query(None, description="Filter tipe kecelakaan: Motorcycle, Car, etc."),
    target_date: Optional[date] = Query(None, description="Filter tanggal spesifik YYYY-MM-DD"),
    until_date: Optional[date] = Query(None, description="Filter tanggal sampai dengan YYYY-MM-DD"),
    active_only: bool = Query(False, description="Filter hanya kejadian aktif 24 jam terakhir"),
    db: Session = Depends(get_db)
):
    query = db.query(Accident)

    if active_only:
        yesterday = date.today() - timedelta(days=1)
        query = query.filter(
            Accident.status.in_(["DETECTED", "REPORTED", "UNDER REVIEW", "VERIFIED"]),
            Accident.event_date >= yesterday
        )

    if status and status != "ALL":
        query = query.filter(Accident.status == status)
    if accident_type and accident_type != "ALL":
        query = query.filter(Accident.accident_type == accident_type)
    if target_date:
        query = query.filter(Accident.event_date == target_date)
    if until_date:
        query = query.filter(Accident.event_date <= until_date)

    accidents = query.order_by(Accident.event_date.desc(), Accident.event_time.desc()).all()

    today = date.today()
    features = []
    for acc in accidents:
        is_recent = (today - acc.event_date).days <= 1 if acc.event_date else False
        is_active = (acc.status in ["DETECTED", "REPORTED", "UNDER REVIEW", "VERIFIED"]) and is_recent

        feature = GeoJSONFeature(
            type="Feature",
            geometry=GeoJSONGeometry(
                type="Point",
                coordinates=[acc.longitude, acc.latitude]
            ),
            properties={
                "accident_id": acc.accident_id,
                "event_date": acc.event_date.isoformat(),
                "event_time": acc.event_time.strftime("%H:%M"),
                "accident_type": acc.accident_type,
                "description": acc.description or "",
                "location_text": acc.location_text,
                "source_type": acc.source_type,
                "confidence": acc.confidence,
                "status": acc.status,
                "comments_count": len(acc.comments),
                "is_active": is_active,
                "precision": getattr(acc, "precision", "MEDIUM") or "MEDIUM",
                "uncertainty_radius": getattr(acc, "uncertainty_radius", 250) or 250
            }
        )
        features.append(feature)

    return GeoJSONFeatureCollection(type="FeatureCollection", features=features)

# -------------------------------------------------------------
# Detail Accident
# -------------------------------------------------------------
@app.get("/api/accidents/{accident_id}", response_model=AccidentDetail)
def get_accident_detail(accident_id: int, db: Session = Depends(get_db)):
    acc = db.query(Accident).filter(Accident.accident_id == accident_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accident event not found")
    return acc

# -------------------------------------------------------------
# 2. SLICE 2: Manual Crowdsourcing Report
# -------------------------------------------------------------
@app.post("/api/reports", response_model=AccidentDetail, status_code=201)
def create_manual_report(report_data: AccidentCreate, db: Session = Depends(get_db)):
    new_accident = Accident(
        event_date=report_data.event_date,
        event_time=report_data.event_time,
        accident_type=report_data.accident_type,
        description=report_data.description,
        location_text=report_data.location_text,
        latitude=report_data.latitude,
        longitude=report_data.longitude,
        source_type="manual",
        confidence=0.80,
        precision="HIGH",
        uncertainty_radius=100,
        status="REPORTED"  # Status awal laporan warga belum terverifikasi
    )
    db.add(new_accident)
    db.commit()
    db.refresh(new_accident)
    return new_accident

# -------------------------------------------------------------
# 3. SLICE 3: Moderator Review & Verification
# -------------------------------------------------------------
@app.post("/api/accidents/{accident_id}/review", response_model=AccidentDetail)
def review_accident(accident_id: int, review_in: ReviewCreate, db: Session = Depends(get_db)):
    acc = db.query(Accident).filter(Accident.accident_id == accident_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accident event not found")

    decision = review_in.decision.upper()
    if decision not in ["VERIFIED", "REJECTED", "DUPLICATE", "UNDER REVIEW", "RESOLVED"]:
        raise HTTPException(status_code=400, detail="Invalid decision value")

    # Catat audit review
    review_record = Review(
        accident_id=acc.accident_id,
        reviewer_name=review_in.reviewer_name,
        decision=decision,
        notes=review_in.notes
    )
    db.add(review_record)

    # Update status kejadian
    acc.status = decision
    if decision == "VERIFIED":
        acc.confidence = 1.0

    db.commit()
    db.refresh(acc)
    return acc

@app.patch("/api/accidents/{accident_id}/location", response_model=AccidentDetail)
def update_accident_location(
    accident_id: int,
    loc_in: AccidentLocationUpdate,
    db: Session = Depends(get_db)
):
    """
    Koreksi titik koordinat & lokasi kejadian oleh Petugas/Moderator.
    Secara otomatis mencatat koreksi ke kamus auto-learning agar sistem cerdas mengingatnya.
    """
    acc = db.query(Accident).filter(Accident.accident_id == accident_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accident event not found")

    acc.latitude = loc_in.latitude
    acc.longitude = loc_in.longitude
    if loc_in.location_text and loc_in.location_text.strip():
        acc.location_text = loc_in.location_text.strip()
    acc.precision = "HIGH"
    acc.uncertainty_radius = 100
    acc.status = "VERIFIED"
    acc.confidence = 1.0

    # Catat audit review
    review_record = Review(
        accident_id=acc.accident_id,
        reviewer_name="Petugas (Koreksi Lokasi)",
        decision="VERIFIED",
        notes=loc_in.notes or f"Lokasi dikoreksi ke: {acc.location_text} [{acc.latitude}, {acc.longitude}]"
    )
    db.add(review_record)

    # Simpan ke kamus auto-learning
    if loc_in.save_as_landmark and acc.location_text:
        from backend.services.landmarks import register_learned_landmark
        register_learned_landmark(
            alias=acc.location_text,
            lat=acc.latitude,
            lon=acc.longitude,
            display_name=acc.location_text,
            precision="HIGH",
            radius=100
        )

    db.commit()
    db.refresh(acc)
    return acc

# -------------------------------------------------------------
# 4. SLICE 4: Crowdsourced Comments
# -------------------------------------------------------------
@app.get("/api/accidents/{accident_id}/comments", response_model=List[CommentResponse])
def get_comments(accident_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).filter(Comment.accident_id == accident_id).order_by(Comment.created_at.asc()).all()
    return comments

@app.post("/api/accidents/{accident_id}/comments", response_model=CommentResponse, status_code=201)
def add_comment(accident_id: int, comment_in: CommentCreate, db: Session = Depends(get_db)):
    acc = db.query(Accident).filter(Accident.accident_id == accident_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accident event not found")

    new_comment = Comment(
        accident_id=accident_id,
        username=comment_in.username.strip() or "Warga",
        comment_text=comment_in.comment_text
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment

# -------------------------------------------------------------
# 5. SLICE 6: Social Media NLP & Ingestion Pipeline Simulator
# -------------------------------------------------------------
from backend.services.ingestion import SocialMediaIngestionPipeline
from pydantic import BaseModel

pipeline = SocialMediaIngestionPipeline()

class IngestTweetRequest(BaseModel):
    raw_text: str
    author: str = "@Merapi_Uncover"

SAMPLE_TWEETS = [
    {
        "id": 1,
        "type": "positive",
        "label": "Laka Jl. Kaliurang KM 14 (Motor vs Mobil)",
        "text": "[Min @Merapi_Uncover] Baru saja terjadi laka motor vs mobil di Jalan Kaliurang KM 14 dekat kampus UII. Korban luka, arus lalin terpantau padat merayap."
    },
    {
        "id": 2,
        "type": "positive",
        "label": "Truk Terguling di Ring Road Barat",
        "text": "Laka lantas truk box terguling di Ring Road Barat Gamping. Muatan tumpah ke badan jalan, lalu lintas macet parah arah utara."
    },
    {
        "id": 3,
        "type": "positive",
        "label": "Tabrakan Simpang Monjali",
        "text": "Terjadi kecelakaan beruntun melibatkan 3 mobil di Simpang Monjali Ring Road Utara, ambulans dan relawan sudah di lokasi TKP."
    },
    {
        "id": 4,
        "type": "negative",
        "label": "Opini / Sering Kecelakaan (Harus Ditolak NLP)",
        "text": "Daerah sini memang sering terjadi kecelakaan tiap malam, lampu penerangan jalan banyak yang mati."
    },
    {
        "id": 5,
        "type": "negative",
        "label": "Himbauan / Edukasi (Harus Ditolak NLP)",
        "text": "Himbauan Ditlantas Polda DIY: Waspada laka lantas di musim hujan, selalu cek kondisi rem dan kurangi kecepatan berkendara."
    }
]

@app.get("/api/simulator/samples")
def get_sample_tweets():
    return SAMPLE_TWEETS

@app.post("/api/simulator/ingest")
def simulate_tweet_ingest(payload: IngestTweetRequest, db: Session = Depends(get_db)):
    result = pipeline.process_tweet(raw_tweet=payload.raw_text, author=payload.author, db=db)
    return result

# -------------------------------------------------------------
# 5. SPATIAL ANALYTICS & BLACKSPOT ENDPOINT (FASE 5)
# -------------------------------------------------------------
@app.get("/api/analytics/blackspots")
def get_blackspots_analytics(db: Session = Depends(get_db)):
    accidents = db.query(Accident).all()
    
    corridors = {
        "Ring Road Utara / Monjali / Gejayan": 0,
        "Jl. Kaliurang (KM 5 - KM 14)": 0,
        "Jl. Solo / Maguwoharjo": 0,
        "Ring Road Barat / Gamping": 0,
        "Jl. Raya Piyungan - Prambanan": 0,
        "Jl. Parangtritis / Sewon": 0,
        "Jl. Magelang / Jombor": 0
    }
    
    time_distribution = {
        "Dini Hari (00:00 - 06:00)": 0,
        "Pagi Sibuk (06:00 - 09:00)": 0,
        "Siang (09:00 - 15:00)": 0,
        "Sore Sibuk (15:00 - 19:00)": 0,
        "Malam (19:00 - 24:00)": 0
    }
    
    vehicles_count = {}
    status_count = {"ACTIVE": 0, "VERIFIED": 0, "RESOLVED": 0, "UNDER REVIEW": 0, "DETECTED": 0, "REPORTED": 0}
    
    today = date.today()
    for acc in accidents:
        loc_lower = (acc.location_text or "").lower()
        if "ring road utara" in loc_lower or "monjali" in loc_lower or "gejayan" in loc_lower:
            corridors["Ring Road Utara / Monjali / Gejayan"] += 1
        elif "kaliurang" in loc_lower:
            corridors["Jl. Kaliurang (KM 5 - KM 14)"] += 1
        elif "solo" in loc_lower or "maguwo" in loc_lower:
            corridors["Jl. Solo / Maguwoharjo"] += 1
        elif "ring road barat" in loc_lower or "gamping" in loc_lower:
            corridors["Ring Road Barat / Gamping"] += 1
        elif "piyungan" in loc_lower or "prambanan" in loc_lower:
            corridors["Jl. Raya Piyungan - Prambanan"] += 1
        elif "parangtritis" in loc_lower or "sewon" in loc_lower:
            corridors["Jl. Parangtritis / Sewon"] += 1
        elif "magelang" in loc_lower or "jombor" in loc_lower:
            corridors["Jl. Magelang / Jombor"] += 1
        
        if acc.event_time:
            hour = acc.event_time.hour
            if 0 <= hour < 6:
                time_distribution["Dini Hari (00:00 - 06:00)"] += 1
            elif 6 <= hour < 9:
                time_distribution["Pagi Sibuk (06:00 - 09:00)"] += 1
            elif 9 <= hour < 15:
                time_distribution["Siang (09:00 - 15:00)"] += 1
            elif 15 <= hour < 19:
                time_distribution["Sore Sibuk (15:00 - 19:00)"] += 1
            else:
                time_distribution["Malam (19:00 - 24:00)"] += 1

        vtype = acc.accident_type or "Motorcycle"
        vehicles_count[vtype] = vehicles_count.get(vtype, 0) + 1
        
        st = acc.status or "REPORTED"
        status_count[st] = status_count.get(st, 0) + 1
            
        if acc.event_date and (today - acc.event_date).days <= 1 and st in ["DETECTED", "REPORTED", "UNDER REVIEW", "VERIFIED"]:
            status_count["ACTIVE"] += 1

    top_corridors = sorted([{"corridor": k, "count": v} for k, v in corridors.items() if v > 0], key=lambda x: x["count"], reverse=True)
    
    return {
        "total_records": len(accidents),
        "top_corridors": top_corridors,
        "time_distribution": time_distribution,
        "vehicles_count": vehicles_count,
        "status_count": status_count
    }

# -------------------------------------------------------------
# 6. SLICE 7: Autonomous Live Twitter/X Crawler & Scheduler
# -------------------------------------------------------------
import threading
import time
import logging
from datetime import datetime
from backend.database import SessionLocal
from backend.services.twitter_crawler import TwitterCrawlerWorker

crawler_worker = TwitterCrawlerWorker()

logger = logging.getLogger("AutoPoller")

auto_poller_state = {
    "enabled": os.getenv("ENABLE_AUTO_POLLER", "true").lower() == "true",
    "interval_minutes": int(os.getenv("POLL_INTERVAL_MINUTES", "5")),
    "target_account": os.getenv("TARGET_TWITTER_ACCOUNT", "Merapi_Uncover"),
    "last_run": None,
    "last_status": "Standby (Menunggu siklus berkala)",
    "last_results_count": 0,
    "total_runs": 0,
    "is_crawling_now": False
}

def auto_crawler_loop():
    logger.info(f"[AutoPoller] Background worker aktif. Memantau @{auto_poller_state['target_account']} setiap {auto_poller_state['interval_minutes']} menit.")
    
    # Beri jeda 8 detik saat startup sebelum run pertama
    time.sleep(8)
    
    while True:
        if auto_poller_state["enabled"]:
            try:
                auto_poller_state["is_crawling_now"] = True
                auto_poller_state["last_status"] = f"Sedang crawling live @{auto_poller_state['target_account']}..."
                logger.info(f"[AutoPoller] Menjalankan siklus crawling live...")
                
                db = SessionLocal()
                try:
                    results = crawler_worker.run_ingestion_cycle(db_session=db, pipeline=pipeline)
                    auto_poller_state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    auto_poller_state["last_results_count"] = len(results)
                    auto_poller_state["total_runs"] += 1
                    
                    detected_count = sum(1 for r in results if r.get("success"))
                    auto_poller_state["last_status"] = f"Sukses memeriksa {len(results)} cuitan ({detected_count} laka baru terdeteksi)"
                    logger.info(f"[AutoPoller] Selesai. {len(results)} cuitan diproses, {detected_count} laka terdeteksi.")
                finally:
                    db.close()
            except Exception as e:
                auto_poller_state["last_status"] = f"Error: {str(e)}"
                logger.error(f"[AutoPoller] Error: {e}")
            finally:
                auto_poller_state["is_crawling_now"] = False
        
        interval_secs = max(60, auto_poller_state["interval_minutes"] * 60)
        time.sleep(interval_secs)

@app.on_event("startup")
def startup_event():
    from backend.services.ingestion import repair_existing_accidents
    repair_existing_accidents()

    # Jalankan background poller thread otomatis
    poller_thread = threading.Thread(target=auto_crawler_loop, daemon=True, name="TwitterAutoPollerThread")
    poller_thread.start()

@app.get("/api/crawler/status")
def get_crawler_status():
    """
    Status live background crawler untuk monitoring di WebGIS
    """
    return auto_poller_state

@app.post("/api/crawler/toggle")
def toggle_auto_crawler(enable: bool = Query(...)):
    """
    Mengaktifkan / menonaktifkan polling otomatis
    """
    auto_poller_state["enabled"] = enable
    return {"enabled": auto_poller_state["enabled"], "status": "Updated"}

@app.post("/api/crawler/trigger")
def trigger_live_crawler(db: Session = Depends(get_db)):
    """
    Memicu proses crawling live X (@Merapi_Uncover) manual on-demand via headless browser
    """
    try:
        results = crawler_worker.run_ingestion_cycle(db_session=db, pipeline=pipeline)
        auto_poller_state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        auto_poller_state["last_results_count"] = len(results)
        auto_poller_state["total_runs"] += 1
        return {
            "status": "completed",
            "crawled_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static frontend jika ada
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

