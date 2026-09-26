from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class AlertOut(BaseModel):
    id: str
    organization_id: str
    shipment_id: Optional[str] = None
    tracker_id: str
    alert_type: str
    message: str
    created_at: datetime
    email_sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
