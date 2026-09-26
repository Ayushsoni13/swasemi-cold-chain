import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    shipment_id = Column(String(36), ForeignKey("shipments.id", ondelete="SET NULL"), index=True, nullable=True)
    tracker_id = Column(String(36), ForeignKey("trackers.id", ondelete="CASCADE"), index=True, nullable=False)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="alerts")
    shipment = relationship("Shipment", back_populates="alerts")
    tracker = relationship("Tracker", back_populates="alerts")
