import sys
import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Add project root to sys.path so simulator can be imported in tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.main import app
from app.db.session import SessionLocal
from app.db.seed import seed_data
from app.models.shipment import Shipment
from app.models.tracker import Tracker
from app.models.telemetry import TelemetryReading
from app.models.alert import Alert
from app.services.telemetry_service import process_telemetry_payload
from simulator.simulator import TRACKERS, generate_telemetry

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    db = SessionLocal()
    try:
        from app.services.email_service import email_service, sent_emails_log
        sent_emails_log.clear()
        email_service.test_mode = True
        db.query(Alert).delete()
        db.query(TelemetryReading).delete()
        db.query(Shipment).delete()
        db.query(Tracker).delete()
        db.commit()
        seed_data(db)
    finally:
        db.close()


def get_auth_header(email: str, password: str):
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# 1. Valid telemetry payload validation
def test_1_valid_telemetry_payload_validation():
    db = SessionLocal()
    try:
        payload = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 4.5,
            "humidity": 65.0,
            "battery_level": 95.0,
            "door_open": False
        }
        process_telemetry_payload(db, payload)
        
        tracker = db.query(Tracker).filter(Tracker.id == "TRK-001").first()
        assert tracker.status == "ONLINE"
        assert tracker.last_seen is not None
    finally:
        db.close()

# 2. Invalid telemetry payload rejected
def test_2_invalid_telemetry_payload_rejected():
    db = SessionLocal()
    try:
        # Invalid latitude (>90)
        invalid_lat = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 150.0,
            "longitude": 77.5946,
            "temperature": 4.5
        }
        result_1 = process_telemetry_payload(db, invalid_lat)
        assert result_1 is None

        # Invalid humidity (>100)
        invalid_hum = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 4.5,
            "humidity": 150.0
        }
        result_2 = process_telemetry_payload(db, invalid_hum)
        assert result_2 is None
    finally:
        db.close()

# 3. Telemetry before shipment start is NOT stored
def test_3_telemetry_before_shipment_start_not_stored():
    db = SessionLocal()
    try:
        payload = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 4.5
        }
        result = process_telemetry_payload(db, payload)
        assert result is None
        
        count = db.query(TelemetryReading).count()
        assert count == 0
    finally:
        db.close()

# 4. Telemetry during active shipment IS stored
def test_4_telemetry_during_active_shipment_is_stored():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    start_res = client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001"})
    assert start_res.status_code == 201
    shipment_id = start_res.json()["id"]

    db = SessionLocal()
    try:
        payload = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 4.5,
            "humidity": 60.0,
            "battery_level": 90.0,
            "door_open": False
        }
        reading = process_telemetry_payload(db, payload)
        assert reading is not None
        assert reading.shipment_id == shipment_id
        assert reading.temperature == 4.5
        
        count = db.query(TelemetryReading).filter(TelemetryReading.shipment_id == shipment_id).count()
        assert count == 1
    finally:
        db.close()

# 5. Telemetry after shipment end is NOT stored
def test_5_telemetry_after_shipment_end_not_stored():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    start_res = client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001"})
    shipment_id = start_res.json()["id"]

    # Send telemetry during active shipment
    db = SessionLocal()
    try:
        payload_1 = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 4.5
        }
        reading_1 = process_telemetry_payload(db, payload_1)
        assert reading_1 is not None
    finally:
        db.close()

    # End Shipment
    end_res = client.post(f"/shipments/{shipment_id}/end", headers=headers)
    assert end_res.status_code == 200

    # Send telemetry after shipment end
    db = SessionLocal()
    try:
        payload_2 = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9800,
            "longitude": 77.6000,
            "temperature": 4.8
        }
        reading_2 = process_telemetry_payload(db, payload_2)
        assert reading_2 is None  # GATE DROPS TELEMETRY FOR ENDED SHIPMENT
        
        count = db.query(TelemetryReading).filter(TelemetryReading.shipment_id == shipment_id).count()
        assert count == 1  # Only reading 1 stored
    finally:
        db.close()

# 6. Correct organization_id is stored
def test_6_correct_organization_id_stored():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    start_res = client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001"})
    shipment_id = start_res.json()["id"]

    db = SessionLocal()
    try:
        payload = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 5.2
        }
        reading = process_telemetry_payload(db, payload)
        assert reading is not None
        assert reading.organization_id == "org-pharma-a"
    finally:
        db.close()

# 7. Correct shipment_id is stored
def test_7_correct_shipment_id_stored():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    start_res = client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001"})
    expected_shipment_id = start_res.json()["id"]

    db = SessionLocal()
    try:
        payload = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 4.1
        }
        reading = process_telemetry_payload(db, payload)
        assert reading.shipment_id == expected_shipment_id
    finally:
        db.close()

# 8. Tracker last_seen updates
def test_8_tracker_last_seen_updates():
    db = SessionLocal()
    try:
        now_time = datetime.now(timezone.utc).isoformat()
        payload = {
            "tracker_id": "TRK-002",
            "timestamp": now_time,
            "latitude": 19.0760,
            "longitude": 72.8777,
            "temperature": 5.0
        }
        process_telemetry_payload(db, payload)
        
        tracker = db.query(Tracker).filter(Tracker.id == "TRK-002").first()
        assert tracker.status == "ONLINE"
        assert tracker.last_seen is not None
    finally:
        db.close()

# 9. Simulator publishes all 3 trackers
def test_9_simulator_publishes_all_3_trackers():
    assert len(TRACKERS) == 3
    tracker_ids = [t["tracker_id"] for t in TRACKERS]
    assert "TRK-001" in tracker_ids
    assert "TRK-002" in tracker_ids
    assert "TRK-003" in tracker_ids

    for tracker in TRACKERS:
        t_data = generate_telemetry(tracker)
        assert "tracker_id" in t_data
        assert "latitude" in t_data
        assert "longitude" in t_data
        assert "temperature" in t_data
        assert "humidity" in t_data
        assert "battery_level" in t_data
        assert "door_open" in t_data

# 10. Cross-tenant telemetry access is blocked
def test_10_cross_tenant_telemetry_access_blocked():
    # User A starts shipment and receives telemetry
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    start_res = client.post("/shipments/start", headers=user_a_headers, json={"tracker_id": "TRK-001"})
    shipment_id = start_res.json()["id"]

    db = SessionLocal()
    try:
        payload = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 4.5
        }
        process_telemetry_payload(db, payload)
    finally:
        db.close()

    # User B attempts to get telemetry for User A's shipment -> 404 Not Found
    user_b_headers = get_auth_header("userb@swasemi.demo", "DemoUser123!")
    tel_res = client.get(f"/shipments/{shipment_id}/telemetry", headers=user_b_headers)
    assert tel_res.status_code == 404

    # User A gets telemetry for their shipment -> 200 OK
    tel_res_a = client.get(f"/shipments/{shipment_id}/telemetry", headers=user_a_headers)
    assert tel_res_a.status_code == 200
    readings = tel_res_a.json()
    assert len(readings) == 1
    assert readings[0]["temperature"] == 4.5
