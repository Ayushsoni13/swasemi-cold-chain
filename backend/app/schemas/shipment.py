from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

class ShipmentStartRequest(BaseModel):
    tracker_id: str
    allowed_min_temp: float = 2.0
    allowed_max_temp: float = 8.0
    grace_period_readings: int = 3
    organization_id: Optional[str] = None  # Used only by Super Admin
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    target_lat: Optional[float] = None
    target_lng: Optional[float] = None
    route_name: Optional[str] = None

    @field_validator("allowed_max_temp")
    def validate_temp_range(cls, v, values):
        min_temp = values.data.get("allowed_min_temp", 2.0)
        if v <= min_temp:
            raise ValueError("allowed_max_temp must be greater than allowed_min_temp")
        return v

    @field_validator("grace_period_readings")
    def validate_grace_period(cls, v):
        if v < 1:
            raise ValueError("grace_period_readings must be at least 1")
        return v

class ShipmentOut(BaseModel):
    id: str
    organization_id: str
    tracker_id: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    allowed_min_temp: float
    allowed_max_temp: float
    grace_period_readings: int
    breach_active: bool
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    target_lat: Optional[float] = None
    target_lng: Optional[float] = None
    route_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
