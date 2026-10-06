from datetime import datetime, date, time
from sqlalchemy import Column, Integer, String, Float, Text, Date, Time, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from backend.database import Base

class Source(Base):
    __tablename__ = "sources"

    source_id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False)  # 'twitter', 'manual', 'official'
    external_id = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)

    accidents = relationship("Accident", back_populates="source")

class Accident(Base):
    __tablename__ = "accidents"

    accident_id = Column(Integer, primary_key=True, index=True)
    event_date = Column(Date, nullable=False, index=True)
    event_time = Column(Time, nullable=False)
    accident_type = Column(String(100), nullable=False)  # 'Motorcycle', 'Car', 'Truck', 'Multiple Vehicle'
    description = Column(Text, nullable=True)
    location_text = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    source_type = Column(String(50), default="manual")
    source_id = Column(Integer, ForeignKey("sources.source_id"), nullable=True)
    confidence = Column(Float, default=1.00)
    precision = Column(String(50), default="MEDIUM")  # 'HIGH', 'MEDIUM', 'ESTIMATED'
    uncertainty_radius = Column(Integer, default=250)  # in meters
    status = Column(String(50), default="REPORTED", index=True)  # 'DETECTED', 'REPORTED', 'UNDER REVIEW', 'VERIFIED', 'REJECTED', 'DUPLICATE', 'RESOLVED'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("Source", back_populates="accidents")
    media = relationship(
        "AccidentMedia",
        back_populates="accident",
        cascade="all, delete-orphan",
        order_by="AccidentMedia.media_id",
    )
    comments = relationship("Comment", back_populates="accident", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="accident", cascade="all, delete-orphan")


class AccidentMedia(Base):
    __tablename__ = "accident_media"

    media_id = Column(Integer, primary_key=True, index=True)
    accident_id = Column(Integer, ForeignKey("accidents.accident_id", ondelete="CASCADE"), nullable=False, index=True)
    media_url = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    alt_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    accident = relationship("Accident", back_populates="media")

class Comment(Base):
    __tablename__ = "comments"

    comment_id = Column(Integer, primary_key=True, index=True)
    accident_id = Column(Integer, ForeignKey("accidents.accident_id"), nullable=False)
    username = Column(String(100), default="Warga")
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="active")

    accident = relationship("Accident", back_populates="comments")

class Review(Base):
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, index=True)
    accident_id = Column(Integer, ForeignKey("accidents.accident_id"), nullable=False)
    reviewer_name = Column(String(100), default="Admin Moderator")
    decision = Column(String(50), nullable=False)  # 'VERIFIED', 'REJECTED', 'DUPLICATE'
    notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.utcnow)

    accident = relationship("Accident", back_populates="reviews")
