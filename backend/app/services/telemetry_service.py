import json
import logging
import asyncio
from typing import Optional, Union, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.schemas.telemetry import TelemetryPayloadSchema
from app.models.tracker import Tracker
from app.models.shipment import Shipment
from app.models.telemetry import TelemetryReading
from app.models.alert import Alert
from app.models.user import User
from app.models.enums import ShipmentStatusEnum, AlertTypeEnum
from app.services.redis_service import redis_service
from app.services.websocket_manager import ws_manager
from app.services.tracker_status import compute_tracker_status
from app.services.email_service import email_service

logger = logging.getLogger("TelemetryService")

def process_telemetry_payload(
    db: Session,
    raw_payload: Union[str, bytes, dict]
) -> Optional[TelemetryReading]:
    """
    Processes incoming MQTT telemetry:
    1. Validates payload structure using Pydantic v2.
    2. Updates tracker last_seen and status ('ONLINE').
    3. SHIPMENT GATE: Checks if tracker has an active shipment ('IN_TRANSIT').
       - If NO active shipment: drops telemetry from shipment history.
       - If ACTIVE shipment exists: saves telemetry to PostgreSQL.
    4. TEMPERATURE BREACH ENGINE: Checks threshold, grace period, continuous breach state, and sends email alerts.
    5. REDIS PUB/SUB & WEBSOCKET: Publishes stored telemetry.
    """
    # Reset any pending transaction snapshot
    try:
        db.commit()
    except Exception:
        db.rollback()

    if isinstance(raw_payload, (str, bytes)):
        try:
            payload_dict = json.loads(raw_payload)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode telemetry JSON: {e}")
            return None
    else:
        payload_dict = raw_payload

    try:
        telemetry_in = TelemetryPayloadSchema.model_validate(payload_dict)
    except ValidationError as ve:
        logger.warning(f"Telemetry validation error for tracker '{payload_dict.get('tracker_id')}': {ve}")
        return None

    tracker = db.query(Tracker).filter(Tracker.id == telemetry_in.tracker_id).first()
    if not tracker:
        logger.warning(f"Received telemetry for unknown tracker: '{telemetry_in.tracker_id}'")
        return None

    # Update Tracker status & last_seen
    tracker.last_seen = telemetry_in.timestamp
    tracker.status = compute_tracker_status(telemetry_in.timestamp)
    db.add(tracker)
    db.commit()

    # SHIPMENT GATE: Check for ACTIVE shipment (IN_TRANSIT)
    db.expire_all()
    active_shipment = db.query(Shipment).filter(
        Shipment.tracker_id == tracker.id,
        Shipment.status == ShipmentStatusEnum.IN_TRANSIT.value
    ).first()

    if not active_shipment:
        logger.info(f"Gate: No active shipment for tracker '{tracker.id}'. Telemetry NOT saved to shipment history.")
        return None

    # Save Telemetry Reading for Active Shipment
    reading = TelemetryReading(
        organization_id=tracker.organization_id,
        shipment_id=active_shipment.id,
        tracker_id=tracker.id,
        timestamp=telemetry_in.timestamp,
        latitude=telemetry_in.latitude,
        longitude=telemetry_in.longitude,
        temperature=telemetry_in.temperature,
        humidity=telemetry_in.humidity,
        battery_level=telemetry_in.battery_level,
        door_open=telemetry_in.door_open
    )

    db.add(reading)
    db.commit()
    db.refresh(reading)
    
    logger.info(f"Saved telemetry reading for shipment '{active_shipment.id}' (Tracker: '{tracker.id}', Temp: {reading.temperature}°C)")

    # 4. TEMPERATURE BREACH ENGINE LOGIC
    is_breach = (reading.temperature < active_shipment.allowed_min_temp) or (reading.temperature > active_shipment.allowed_max_temp)

    if not is_breach:
        # Rule 1 & 6: Temperature inside range -> reset breach count and clear breach state
        if active_shipment.consecutive_breach_count > 0 or active_shipment.breach_active:
            active_shipment.consecutive_breach_count = 0
            active_shipment.breach_active = False
            db.add(active_shipment)
            db.commit()
    else:
        # Rule 2: Temperature outside range -> increment consecutive breach count
        active_shipment.consecutive_breach_count = (active_shipment.consecutive_breach_count or 0) + 1
        
        # Rule 3, 4, 5: Check grace period
        if active_shipment.consecutive_breach_count >= active_shipment.grace_period_readings:
            if not active_shipment.breach_active:
                # Rule 4: Grace period exceeded! Continuous breach starts NOW.
                active_shipment.breach_active = True
                active_shipment.breach_started_at = reading.timestamp
                active_shipment.alert_sent_at = reading.timestamp
                db.add(active_shipment)

                # Create Alert Record
                alert = Alert(
                    organization_id=tracker.organization_id,
                    shipment_id=active_shipment.id,
                    tracker_id=tracker.id,
                    alert_type=AlertTypeEnum.TEMPERATURE_BREACH.value,
                    message=f"Temperature breach detected! Current: {reading.temperature}°C (Allowed range: {active_shipment.allowed_min_temp}°C - {active_shipment.allowed_max_temp}°C). Grace period of {active_shipment.grace_period_readings} readings exceeded.",
                    created_at=reading.timestamp,
                    email_sent_at=reading.timestamp
                )
                db.add(alert)
                db.commit()

                # Find tenant user or default email to send notification
                org_user = db.query(User).filter(User.organization_id == tracker.organization_id).first()
                recipient_email = org_user.email if org_user else "alerts@swasemi.demo"
                org_name = tracker.organization.name if tracker.organization else tracker.organization_id

                # Send ONE email
                email_service.send_temperature_breach_email(
                    to_email=recipient_email,
                    org_name=org_name,
                    tracker_name=tracker.name,
                    shipment_id=active_shipment.id,
                    current_temp=reading.temperature,
                    min_temp=active_shipment.allowed_min_temp,
                    max_temp=active_shipment.allowed_max_temp,
                    timestamp=reading.timestamp,
                    message_detail=alert.message
                )
            else:
                # Rule 5: Continuous breach is already active -> DO NOT send duplicate email/alert
                db.add(active_shipment)
                db.commit()
        else:
            # Below grace period -> DO NOT create/send alert
            db.add(active_shipment)
            db.commit()

    # REDIS PUB/SUB & WS EVENT PAYLOAD
    telemetry_event: Dict[str, Any] = {
        "tracker_id": tracker.id,
        "shipment_id": active_shipment.id,
        "organization_id": tracker.organization_id,
        "timestamp": reading.timestamp.isoformat() if reading.timestamp else datetime.now(timezone.utc).isoformat(),
        "latitude": reading.latitude,
        "longitude": reading.longitude,
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "battery_level": reading.battery_level,
        "door_open": reading.door_open,
        "status": tracker.status
    }
    
    redis_service.publish_telemetry(tracker.organization_id, telemetry_event)
    ws_manager.broadcast_from_thread(tracker.organization_id, telemetry_event)


    return reading
