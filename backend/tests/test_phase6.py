import sys
import os
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.main import app
from app.db.session import SessionLocal
from app.db.seed import seed_data
from app.models.shipment import Shipment
from app.models.tracker import Tracker
from app.models.telemetry import TelemetryReading
from app.models.alert import Alert
from app.services.telemetry_service import process_telemetry_payload
from app.services.email_service import email_service, sent_emails_log

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    db = SessionLocal()
    try:
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

# 1. Normal temperature creates no alert
def test_1_normal_temperature_creates_no_alert():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    ship_res = client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001", "allowed_min_temp": 2.0, "allowed_max_temp": 8.0, "grace_period_readings": 3})
    assert ship_res.status_code == 201

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
        
        alerts_count = db.query(Alert).count()
        assert alerts_count == 0
        assert len(sent_emails_log) == 0
    finally:
        db.close()

# 2. One bad reading below grace creates no alert
def test_2_bad_reading_below_grace_creates_no_alert():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001", "allowed_min_temp": 2.0, "allowed_max_temp": 8.0, "grace_period_readings": 3})

    db = SessionLocal()
    try:
        # Reading 1: Breach (10.0°C > 8.0°C)
        payload = {
            "tracker_id": "TRK-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 10.0
        }
        process_telemetry_payload(db, payload)

        db.expire_all()
        shipment = db.query(Shipment).filter(Shipment.tracker_id == "TRK-001").first()
        assert shipment.consecutive_breach_count == 1
        assert shipment.breach_active is False
        assert db.query(Alert).count() == 0
        assert len(sent_emails_log) == 0
    finally:
        db.close()

# 3, 4, 5. Grace period exceeded creates alert, continuous breach sends 1 email, additional bad readings do not duplicate
def test_3_4_5_grace_period_exceeded_creates_alert_one_email_no_duplicates():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001", "allowed_min_temp": 2.0, "allowed_max_temp": 8.0, "grace_period_readings": 3})

    db = SessionLocal()
    try:
        # Reading 1 (Breach count = 1)
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 10.0})
        assert db.query(Alert).count() == 0

        # Reading 2 (Breach count = 2)
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 10.5})
        assert db.query(Alert).count() == 0

        # Reading 3 (Breach count = 3 >= Grace period 3) -> BREACH ACTIVATED & EMAIL SENT!
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 11.0})
        
        shipment = db.query(Shipment).filter(Shipment.tracker_id == "TRK-001").first()
        assert shipment.breach_active is True
        assert db.query(Alert).count() == 1
        assert len(sent_emails_log) == 1

        # Reading 4 & 5 (Continued breach) -> NO SECOND EMAIL / ALERT
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 11.2})
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 11.5})
        
        assert db.query(Alert).count() == 1
        assert len(sent_emails_log) == 1
    finally:
        db.close()

# 6 & 7. Recovery resets breach state; new breach after recovery sends new alert
def test_6_7_recovery_resets_state_and_new_breach_sends_new_alert():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001", "allowed_min_temp": 2.0, "allowed_max_temp": 8.0, "grace_period_readings": 2})

    db = SessionLocal()
    try:
        # First breach (2 readings >= grace 2)
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 9.0})
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 9.5})
        
        assert db.query(Alert).count() == 1
        assert len(sent_emails_log) == 1

        # Recovery reading (4.0°C in range 2-8)
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 4.0})
        
        db.expire_all()
        shipment = db.query(Shipment).filter(Shipment.tracker_id == "TRK-001").first()
        assert shipment.breach_active is False
        assert shipment.consecutive_breach_count == 0

        # Second breach (2 readings >= grace 2)
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 10.0})
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 10.5})

        assert db.query(Alert).count() == 2
        assert len(sent_emails_log) == 2
    finally:
        db.close()

# 8. Alert state survives restart
def test_8_alert_state_survives_restart():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    start_res = client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001", "grace_period_readings": 1})
    shipment_id = start_res.json()["id"]

    db = SessionLocal()
    try:
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 12.0})
    finally:
        db.close()

    # Re-query fresh DB session simulating app restart
    db2 = SessionLocal()
    try:
        shipment = db2.query(Shipment).filter(Shipment.id == shipment_id).first()
        assert shipment.breach_active is True
        assert shipment.consecutive_breach_count >= 1
    finally:
        db2.close()

# 9. User A cannot access Org B alerts
def test_9_user_a_cannot_access_org_b_alerts():
    admin_headers = get_auth_header("admin@swasemi.demo", "DemoAdmin123!")
    client.post("/shipments/start", headers=admin_headers, json={"tracker_id": "TRK-002", "organization_id": "org-biocold-b", "grace_period_readings": 1})

    db = SessionLocal()
    try:
        process_telemetry_payload(db, {"tracker_id": "TRK-002", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 19.0760, "longitude": 72.8777, "temperature": 15.0})
    finally:
        db.close()

    # User A requests alerts -> Org B alert is excluded
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.get("/alerts", headers=user_a_headers)
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) == 0

# 10. User A cannot access Org B shipment history
def test_10_user_a_cannot_access_org_b_shipment_history():
    admin_headers = get_auth_header("admin@swasemi.demo", "DemoAdmin123!")
    ship_b = client.post("/shipments/start", headers=admin_headers, json={"tracker_id": "TRK-002", "organization_id": "org-biocold-b"}).json()

    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.get(f"/shipments/{ship_b['id']}/telemetry", headers=user_a_headers)
    assert res.status_code == 404

# 11. Super Admin can access both
def test_11_super_admin_can_access_both_alerts_and_history():
    admin_headers = get_auth_header("admin@swasemi.demo", "DemoAdmin123!")
    client.post("/shipments/start", headers=admin_headers, json={"tracker_id": "TRK-002", "organization_id": "org-biocold-b", "grace_period_readings": 1})

    db = SessionLocal()
    try:
        process_telemetry_payload(db, {"tracker_id": "TRK-002", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 19.0760, "longitude": 72.8777, "temperature": 15.0})
    finally:
        db.close()

    res = client.get("/alerts", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

# 12. Historical telemetry is returned correctly
def test_12_historical_telemetry_returned_correctly():
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    ship_a = client.post("/shipments/start", headers=user_a_headers, json={"tracker_id": "TRK-001"}).json()

    db = SessionLocal()
    try:
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 4.5})
    finally:
        db.close()

    res = client.get(f"/shipments/{ship_a['id']}/telemetry", headers=user_a_headers)
    assert res.status_code == 200
    readings = res.json()
    assert len(readings) == 1
    assert readings[0]["temperature"] == 4.5

# 13. CSV export returns correct headers and data
def test_13_csv_export_returns_correct_data():
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    ship_a = client.post("/shipments/start", headers=user_a_headers, json={"tracker_id": "TRK-001"}).json()

    db = SessionLocal()
    try:
        process_telemetry_payload(db, {"tracker_id": "TRK-001", "timestamp": datetime.now(timezone.utc).isoformat(), "latitude": 12.9716, "longitude": 77.5946, "temperature": 4.5, "humidity": 65.0, "battery_level": 95.0, "door_open": False})
    finally:
        db.close()

    res = client.get(f"/shipments/{ship_a['id']}/export", headers=user_a_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "attachment; filename=" in res.headers.get("content-disposition", "")
    csv_text = res.text
    assert "timestamp,tracker_id,latitude,longitude,temperature,humidity,battery_level,door_open" in csv_text
    assert "TRK-001" in csv_text
    assert "4.5" in csv_text

# 14. Cross-tenant CSV access is blocked
def test_14_cross_tenant_csv_access_blocked():
    admin_headers = get_auth_header("admin@swasemi.demo", "DemoAdmin123!")
    ship_b = client.post("/shipments/start", headers=admin_headers, json={"tracker_id": "TRK-002", "organization_id": "org-biocold-b"}).json()

    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.get(f"/shipments/{ship_b['id']}/export", headers=user_a_headers)
    assert res.status_code == 404
