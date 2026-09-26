import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.seed import seed_data
from app.models.shipment import Shipment
from app.models.tracker import Tracker
from app.models.telemetry import TelemetryReading
from app.models.alert import Alert

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    db = SessionLocal()
    try:
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

# 1. User A sees only Organization A trackers
def test_1_user_a_sees_only_org_a_trackers():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.get("/trackers", headers=headers)
    assert res.status_code == 200
    trackers = res.json()
    tracker_ids = [t["id"] for t in trackers]
    
    assert "TRK-001" in tracker_ids
    assert "TRK-003" in tracker_ids
    assert "TRK-002" not in tracker_ids  # TRK-002 belongs to Org B

# 2. User A cannot access Organization B tracker by ID
def test_2_user_a_cannot_access_org_b_tracker_by_id():
    headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.get("/trackers/TRK-002", headers=headers)
    assert res.status_code == 404

# 3. User A sees only Organization A shipments
def test_3_user_a_sees_only_org_a_shipments():
    admin_headers = get_auth_header("admin@swasemi.demo", "DemoAdmin123!")
    
    # Start shipment for Org A
    ship_a = client.post("/shipments/start", headers=admin_headers, json={
        "tracker_id": "TRK-001",
        "organization_id": "org-pharma-a"
    }).json()
    
    # Start shipment for Org B
    ship_b = client.post("/shipments/start", headers=admin_headers, json={
        "tracker_id": "TRK-002",
        "organization_id": "org-biocold-b"
    }).json()

    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.get("/shipments", headers=user_a_headers)
    assert res.status_code == 200
    shipments = res.json()
    shipment_ids = [s["id"] for s in shipments]
    
    assert ship_a["id"] in shipment_ids
    assert ship_b["id"] not in shipment_ids

# 4. User A cannot access Organization B shipment
def test_4_user_a_cannot_access_org_b_shipment():
    admin_headers = get_auth_header("admin@swasemi.demo", "DemoAdmin123!")
    ship_b = client.post("/shipments/start", headers=admin_headers, json={
        "tracker_id": "TRK-002",
        "organization_id": "org-biocold-b"
    }).json()

    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.get(f"/shipments/{ship_b['id']}", headers=user_a_headers)
    assert res.status_code == 404

# 5. User A cannot create a tracker for Organization B
def test_5_user_a_cannot_create_tracker_for_org_b():
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.post("/trackers", headers=user_a_headers, json={
        "name": "Malicious Tracker",
        "mqtt_topic": "swasemi/telemetry/malicious",
        "organization_id": "org-biocold-b"  # Attempt to create in Org B
    })
    assert res.status_code == 201
    tracker = res.json()
    # Must be forced to User A's organization (org-pharma-a)
    assert tracker["organization_id"] == "org-pharma-a"
    assert tracker["organization_id"] != "org-biocold-b"

# 6. User A cannot create a shipment using Organization B tracker
def test_6_user_a_cannot_create_shipment_using_org_b_tracker():
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.post("/shipments/start", headers=user_a_headers, json={
        "tracker_id": "TRK-002"  # TRK-002 belongs to Org B
    })
    assert res.status_code in [404, 400]

# 7. Super Admin can access both organizations
def test_7_super_admin_can_access_both_organizations():
    admin_headers = get_auth_header("admin@swasemi.demo", "DemoAdmin123!")
    res = client.get("/trackers", headers=admin_headers)
    assert res.status_code == 200
    trackers = res.json()
    tracker_ids = [t["id"] for t in trackers]
    
    assert "TRK-001" in tracker_ids
    assert "TRK-002" in tracker_ids
    assert "TRK-003" in tracker_ids

    # Super Admin can get Org B tracker by ID
    res_b = client.get("/trackers/TRK-002", headers=admin_headers)
    assert res_b.status_code == 200
    assert res_b.json()["id"] == "TRK-002"

# 8. Tracker/shipment organization mismatch is rejected
def test_8_tracker_shipment_org_mismatch_rejected():
    admin_headers = get_auth_header("admin@swasemi.demo", "DemoAdmin123!")
    res = client.post("/shipments/start", headers=admin_headers, json={
        "tracker_id": "TRK-002",  # Belongs to Org B
        "organization_id": "org-pharma-a"  # Specifying Org A
    })
    assert res.status_code == 400
    assert "mismatch" in res.json()["detail"].lower()

# 9. Shipment can be started
def test_9_shipment_can_be_started():
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    res = client.post("/shipments/start", headers=user_a_headers, json={
        "tracker_id": "TRK-001",
        "allowed_min_temp": 2.0,
        "allowed_max_temp": 8.0,
        "grace_period_readings": 3
    })
    assert res.status_code == 201
    shipment = res.json()
    assert shipment["status"] == "IN_TRANSIT"
    assert shipment["started_at"] is not None
    assert shipment["tracker_id"] == "TRK-001"

# 10. Shipment can be ended
def test_10_shipment_can_be_ended():
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    start_res = client.post("/shipments/start", headers=user_a_headers, json={
        "tracker_id": "TRK-001"
    })
    shipment_id = start_res.json()["id"]

    end_res = client.post(f"/shipments/{shipment_id}/end", headers=user_a_headers)
    assert end_res.status_code == 200
    ended_shipment = end_res.json()
    assert ended_shipment["status"] == "DELIVERED"
    assert ended_shipment["ended_at"] is not None

# 11. Second active shipment for same tracker is rejected
def test_11_second_active_shipment_rejected():
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    
    # First active shipment
    start_1 = client.post("/shipments/start", headers=user_a_headers, json={
        "tracker_id": "TRK-003"
    })
    assert start_1.status_code == 201

    # Second active shipment attempt on same tracker TRK-003
    start_2 = client.post("/shipments/start", headers=user_a_headers, json={
        "tracker_id": "TRK-003"
    })
    assert start_2.status_code == 400
    assert "already has an active shipment" in start_2.json()["detail"].lower()

# 12. Ended shipment cannot be ended again
def test_12_ended_shipment_cannot_be_ended_again():
    user_a_headers = get_auth_header("usera@swasemi.demo", "DemoUser123!")
    
    # Start & end shipment
    start_res = client.post("/shipments/start", headers=user_a_headers, json={
        "tracker_id": "TRK-001"
    })
    shipment_id = start_res.json()["id"]

    end_1 = client.post(f"/shipments/{shipment_id}/end", headers=user_a_headers)
    assert end_1.status_code == 200

    # Try ending again
    end_2 = client.post(f"/shipments/{shipment_id}/end", headers=user_a_headers)
    assert end_2.status_code == 400
    assert "not active" in end_2.json()["detail"].lower() or "already ended" in end_2.json()["detail"].lower()
