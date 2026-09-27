from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
from typing import Optional, Any
from datetime import datetime, timezone


class TelemetryPayloadSchema(BaseModel):
    tracker_id: str
    timestamp: Optional[datetime] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    temperature: float
    humidity: Optional[float] = Field(None, ge=0.0, le=100.0)
    battery_level: Optional[float] = Field(None, ge=0.0, le=100.0)
    door_open: bool = False

    @model_validator(mode="before")
    @classmethod
    def populate_tracker_id_and_timestamp(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "tracker_id" not in values:
                for key in ("device_id", "deviceId", "vehicle_id", "vehicleId", "vehicle", "truck_id", "trackerId", "id"):
                    if key in values and values[key]:
                        values["tracker_id"] = str(values[key])
                        break

            if "timestamp" not in values or not values["timestamp"]:
                values["timestamp"] = datetime.now(timezone.utc)
        return values


class TelemetryReadingOut(BaseModel):
    id: str
    organization_id: str
    shipment_id: Optional[str] = None
    tracker_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    temperature: float
    humidity: Optional[float] = None
    battery_level: Optional[float] = None
    door_open: bool

    model_config = ConfigDict(from_attributes=True)
