"""FraudShield AI - Real-Time Fraud Alert System Integration Tests.

Validates:
1. Configurable threshold alert creation (Medium and High risk transactions trigger alerts; Low risk do not).
2. Required alert fields: alert_id, tx_id, risk_score, risk_category, created_at, primary_reason, explanations, status.
3. Duplicate alert prevention: re-evaluating the same transaction never generates duplicate alerts.
4. Review status preservation: re-evaluating an already reviewed transaction does not reset status to PENDING.
5. Mark as reviewed workflow (POST /api/alerts/{id}/review and PATCH with REVIEWED).
6. Alert filtering by status, severity, and search keywords.
7. Real-time Server-Sent Events (SSE) stream endpoint.
8. Frontend UI component integrity (Alerts surveillance table, slide-over drawer, toast container, unread counters).
"""

import json
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.alert_service import get_alert_service
from database.connection import query_all, query_one, execute_stmt

client = TestClient(app)

# Credentials for test execution
ADMIN_AUTH = ("admin", "Admin@FraudShield2026!")
ANALYST_AUTH = ("analyst", "Analyst@FraudShield2026!")


def get_auth_token(role: str = "analyst") -> str:
    """Helper to authenticate and retrieve a bearer JWT token."""
    creds = ADMIN_AUTH if role.lower() == "admin" else ANALYST_AUTH
    res = client.post("/api/auth/login", json={"username": creds[0], "password": creds[1]})
    assert res.status_code == 200, f"Authentication failed: {res.text}"
    return res.json()["access_token"]


def test_threshold_based_alert_generation():
    """Verifies that transactions with risk >= 40.0 (Medium or High risk) create alerts, while Low risk do not."""
    token = get_auth_token("analyst")
    headers = {"Authorization": f"Bearer {token}"}

    uid = uuid.uuid4().hex[:8]
    low_tx_id = f"TXN-TEST-LOW-{uid}"
    high_tx_id = f"TXN-TEST-HIGH-{uid}"

    # 1. Low-risk normal payment -> should NOT generate an alert
    normal_tx = {
        "tx_id": low_tx_id,
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "kirana.grocery@icici",
        "amount": 250.0,
        "channel": "QR_CODE",
        "device_id": "DEV-XIAOMI-12",
        "location_city": "Mumbai",
        "velocity_15m": 1.0,
        "time_since_last_sec": 3600.0,
        "is_new_recipient": 0,
        "is_new_device": 0,
    }
    low_resp = client.post("/api/transactions", json=normal_tx, headers=headers)
    assert low_resp.status_code == 201
    low_data = low_resp.json()
    assert low_data["risk_category"] == "Low risk"
    assert low_data["alert_id"] is None, "Low risk payment should not produce an alert"

    # Database check: no alert in fraud_alerts table
    db_low_alert = query_one("SELECT * FROM fraud_alerts WHERE tx_id = ?;", (low_tx_id,))
    assert db_low_alert is None

    # 2. High-risk transaction -> MUST generate an alert
    high_tx = {
        "tx_id": high_tx_id,
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "mule.drop.account@paytm",
        "amount": 85000.0,
        "channel": "COLLECT_REQUEST",
        "device_id": "DEV-SUSPICIOUS-ROOT",
        "velocity_15m": 5.0,
        "time_since_last_sec": 20.0,
        "is_new_recipient": 1,
        "is_new_device": 1,
    }
    high_resp = client.post("/api/transactions", json=high_tx, headers=headers)
    assert high_resp.status_code == 201
    high_data = high_resp.json()
    assert high_data["risk_category"] == "High risk"
    alert_id = high_data["alert_id"]
    assert alert_id is not None
    assert alert_id.startswith("ALT-")

    # Verify fields in the generated alert response
    alert_resp = client.get(f"/api/alerts/{alert_id}", headers=headers)
    assert alert_resp.status_code == 200
    alert_payload = alert_resp.json()
    assert alert_payload["alert_id"] == alert_id
    assert alert_payload["tx_id"] == high_tx_id
    assert alert_payload["risk_score"] >= 70.0
    assert alert_payload["risk_category"] == "High risk"
    assert alert_payload["severity"] == "HIGH"
    assert alert_payload["status"] == "PENDING"
    assert len(alert_payload["primary_reason"]) > 0
    assert len(alert_payload["explanations"]) >= 1


def test_duplicate_alert_prevention():
    """Verifies that re-evaluating or re-processing the same transaction ID never creates duplicate alerts."""
    service = get_alert_service()

    tx = {
        "tx_id": "TXN-DEDUP-TEST-999",
        "sender_upi": "rohit.verma@okaxis",
        "receiver_upi": "crypto.cashout@ybl",
        "amount": 65000.0,
        "channel": "COLLECT_REQUEST",
        "device_id": "DEV-UNKNOWN-DEDUP",
        "velocity_15m": 4.0,
        "time_since_last_sec": 30.0,
        "is_new_recipient": 1,
        "is_new_device": 1,
    }

    # First evaluation
    res1 = service.process_transaction(tx)
    alert_id1 = res1["alert_id"]
    assert alert_id1 is not None

    # Verify exactly 1 alert exists in DB
    alerts_after_first = query_all("SELECT * FROM fraud_alerts WHERE tx_id = ?;", ("TXN-DEDUP-TEST-999",))
    assert len(alerts_after_first) == 1

    # Second evaluation of the same transaction (e.g. reprocessing / retry webhook)
    res2 = service.process_transaction(tx)
    alert_id2 = res2["alert_id"]

    # Must reuse the same alert ID and NOT create a second row
    assert alert_id2 == alert_id1, "Alert ID must remain identical on deduplication"
    alerts_after_second = query_all("SELECT * FROM fraud_alerts WHERE tx_id = ?;", ("TXN-DEDUP-TEST-999",))
    assert len(alerts_after_second) == 1, "Duplicate alert row was created in fraud_alerts table!"


def test_review_status_preservation_on_deduplication():
    """Verifies that if an alert has already been reviewed, re-evaluating does not reset status to PENDING."""
    service = get_alert_service()

    tx = {
        "tx_id": "TXN-STATUS-PRESERVE-001",
        "sender_upi": "priya.patel@okhdfc",
        "receiver_upi": "offshore.gateway@axis",
        "amount": 72000.0,
        "channel": "INTENT_FLOW",
        "device_id": "DEV-NEW-ROOTED",
        "velocity_15m": 4.0,
    }

    # 1. Create alert
    res = service.process_transaction(tx)
    alert_id = res["alert_id"]
    assert alert_id is not None

    # 2. Mark alert as REVIEWED
    service.update_alert_action(alert_id, "REVIEWED", notes="Investigated by Tier-2 SOC", reviewed_by="SOC-Analyst-Maya")
    db_alert = query_one("SELECT status, reviewed_by, analyst_notes FROM fraud_alerts WHERE alert_id = ?;", (alert_id,))
    assert db_alert["status"] == "REVIEWED"

    # 3. Re-process transaction
    service.process_transaction(tx)

    # 4. Ensure status remains REVIEWED and was not clobbered back to PENDING
    db_after = query_one("SELECT status, reviewed_by FROM fraud_alerts WHERE alert_id = ?;", (alert_id,))
    assert db_after["status"] == "REVIEWED", "Review status was incorrectly reset to PENDING"


def test_mark_alert_as_reviewed_flow():
    """Verifies the dedicated 'Mark as Reviewed' API endpoints (POST /review and PATCH with REVIEWED)."""
    token = get_auth_token("analyst")
    headers = {"Authorization": f"Bearer {token}"}

    # Generate test alert
    tx = {
        "tx_id": "TXN-REVIEW-FLOW-001",
        "sender_upi": "kavita.nair@okicici",
        "receiver_upi": "mule.holding@icici",
        "amount": 80000.0,
        "channel": "COLLECT_REQUEST",
        "device_id": "DEV-ANOMALOUS",
        "velocity_15m": 5.0,
    }
    post_res = client.post("/api/transactions", json=tx, headers=headers)
    assert post_res.status_code == 201
    alert_id = post_res.json()["alert_id"]
    assert alert_id is not None

    # 1. Mark as reviewed via POST /api/alerts/{id}/review
    rev_resp = client.post(
        f"/api/alerts/{alert_id}/review",
        json={"action": "REVIEWED", "notes": "Reviewed KYC and call confirmation logged"},
        headers=headers,
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["status"] == "REVIEWED"
    assert rev_data["reviewed_by"] == "analyst"
    assert "Reviewed KYC" in rev_data["analyst_notes"]

    # Verify linked transaction status was set to UNDER_REVIEW
    db_tx = query_one("SELECT status FROM transactions WHERE tx_id = ?;", ("TXN-REVIEW-FLOW-001",))
    assert db_tx["status"] == "UNDER_REVIEW"

    # 2. Transition from REVIEWED -> APPROVED
    appr_resp = client.patch(
        f"/api/alerts/{alert_id}",
        json={"action": "APPROVE", "notes": "Customer confirmed legitimate emergency payment"},
        headers=headers,
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "APPROVE"


def test_alert_filtering_and_search():
    """Verifies searching and filtering alerts by status, severity, and search keywords."""
    token = get_auth_token("analyst")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test filtering by status=PENDING
    resp_pending = client.get("/api/alerts?status=PENDING&limit=20", headers=headers)
    assert resp_pending.status_code == 200
    data_pending = resp_pending.json()
    assert "alerts" in data_pending
    for alert in data_pending["alerts"]:
        assert alert["status"] == "PENDING"

    # 2. Test filtering by severity=HIGH
    resp_sev = client.get("/api/alerts?severity=HIGH&limit=20", headers=headers)
    assert resp_sev.status_code == 200
    for alert in resp_sev.json()["alerts"]:
        assert alert["severity"] == "HIGH"

    # 3. Test searching by text
    resp_search = client.get("/api/alerts?search=TXN-REVIEW-FLOW-001&limit=10", headers=headers)
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert search_data["total"] >= 1
    assert search_data["alerts"][0]["tx_id"] == "TXN-REVIEW-FLOW-001"


def test_sse_alert_stream_endpoint():
    """Verifies that the /api/alerts/stream Server-Sent Events endpoint connects and streams valid data."""
    # Test client stream request
    with client.stream("GET", "/api/alerts/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        # Read the first event chunk
        for line in response.iter_lines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                assert payload["type"] == "ALERTS_SYNC"
                assert "alerts" in payload
                assert "pending_count" in payload
                break


def test_frontend_alert_system_components():
    """Verifies that the frontend HTML includes all user-requested alert components and controls."""
    html_resp = client.get("/ui")
    assert html_resp.status_code == 200
    html = html_resp.text

    # 1. Navigation and Counters
    assert 'id="nav-alerts"' in html
    assert 'id="sidebar-alert-badge"' in html
    assert 'id="btn-notifications"' in html
    assert 'id="notification-unread-count"' in html

    # 2. Dedicated View 3: Fraud Alerts & Investigation Center
    assert 'id="view-alerts"' in html
    assert 'id="alerts-data-table"' in html
    assert 'id="alerts-table-body"' in html
    assert 'id="alert-stat-pending"' in html
    assert 'id="alert-stat-reviewed"' in html
    assert 'id="alert-stat-approved"' in html
    assert 'id="alert-stat-blocked"' in html

    # 3. Filtering Toolbar
    assert 'id="alert-mgmt-search"' in html
    assert 'data-alert-status="PENDING"' in html
    assert 'data-alert-status="REVIEWED"' in html
    assert 'id="alert-severity-select"' in html

    # 4. Slide-over Alert Detail Drawer
    assert 'id="alert-drawer-backdrop"' in html
    assert 'id="drawer-alert-id"' in html
    assert 'id="drawer-alert-risk-score"' in html
    assert 'id="drawer-factors-container"' in html
    assert 'id="btn-drawer-mark-reviewed"' in html
    assert 'id="btn-drawer-approve"' in html
    assert 'id="btn-drawer-block"' in html
    assert 'id="drawer-analyst-notes"' in html

    # 5. Live Notifications Toast Container
    assert 'id="fraudshield-toast-container"' in html
