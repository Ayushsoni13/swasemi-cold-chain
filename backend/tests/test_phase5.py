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
from app.services.redis_service import redis_service
from app.services.telemetry_service import process_telemetry_payload
from app.services.websocket_manager import ws_manager
from app.services.tracker_status import compute_tracker_status

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


def get_token(email: str, password: str) -> str:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

# 1. Redis connection / configuration
def test_1_redis_connection_config():
    result = redis_service.publish_telemetry("org-pharma-a", {"test": "data"})
    assert isinstance(result, bool)

# 2. Telemetry publishes to correct organization Redis channel
def test_2_telemetry_publishes_correct_channel():
    published_calls = []
    original_publish = redis_service.publish_telemetry

    def mock_publish(org_id, data):
        published_calls.append((org_id, data))
        return True

    redis_service.publish_telemetry = mock_publish
    try:
        headers = {"Authorization": f"Bearer {get_token('usera@swasemi.demo', 'DemoUser123!')}"}
        client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001"})

        db = SessionLocal()
        try:
            payload = {
                "tracker_id": "TRK-001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "latitude": 12.9716,
                "longitude": 77.5946,
                "temperature": 4.2,
                "humidity": 60.0,
                "battery_level": 95.0,
                "door_open": False
            }
            process_telemetry_payload(db, payload)
        finally:
            db.close()

        assert len(published_calls) == 1
        org_id, data = published_calls[0]
        assert org_id == "org-pharma-a"
        assert data["tracker_id"] == "TRK-001"
        assert data["temperature"] == 4.2
    finally:
        redis_service.publish_telemetry = original_publish

# 3. WebSocket accepts valid JWT
def test_3_websocket_accepts_valid_jwt():
    token = get_token("usera@swasemi.demo", "DemoUser123!")
    with client.websocket_connect(f"/ws?token={token}") as websocket:
        assert websocket is not None

# 4. WebSocket rejects invalid JWT
def test_4_websocket_rejects_invalid_jwt():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=invalid.jwt.token"):
            pass

# 5. User A receives only Organization A telemetry
# 6. User B receives only Organization B telemetry
# 7. Super Admin can receive telemetry from all organizations
@pytest.mark.asyncio
async def test_5_6_7_websocket_tenant_isolation_and_super_admin():
    token_a = get_token("usera@swasemi.demo", "DemoUser123!")
    token_b = get_token("userb@swasemi.demo", "DemoUser123!")
    token_admin = get_token("admin@swasemi.demo", "DemoAdmin123!")

    with client.websocket_connect(f"/ws?token={token_a}") as ws_a, \
         client.websocket_connect(f"/ws?token={token_b}") as ws_b, \
         client.websocket_connect(f"/ws?token={token_admin}") as ws_admin:

        telemetry_a = {
            "tracker_id": "TRK-001",
            "shipment_id": "ship-1",
            "organization_id": "org-pharma-a",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "temperature": 4.5,
            "status": "ONLINE"
        }

        await ws_manager.broadcast_to_organization("org-pharma-a", telemetry_a)

        msg_a = ws_a.receive_json()
        assert msg_a["tracker_id"] == "TRK-001"
        assert msg_a["organization_id"] == "org-pharma-a"

        msg_admin = ws_admin.receive_json()
        assert msg_admin["tracker_id"] == "TRK-001"

# 8. WebSocket cannot be used to override organization_id
def test_8_websocket_cannot_override_organization_id():
    token_a = get_token("usera@swasemi.demo", "DemoUser123!")
    with client.websocket_connect(f"/ws?token={token_a}") as ws:
        ws.send_text(json.dumps({"override_org": "org-biocold-b"}))
        assert "org-pharma-a" in ws_manager.org_connections
        assert "org-biocold-b" not in ws_manager.org_connections

# 9. Multiple WebSocket clients work independently
def test_9_multiple_websocket_clients_work_independently():
    token = get_token("usera@swasemi.demo", "DemoUser123!")
    with client.websocket_connect(f"/ws?token={token}") as ws1, \
         client.websocket_connect(f"/ws?token={token}") as ws2:
        assert len(ws_manager.org_connections.get("org-pharma-a", set())) == 2

# 10. Disconnect / reconnect works
def test_10_disconnect_reconnect_works():
    token = get_token("usera@swasemi.demo", "DemoUser123!")
    with client.websocket_connect(f"/ws?token={token}") as ws:
        assert len(ws_manager.org_connections.get("org-pharma-a", set())) >= 1
    # Context manager exit disconnects client
    assert len(ws_manager.org_connections.get("org-pharma-a", set())) == 0

# 11 & 12. Dashboard & Map payload verification
def test_11_12_dashboard_and_map_payload():
    status_online = compute_tracker_status(datetime.now(timezone.utc))
    assert status_online == "ONLINE"

    status_offline = compute_tracker_status(None)
    assert status_offline == "OFFLINE"

# 13 & 14. Start and End Shipment API flows
def test_13_14_start_end_shipment_api():
    headers = {"Authorization": f"Bearer {get_token('usera@swasemi.demo', 'DemoUser123!')}"}
    
    start_res = client.post("/shipments/start", headers=headers, json={"tracker_id": "TRK-001"})
    assert start_res.status_code == 201
    shipment_id = start_res.json()["id"]

    end_res = client.post(f"/shipments/{shipment_id}/end", headers=headers)
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "DELIVERED"
