import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    tracker_id = Column(String(36), ForeignKey("trackers.id", ondelete="SET NULL"), index=True, nullable=True)
    status = Column(String(50), default="CREATED", nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    allowed_min_temp = Column(Float, nullable=False, default=2.0)
    allowed_max_temp = Column(Float, nullable=False, default=8.0)
    grace_period_readings = Column(Integer, nullable=False, default=3)
    consecutive_breach_count = Column(Integer, nullable=False, default=0)
    breach_active = Column(Boolean, default=False, nullable=False)
    breach_started_at = Column(DateTime(timezone=True), nullable=True)
    alert_sent_at = Column(DateTime(timezone=True), nullable=True)
    origin_lat = Column(Float, nullable=True)
    origin_lng = Column(Float, nullable=True)
    target_lat = Column(Float, nullable=True)
    target_lng = Column(Float, nullable=True)
    route_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("allowed_min_temp < allowed_max_temp", name="chk_min_less_than_max_temp"),
        CheckConstraint("grace_period_readings >= 1", name="chk_grace_period_readings_positive"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="shipments")
    tracker = relationship("Tracker", back_populates="shipments")
    telemetry_readings = relationship("TelemetryReading", back_populates="shipment")
    alerts = relationship("Alert", back_populates="shipment")
