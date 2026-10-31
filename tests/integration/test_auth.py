"""Integration tests for secure authentication, JWT tokens, and Role-Based Access Control (RBAC).

Tests:
1. Secure login for ADMIN and ANALYST accounts.
2. Invalid credentials and non-existent user rejections (HTTP 401).
3. Session inspection via GET /api/auth/me.
4. Token revocation on logout via POST /api/auth/logout.
5. ADMIN-only permissions enforcement:
   - ADMIN can list, create, and delete application users (HTTP 200/201).
   - ADMIN can access system analytics (HTTP 200).
6. ANALYST role restrictions:
   - ANALYST is blocked from user management (HTTP 403 Forbidden).
   - ANALYST is blocked from analytics (HTTP 403 Forbidden).
   - ANALYST is permitted on transaction ledger, prediction, and alert triage (HTTP 200).
7. Unauthenticated access rejections on protected routes (HTTP 401 Unauthorized).
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.config import settings

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Login & Token Issuance Tests
# ---------------------------------------------------------------------------
def test_login_admin_success():
    """Verifies successful login for ADMIN account and JWT issuance."""
    response = client.post(
        "/api/auth/login",
        json={
            "username": settings.DEFAULT_ADMIN_USERNAME,
            "password": settings.DEFAULT_ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["username"] == settings.DEFAULT_ADMIN_USERNAME
    assert data["user"]["role"] == "ADMIN"


def test_login_analyst_success():
    """Verifies successful login for ANALYST account and JWT issuance."""
    response = client.post(
        "/api/auth/login",
        json={
            "username": settings.DEFAULT_ANALYST_USERNAME,
            "password": settings.DEFAULT_ANALYST_PASSWORD,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == settings.DEFAULT_ANALYST_USERNAME
    assert data["user"]["role"] == "ANALYST"


def test_login_invalid_password():
    """Verifies HTTP 401 Unauthorized when password does not match."""
    response = client.post(
        "/api/auth/login",
        json={
            "username": settings.DEFAULT_ADMIN_USERNAME,
            "password": "IncorrectPassword123!",
        },
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    assert "invalid" in response.json()["detail"].lower()


def test_login_nonexistent_user():
    """Verifies HTTP 401 Unauthorized when user account does not exist."""
    response = client.post(
        "/api/auth/login",
        json={
            "username": "ghost_user_999",
            "password": "SomePassword123!",
        },
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 2. Session Inspection & Logout Tests
# ---------------------------------------------------------------------------
def test_get_me_endpoint():
    """Verifies retrieving authenticated user profile via /api/auth/me."""
    # Login to get token
    login_resp = client.post(
        "/api/auth/login",
        json={
            "username": settings.DEFAULT_ANALYST_USERNAME,
            "password": settings.DEFAULT_ANALYST_PASSWORD,
        },
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query /api/auth/me
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == settings.DEFAULT_ANALYST_USERNAME
    assert me_data["role"] == "ANALYST"


def test_logout_revokes_token():
    """Verifies that logging out revokes the token and blocks subsequent requests."""
    # Login
    login_resp = client.post(
        "/api/auth/login",
        json={
            "username": settings.DEFAULT_ANALYST_USERNAME,
            "password": settings.DEFAULT_ANALYST_PASSWORD,
        },
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Logout
    logout_resp = client.post("/api/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "success"

    # Attempt reuse of revoked token -> 401 Unauthorized
    reuse_resp = client.get("/api/auth/me", headers=headers)
    assert reuse_resp.status_code == 401
    assert "revoked" in reuse_resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 3. Role-Based Permissions Tests (ADMIN vs ANALYST)
# ---------------------------------------------------------------------------
def test_admin_can_manage_users_and_access_analytics():
    """Verifies that ADMIN can manage users and access analytics."""
    # Login as ADMIN
    admin_login = client.post(
        "/api/auth/login",
        json={
            "username": settings.DEFAULT_ADMIN_USERNAME,
            "password": settings.DEFAULT_ADMIN_PASSWORD,
        },
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin accesses analytics
    analytics_resp = client.get("/api/analytics", headers=admin_headers)
    assert analytics_resp.status_code == 200

    # 2. Admin creates a new analyst
    new_username = "test_analyst_soc"
    create_resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "username": new_username,
            "email": "test.soc@fraudshield.ai",
            "password": "TemporaryPassword123!",
            "full_name": "Test SOC Investigator",
            "role": "ANALYST",
        },
    )
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]

    # 3. Admin lists users
    list_resp = client.get("/api/users", headers=admin_headers)
    assert list_resp.status_code == 200
    assert any(u["username"] == new_username for u in list_resp.json()["users"])

    # 4. Admin deletes user
    del_resp = client.delete(f"/api/users/{created_id}", headers=admin_headers)
    assert del_resp.status_code == 200


def test_analyst_blocked_from_admin_only_endpoints():
    """Verifies that an ANALYST is rejected with HTTP 403 Forbidden on ADMIN-only routes."""
    # Login as ANALYST
    analyst_login = client.post(
        "/api/auth/login",
        json={
            "username": settings.DEFAULT_ANALYST_USERNAME,
            "password": settings.DEFAULT_ANALYST_PASSWORD,
        },
    )
    analyst_token = analyst_login.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Blocked from listing users -> 403 Forbidden
    resp_users = client.get("/api/users", headers=analyst_headers)
    assert resp_users.status_code == 403
    assert "ADMIN role required" in resp_users.json()["detail"]

    # 2. Blocked from creating users -> 403 Forbidden
    resp_create = client.post(
        "/api/users",
        headers=analyst_headers,
        json={
            "username": "unauthorized_user",
            "email": "unauth@fraudshield.ai",
            "password": "Password123!",
            "full_name": "Unauthorized",
            "role": "ANALYST",
        },
    )
    assert resp_create.status_code == 403

    # 3. Blocked from analytics -> 403 Forbidden
    resp_analytics = client.get("/api/analytics", headers=analyst_headers)
    assert resp_analytics.status_code == 403


def test_analyst_permitted_on_investigation_endpoints():
    """Verifies that an ANALYST can view transactions, submit predictions, and review alerts."""
    analyst_login = client.post(
        "/api/auth/login",
        json={
            "username": settings.DEFAULT_ANALYST_USERNAME,
            "password": settings.DEFAULT_ANALYST_PASSWORD,
        },
    )
    analyst_token = analyst_login.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. View transactions ledger -> 200 OK
    resp_tx = client.get("/api/transactions?limit=5", headers=analyst_headers)
    assert resp_tx.status_code == 200

    # 2. View fraud alerts -> 200 OK
    resp_alerts = client.get("/api/alerts?limit=5", headers=analyst_headers)
    assert resp_alerts.status_code == 200

    # 3. Execute ML prediction -> 200 OK
    resp_pred = client.post(
        "/api/predict",
        headers=analyst_headers,
        json={
            "sender_upi": "arjun.sharma@okaxis",
            "receiver_upi": "merchant@icici",
            "amount": 1500.0,
            "channel": "UPI_APP",
            "device_id": "DEV-XIAOMI-12",
        },
    )
    assert resp_pred.status_code == 200


# ---------------------------------------------------------------------------
# 4. Unauthenticated Access Rejections (HTTP 401)
# ---------------------------------------------------------------------------
def test_unauthenticated_requests_rejected():
    """Verifies that protected routes reject requests without a Bearer token with HTTP 401."""
    # Transactions without auth
    resp1 = client.get("/api/transactions")
    assert resp1.status_code == 401

    # Alerts without auth
    resp2 = client.get("/api/alerts")
    assert resp2.status_code == 401

    # Analytics without auth
    resp3 = client.get("/api/analytics")
    assert resp3.status_code == 401

    # User management without auth
    resp4 = client.get("/api/users")
    assert resp4.status_code == 401

    # Predict without auth
    resp5 = client.post("/api/predict", json={})
    assert resp5.status_code == 401
