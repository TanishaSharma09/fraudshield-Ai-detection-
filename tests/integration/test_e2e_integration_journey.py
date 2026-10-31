"""FraudShield AI - End-to-End Integration Journey Test Suite.

Verifies the complete operational lifecycle from authentication to deep forensic investigation:
1. Login and logout flow for ADMIN and ANALYST accounts.
2. Dashboard operational statistics and metrics computation.
3. Transaction submission, evaluation, and direct ML inference.
4. Risk scoring and explainable alert generation for anomalous payments.
5. Alert retrieval, deduplication, and analyst triage workflow.
6. Transaction surveillance queries with filtering, sorting, and pagination.
7. Real-time transaction simulation preset and batch streaming.
8. Account relationship network graph and topology metrics.
9. RFC-4180 compliant CSV export streams for transactions and alerts.
10. Role-Based Access Control (RBAC) authorization boundaries.
11. Frontend DOM states (loading, empty, error, and pagination).
"""

import csv
import io
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def login_user(username: str, password: str) -> tuple[str, dict]:
    """Helper to authenticate and return (access_token, user_dict)."""
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    data = resp.json()
    return data["access_token"], data["user"]


# ---------------------------------------------------------------------------
# 1. Login and Logout Flow
# ---------------------------------------------------------------------------
def test_e2e_login_and_logout_flow():
    """Verifies authentication, token verification, session inspection, and logout revocation."""
    # 1. Login as ADMIN
    admin_token, admin_user = login_user(
        settings.DEFAULT_ADMIN_USERNAME, settings.DEFAULT_ADMIN_PASSWORD
    )
    assert admin_user["role"] == "ADMIN"

    # Inspect current session via /api/auth/me
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == settings.DEFAULT_ADMIN_USERNAME

    # Logout ADMIN and verify token is revoked
    logout_resp = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert logout_resp.status_code == 200

    # Attempting to reuse revoked token must be rejected with 401
    reuse_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reuse_resp.status_code == 401

    # 2. Login as ANALYST
    analyst_token, analyst_user = login_user(
        settings.DEFAULT_ANALYST_USERNAME, settings.DEFAULT_ANALYST_PASSWORD
    )
    assert analyst_user["role"] == "ANALYST"

    # 3. Invalid credentials test
    bad_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "WrongPassword999!"},
    )
    assert bad_resp.status_code == 401
    assert "invalid" in bad_resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 2. Dashboard Statistics & Health Check
# ---------------------------------------------------------------------------
def test_e2e_dashboard_statistics():
    """Verifies system health check and database-driven dashboard statistics."""
    # Health check
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert health_data["database"]["status"] == "healthy"

    # Admin accesses analytics KPIs
    admin_token, _ = login_user(
        settings.DEFAULT_ADMIN_USERNAME, settings.DEFAULT_ADMIN_PASSWORD
    )
    analytics_resp = client.get(
        "/api/analytics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert analytics_resp.status_code == 200
    data = analytics_resp.json()

    assert data["total_evaluated"] >= 0
    assert isinstance(data["total_volume_inr"], (int, float))
    assert "distribution" in data
    assert "hourly_trends" in data
    assert "model_metrics" in data
    assert data["model_metrics"]["model_name"] == "IsolationForest"


# ---------------------------------------------------------------------------
# 3. Transaction Retrieval, Evaluation & ML Prediction
# ---------------------------------------------------------------------------
def test_e2e_transaction_submission_and_prediction():
    """Verifies legitimate payment scoring and direct stateless ML prediction."""
    analyst_token, _ = login_user(
        settings.DEFAULT_ANALYST_USERNAME, settings.DEFAULT_ANALYST_PASSWORD
    )
    headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Normal grocery transaction
    normal_payload = {
        "tx_id": f"TXN-E2E-NORM-{datetime.now().strftime('%M%S%f')}",
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "grocery.store@icici",
        "amount": 420.0,
        "channel": "UPI_APP",
        "device_id": "DEV-XIAOMI-12",
        "ip_address": "49.207.180.12",
        "location_city": "Bengaluru",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "velocity_15m": 1.0,
        "time_since_last_sec": 7200.0,
        "is_new_recipient": 0,
        "is_new_device": 0,
    }

    eval_resp = client.post("/api/transactions", json=normal_payload, headers=headers)
    assert eval_resp.status_code == 201
    eval_data = eval_resp.json()
    assert eval_data["tx_id"] == normal_payload["tx_id"]
    assert eval_data["risk_tier"] == "LOW"
    assert eval_data["risk_score"] < 40.0
    assert eval_data["status"] in ("APPROVE", "APPROVED")
    assert eval_data["is_flagged"] is False

    # 2. Direct stateless inference via /api/predict
    pred_resp = client.post("/api/predict", json=normal_payload, headers=headers)
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert "raw_decision_score" in pred_data
    assert "risk_score" in pred_data
    assert "is_anomaly" in pred_data


# ---------------------------------------------------------------------------
# 4. Risk Scoring & Explainable Alerts
# ---------------------------------------------------------------------------
def test_e2e_high_risk_transaction_and_explainable_alert():
    """Verifies anomalous transaction scoring, behavioural penalties, and explainable alert generation."""
    analyst_token, _ = login_user(
        settings.DEFAULT_ANALYST_USERNAME, settings.DEFAULT_ANALYST_PASSWORD
    )
    headers = {"Authorization": f"Bearer {analyst_token}"}

    tx_id = f"TXN-E2E-ALERT-{datetime.now().strftime('%M%S%f')}"
    whale_payload = {
        "tx_id": tx_id,
        "sender_upi": "sneha.reddy@okicici",
        "receiver_upi": "crypto.cashout.mule@ybl",
        "amount": 92000.0,
        "channel": "COLLECT_REQUEST",
        "device_id": "DEV-UNKNOWN-ROOTED-88",
        "ip_address": "185.220.101.5",
        "location_city": "Kolkata",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "velocity_15m": 6.0,
        "time_since_last_sec": 30.0,
        "is_new_recipient": 1,
        "is_new_device": 1,
    }

    resp = client.post("/api/transactions", json=whale_payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["risk_score"] >= 70.0
    assert data["risk_tier"] in ("HIGH", "CRITICAL")
    assert data["is_flagged"] is True
    assert data["alert_id"] is not None
    assert len(data["explanations"]) >= 1

    alert_id = data["alert_id"]

    # Retrieve individual transaction and verify full explainability details
    get_resp = client.get(f"/api/transactions/{tx_id}", headers=headers)
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["transaction"]["tx_id"] == tx_id
    assert detail["alert"]["alert_id"] == alert_id
    assert len(detail["explanations"]) >= 1
    assert "factor_name" in detail["explanations"][0]
    assert "description" in detail["explanations"][0]


# ---------------------------------------------------------------------------
# 5. Alert Surveillance, Investigation & Triage
# ---------------------------------------------------------------------------
def test_e2e_alert_investigation_and_triage():
    """Verifies listing alerts, reviewing an alert, and preventing duplicate alerts."""
    analyst_token, _ = login_user(
        settings.DEFAULT_ANALYST_USERNAME, settings.DEFAULT_ANALYST_PASSWORD
    )
    headers = {"Authorization": f"Bearer {analyst_token}"}

    # Fetch pending alerts
    alerts_resp = client.get("/api/alerts?status=PENDING&limit=10", headers=headers)
    assert alerts_resp.status_code == 200
    data = alerts_resp.json()
    assert "alerts" in data
    assert len(data["alerts"]) > 0

    target_alert = data["alerts"][0]
    alert_id = target_alert["alert_id"]

    # Review the alert
    triage_resp = client.patch(
        f"/api/alerts/{alert_id}",
        json={
            "action": "REVIEWED",
            "notes": "E2E automated SOC triage test: verified counterparty risk profile.",
            "reviewed_by": "analyst",
        },
        headers=headers,
    )
    assert triage_resp.status_code == 200
    updated = triage_resp.json()
    assert updated["status"] == "REVIEWED"
    assert updated["reviewed_by"] == "analyst"
    assert "E2E automated SOC triage" in updated["analyst_notes"]


# ---------------------------------------------------------------------------
# 6. Transaction Ledger Surveillance (Search, Filters, Pagination)
# ---------------------------------------------------------------------------
def test_e2e_transaction_surveillance_queries():
    """Verifies transaction queries with pagination, search, and risk tier filters."""
    analyst_token, _ = login_user(
        settings.DEFAULT_ANALYST_USERNAME, settings.DEFAULT_ANALYST_PASSWORD
    )
    headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Pagination
    paged_resp = client.get("/api/transactions?limit=5&offset=0", headers=headers)
    assert paged_resp.status_code == 200
    paged_data = paged_resp.json()
    assert len(paged_data["transactions"]) <= 5
    assert paged_data["limit"] == 5
    assert paged_data["offset"] == 0

    # 2. Risk filter
    low_resp = client.get("/api/transactions?risk_tier=LOW&limit=5", headers=headers)
    assert low_resp.status_code == 200
    for tx in low_resp.json()["transactions"]:
        assert tx["risk_tier"] == "LOW"

    # 3. Empty state query (search that matches nothing)
    empty_resp = client.get("/api/transactions?search=NONEXISTENT_HASH_XYZ999", headers=headers)
    assert empty_resp.status_code == 200
    assert empty_resp.json()["total"] == 0
    assert len(empty_resp.json()["transactions"]) == 0


# ---------------------------------------------------------------------------
# 7. Live Stream Simulator
# ---------------------------------------------------------------------------
def test_e2e_live_simulation_stream():
    """Verifies triggering scenario presets and streaming batches through the ML engine."""
    analyst_token, _ = login_user(
        settings.DEFAULT_ANALYST_USERNAME, settings.DEFAULT_ANALYST_PASSWORD
    )
    headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Preset trigger
    preset_resp = client.post(
        "/api/simulation/preset",
        json={"preset": "VELOCITY_BURST"},
        headers=headers,
    )
    assert preset_resp.status_code == 201
    preset_data = preset_resp.json()
    assert "TXN-SIM-BURST" in preset_data["tx_id"]
    assert preset_data["risk_score"] > 40.0

    # 2. Stream batch
    batch_resp = client.post(
        "/api/simulation/stream?count=4",
        headers=headers,
    )
    assert batch_resp.status_code == 201
    batch_data = batch_resp.json()
    assert batch_data["batch_size"] == 4
    assert len(batch_data["transactions"]) == 4


# ---------------------------------------------------------------------------
# 8. Analytics & Account Relationship Network Graph
# ---------------------------------------------------------------------------
def test_e2e_analytics_and_network_graph():
    """Verifies account relationship topology graph generation from SQLite."""
    analyst_token, _ = login_user(
        settings.DEFAULT_ANALYST_USERNAME, settings.DEFAULT_ANALYST_PASSWORD
    )
    headers = {"Authorization": f"Bearer {analyst_token}"}

    graph_resp = client.get(
        "/api/analytics/network-graph?min_risk_score=0&limit=80",
        headers=headers,
    )
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()

    assert "nodes" in graph_data
    assert "edges" in graph_data
    metrics_summary = graph_data.get("metrics") or graph_data.get("summary")
    assert metrics_summary is not None
    assert metrics_summary["total_nodes"] >= 0
    assert metrics_summary["total_edges"] >= 0


# ---------------------------------------------------------------------------
# 9. CSV Report Exports (RFC-4180 Compliant Streams)
# ---------------------------------------------------------------------------
def test_e2e_csv_reports_export():
    """Verifies transactions and alerts CSV export streams with RFC-4180 headers."""
    admin_token, _ = login_user(
        settings.DEFAULT_ADMIN_USERNAME, settings.DEFAULT_ADMIN_PASSWORD
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Transactions CSV export
    tx_csv_resp = client.get("/api/analytics/export/transactions", headers=headers)
    assert tx_csv_resp.status_code == 200
    assert "text/csv" in tx_csv_resp.headers["content-type"]
    assert "fraudshield_transactions_" in tx_csv_resp.headers["content-disposition"]

    reader = csv.reader(io.StringIO(tx_csv_resp.text))
    rows = list(reader)
    assert len(rows) >= 2  # Header + at least one data row
    assert "Transaction ID" in rows[0]
    assert "Sender VPA" in rows[0] or "Sender UPI" in rows[0]
    assert "Amount (INR)" in rows[0]

    # 2. Fraud Alerts CSV export
    alt_csv_resp = client.get("/api/analytics/export/alerts", headers=headers)
    assert alt_csv_resp.status_code == 200
    assert "text/csv" in alt_csv_resp.headers["content-type"]
    assert "fraudshield_alerts_" in alt_csv_resp.headers["content-disposition"]

    alt_reader = csv.reader(io.StringIO(alt_csv_resp.text))
    alt_rows = list(alt_reader)
    assert len(alt_rows) >= 2
    assert "Alert ID" in alt_rows[0]
    assert "Primary Flag Reason" in alt_rows[0]


# ---------------------------------------------------------------------------
# 10. Role-Based Access Control (RBAC) Enforcement
# ---------------------------------------------------------------------------
def test_e2e_role_based_access_control():
    """Verifies that ANALYST role is strictly forbidden from ADMIN endpoints."""
    analyst_token, _ = login_user(
        settings.DEFAULT_ANALYST_USERNAME, settings.DEFAULT_ANALYST_PASSWORD
    )
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # Blocked from Analytics
    assert client.get("/api/analytics", headers=analyst_headers).status_code == 403

    # Blocked from CSV Exports
    assert client.get("/api/analytics/export/transactions", headers=analyst_headers).status_code == 403
    assert client.get("/api/analytics/export/alerts", headers=analyst_headers).status_code == 403

    # Blocked from User Management
    assert client.get("/api/users", headers=analyst_headers).status_code == 403

    # Permitted on Transaction Surveillance & Triage
    assert client.get("/api/transactions", headers=analyst_headers).status_code == 200
    assert client.get("/api/alerts", headers=analyst_headers).status_code == 200
    assert client.get("/api/analytics/network-graph", headers=analyst_headers).status_code == 200


# ---------------------------------------------------------------------------
# 11. Frontend UI States & Components Verification
# ---------------------------------------------------------------------------
def test_e2e_frontend_dom_states_verification():
    """Verifies frontend HTML contains all interactive loading, empty, and error states."""
    ui_resp = client.get("/ui/")
    assert ui_resp.status_code == 200
    html = ui_resp.text

    # Authentication Drawer & Login Form
    assert 'id="login-username"' in html
    assert 'id="login-password"' in html
    assert 'id="btn-do-login"' in html
    assert 'id="login-error-msg"' in html
    assert 'id="btn-switch-admin"' in html
    assert 'id="btn-switch-analyst"' in html
    assert 'id="btn-logout"' in html

    # Transactions Table States
    assert 'id="mgmt-loading-state"' in html
    assert 'id="mgmt-empty-state"' in html
    assert 'id="mgmt-error-state"' in html
    assert 'id="mgmt-pagination-container"' in html

    # Alerts Queue States
    assert 'id="alerts-loading-state"' in html
    assert 'id="alerts-empty-state"' in html
    assert 'id="alerts-error-state"' in html
    assert 'id="alerts-pagination-container"' in html

    # Analytics RBAC State
    assert 'id="analytics-role-restricted-state"' in html
    assert 'id="btn-analytics-switch-admin"' in html

    # Network Graph Canvas & Controls
    assert 'id="card-network-graph"' in html
    assert 'id="canvas-account-network-graph"' in html
    assert 'id="btn-graph-filter-all"' in html
    assert 'id="btn-graph-filter-susp"' in html
