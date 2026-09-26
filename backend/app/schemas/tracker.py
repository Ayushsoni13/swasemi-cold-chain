from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class TrackerCreate(BaseModel):
    name: str
    mqtt_topic: str
    organization_id: Optional[str] = None  # Used only by Super Admin

class TrackerOut(BaseModel):
    id: str
    organization_id: str
    name: str
    mqtt_topic: str
    status: str
    last_seen: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
