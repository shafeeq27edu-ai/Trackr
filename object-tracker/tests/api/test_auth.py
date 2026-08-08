import pytest
from datetime import datetime, timedelta
import jwt

from core.security import ALGORITHM, SECRET_KEY

@pytest.fixture
def test_user(auth_client):
    user_data = {
        "email": "testauth@example.com",
        "password": "Password123!",
        "username": "testauth"
    }
    res = auth_client.post("/api/v1/auth/register", json=user_data)
    assert res.status_code in [200, 201]
    return user_data

def test_register_valid(auth_client):
    res = auth_client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "Password123!",
        "username": "newuser"
    })
    assert res.status_code in [200, 201]
    assert res.json()["email"] == "newuser@example.com"

def test_register_duplicate(auth_client, test_user):
    res = auth_client.post("/api/v1/auth/register", json={
        "email": test_user["email"],
        "password": "DifferentPassword1!",
        "username": "newusername"
    })
    assert res.status_code == 400
    assert "Email already registered" in res.json()["message"]

def test_register_password_too_short(auth_client):
    res = auth_client.post("/api/v1/auth/register", json={
        "email": "shortpass@example.com",
        "password": "short",
        "username": "shortpass"
    })
    assert res.status_code == 422

def test_register_invalid_email(auth_client):
    res = auth_client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "password": "Password123!",
        "username": "notanemail"
    })
    assert res.status_code == 422

def test_login_valid(auth_client, test_user):
    res = auth_client.post("/api/v1/auth/login", data={
        "username": test_user["email"],
        "password": test_user["password"]
    })
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_login_wrong_password(auth_client, test_user):
    res = auth_client.post("/api/v1/auth/login", data={
        "username": test_user["email"],
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["message"]

    # Also check non-existent user gives exact same message
    res_nonexistent = auth_client.post("/api/v1/auth/login", data={
        "username": "doesnotexist@example.com",
        "password": "SomePassword1!"
    })
    assert res_nonexistent.status_code == 401
    assert "Incorrect email or password" in res_nonexistent.json()["message"]

def test_protected_no_token(auth_client):
    res = auth_client.get("/api/v1/auth/me")
    assert res.status_code == 401

def test_protected_invalid_token(auth_client):
    res = auth_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert res.status_code == 401

def test_protected_expired_token(auth_client):
    expired_payload = {
        "user_id": "dummy_id",
        "exp": datetime.utcnow() - timedelta(minutes=15)
    }
    token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
    res = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401

def test_system_endpoints_no_auth(auth_client):
    for endpoint in ["performance", "diagnostics", "resources", "models"]:
        res = auth_client.get(f"/api/v1/system/{endpoint}")
        assert res.status_code == 401

def test_public_system_endpoints(auth_client):
    for endpoint in ["health", "ready", "live"]:
        res = auth_client.get(f"/api/v1/system/{endpoint}")
        assert res.status_code == 200

def test_cors_origin_rejected(auth_client):
    res = auth_client.options("/api/v1/auth/login", headers={
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "POST"
    })
    assert res.status_code == 400
    assert "Disallowed CORS origin" in res.text
