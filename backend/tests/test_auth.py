import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.db.seed import seed_data

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_seed():
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()

def test_1_valid_login_succeeds():
    response = client.post("/auth/login", json={
        "email": "usera@swasemi.demo",
        "password": "DemoUser123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_2_invalid_email_fails():
    response = client.post("/auth/login", json={
        "email": "nonexistent@swasemi.demo",
        "password": "DemoUser123!"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_3_invalid_password_fails():
    response = client.post("/auth/login", json={
        "email": "usera@swasemi.demo",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_4_jwt_contains_expected_claims():
    response = client.post("/auth/login", json={
        "email": "usera@swasemi.demo",
        "password": "DemoUser123!"
    })
    token = response.json()["access_token"]
    payload = decode_access_token(token)
    
    assert payload is not None
    assert "sub" in payload
    assert payload["sub"] == "user-org-a"
    assert "role" in payload
    assert payload["role"] == "USER"
    assert "organization_id" in payload
    assert payload["organization_id"] == "org-pharma-a"

def test_5_password_never_returned():
    # 1. Login response
    login_resp = client.post("/auth/login", json={
        "email": "usera@swasemi.demo",
        "password": "DemoUser123!"
    })
    assert "password" not in login_resp.text
    assert "password_hash" not in login_resp.text

    # 2. Get User details endpoint
    token = login_resp.json()["access_token"]
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert "password" not in me_data
    assert "password_hash" not in me_data

def test_6_normal_user_has_organization_id_in_jwt():
    response = client.post("/auth/login", json={
        "email": "userb@swasemi.demo",
        "password": "DemoUser123!"
    })
    token = response.json()["access_token"]
    payload = decode_access_token(token)
    
    assert payload["role"] == "USER"
    assert payload["organization_id"] == "org-biocold-b"

def test_7_super_admin_has_null_organization_id():
    response = client.post("/auth/login", json={
        "email": "admin@swasemi.demo",
        "password": "DemoAdmin123!"
    })
    token = response.json()["access_token"]
    payload = decode_access_token(token)
    
    assert payload["role"] == "SUPER_ADMIN"
    assert payload["organization_id"] is None

def test_8_protected_endpoint_rejects_missing_jwt():
    response = client.get("/auth/me")
    assert response.status_code == 401

def test_9_protected_endpoint_rejects_invalid_jwt():
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert response.status_code == 401

def test_10_super_admin_authorization_dependency():
    # 1. Normal user calling super admin route -> 403 Forbidden
    login_user = client.post("/auth/login", json={
        "email": "usera@swasemi.demo",
        "password": "DemoUser123!"
    })
    user_token = login_user.json()["access_token"]
    forbidden_resp = client.get("/api/v1/auth/admin-only", headers={"Authorization": f"Bearer {user_token}"})
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()["detail"] == "Super Admin access required"

    # 2. Super admin user calling super admin route -> 200 OK
    login_admin = client.post("/auth/login", json={
        "email": "admin@swasemi.demo",
        "password": "DemoAdmin123!"
    })
    admin_token = login_admin.json()["access_token"]
    ok_resp = client.get("/api/v1/auth/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
    assert ok_resp.status_code == 200
    assert ok_resp.json()["message"] == "Welcome Super Admin"
