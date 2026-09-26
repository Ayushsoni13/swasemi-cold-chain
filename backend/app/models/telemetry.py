import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, Boolean, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    shipment_id = Column(String(36), ForeignKey("shipments.id", ondelete="SET NULL"), index=True, nullable=True)
    tracker_id = Column(String(36), ForeignKey("trackers.id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False, default=lambda: datetime.now(timezone.utc))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=True)
    battery_level = Column(Float, nullable=True)
    door_open = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("idx_shipment_timestamp", "shipment_id", "timestamp"),
        CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="chk_latitude_bounds"),
        CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="chk_longitude_bounds"),
        CheckConstraint("humidity IS NULL OR (humidity >= 0.0 AND humidity <= 100.0)", name="chk_humidity_bounds"),
        CheckConstraint("battery_level IS NULL OR (battery_level >= 0.0 AND battery_level <= 100.0)", name="chk_battery_bounds"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="telemetry_readings")
    shipment = relationship("Shipment", back_populates="telemetry_readings")
    tracker = relationship("Tracker", back_populates="telemetry_readings")
