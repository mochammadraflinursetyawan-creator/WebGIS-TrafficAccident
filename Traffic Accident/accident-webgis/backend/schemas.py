from datetime import date, time, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

# Schema untuk Comment
class CommentBase(BaseModel):
    username: str = "Warga"
    comment_text: str

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    comment_id: int
    accident_id: int
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True

# Schema untuk Review
class ReviewCreate(BaseModel):
    decision: str = Field(..., description="VERIFIED, REJECTED, atau DUPLICATE")
    notes: Optional[str] = None
    reviewer_name: str = "Moderator"

class ReviewResponse(BaseModel):
    review_id: int
    accident_id: int
    decision: str
    notes: Optional[str]
    reviewer_name: str
    reviewed_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class AccidentMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    media_id: int
    media_url: str
    alt_text: Optional[str] = None

class AccidentLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    location_text: Optional[str] = None
    save_as_landmark: bool = True
    notes: Optional[str] = None

# Schema untuk Input Laporan Kecelakaan (Manual Report)
class AccidentCreate(BaseModel):
    event_date: date
    event_time: time
    accident_type: str = "Motorcycle"
    description: Optional[str] = None
    location_text: str
    latitude: float
    longitude: float
    source_type: str = "manual"

# Schema Detail Accident
class AccidentDetail(BaseModel):
    accident_id: int
    event_date: date
    event_time: time
    accident_type: str
    description: Optional[str]
    location_text: str
    latitude: float
    longitude: float
    source_type: str
    confidence: float
    precision: Optional[str] = "MEDIUM"
    uncertainty_radius: Optional[int] = 250
    status: str
    created_at: datetime
    comments: List[CommentResponse] = []
    reviews: List[ReviewResponse] = []
    media: List[AccidentMediaResponse] = Field(default_factory=list)

    class Config:
        orm_mode = True
        from_attributes = True

# Standard GeoJSON Schemas
class GeoJSONGeometry(BaseModel):
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any]

class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
