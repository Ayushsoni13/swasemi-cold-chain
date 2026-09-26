import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Tracker(Base):
    __tablename__ = "trackers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    mqtt_topic = Column(String(255), nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="trackers")
    shipments = relationship("Shipment", back_populates="tracker")
    telemetry_readings = relationship("TelemetryReading", back_populates="tracker")
    alerts = relationship("Alert", back_populates="tracker")
