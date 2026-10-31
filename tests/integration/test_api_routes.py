"""FraudShield AI - Integration Test Suite for REST API Gateway.

Validates all required endpoints:
1. GET /health
2. POST /api/transactions (and validation handling)
3. POST /api/predict (ML inference with explainability)
4. GET /api/transactions (pagination, filters)
5. GET /api/transactions/{transaction_id} (detail & 404)
6. GET /api/alerts (filters, pagination, triage)
7. GET /api/analytics (KPIs, distribution, trends)
8. POST /api/simulation/preset & stream
9. Swagger UI docs (/docs & /openapi.json)
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.security import create_access_token

# Configure test client with valid ADMIN Bearer token for protected routes
admin_token = create_access_token({"sub": "1", "username": "admin", "role": "ADMIN"})
client = TestClient(app, headers={"Authorization": f"Bearer {admin_token}"})


# ---------------------------------------------------------------------------
# 1. Health Endpoint Tests
# ---------------------------------------------------------------------------
def test_get_health():
    """Verifies that /health returns 200 with operational database and loaded ML model."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["project"] == "FraudShield AI"
    assert data["database"]["status"] == "healthy"
    assert data["database"]["baseline_users_loaded"] >= 5
    assert data["ml_capabilities"]["status"] == "healthy"
    assert data["subsystems"]["ml_engine"]["status"] == "loaded"


# ---------------------------------------------------------------------------
# 2. POST /api/transactions Tests
# ---------------------------------------------------------------------------
def test_post_transactions_normal():
    """Verifies successful submission and evaluation of a normal legitimate transaction."""
    payload = {
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "kirana.store@icici",
        "amount": 350.0,
        "channel": "QR_CODE",
        "device_id": "DEV-XIAOMI-12",
        "ip_address": "49.207.180.12",
        "location_city": "Mumbai",
    }
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "tx_id" in data
    assert data["sender_upi"] == "arjun.sharma@okaxis"
    assert data["amount"] == 350.0
    assert 0.0 <= data["risk_score"] <= 100.0
    assert data["risk_tier"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert data["action_recommendation"] in ["APPROVE", "STEP_UP_AUTHENTICATION", "HOLD_FOR_REVIEW"]
    assert isinstance(data["explanations"], list)
    assert len(data["explanations"]) >= 1


def test_post_transactions_suspicious_high_risk():
    """Verifies that a compound attack pattern triggers elevated risk and creates an alert."""
    payload = {
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "unverified.scam.wallet@paytm",
        "amount": 95000.0,
        "channel": "COLLECT_REQUEST",
        "device_id": "DEV-UNKNOWN-EMULATOR",
        "ip_address": "185.220.101.5",
        "location_city": "Moscow",
        "velocity_15m": 6.0,
        "time_since_last_sec": 10.0,
        "is_new_recipient": 1,
        "is_new_device": 1,
    }
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["risk_score"] >= 70.0
    assert data["risk_tier"] == "HIGH"
    assert data["is_flagged"] is True
    assert data["action_recommendation"] == "HOLD_FOR_REVIEW"
    assert data["alert_id"] is not None
    assert data["alert_id"].startswith("ALT-")


def test_post_transactions_invalid_upi():
    """Verifies 422 Unprocessable Entity when VPA format is invalid."""
    payload = {
        "sender_upi": "invalid_upi_without_at_symbol",
        "receiver_upi": "receiver@icici",
        "amount": 1000.0,
        "channel": "UPI_APP",
        "device_id": "DEV-XIAOMI-12",
    }
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data or "detail" in data


def test_post_transactions_invalid_amount():
    """Verifies 422 Unprocessable Entity when amount is zero or negative."""
    payload = {
        "sender_upi": "valid.user@okaxis",
        "receiver_upi": "receiver@icici",
        "amount": -50.0,
        "channel": "UPI_APP",
        "device_id": "DEV-XIAOMI-12",
    }
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 3. POST /api/predict Tests
# ---------------------------------------------------------------------------
def test_post_predict_direct_inference():
    """Verifies direct machine learning inference via POST /api/predict."""
    payload = {
        "sender_upi": "vikram.malhotra@okhdfcbank",
        "receiver_upi": "merchant.jewels@hdfcbank",
        "amount": 25000.0,
        "channel": "UPI_APP",
        "device_id": "DEV-IPHONE-15PRO",
        "ip_address": "157.34.120.45",
        "location_city": "Mumbai",
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "transaction_id" in data
    assert isinstance(data["is_anomaly"], bool)
    assert data["prediction_label"] in ["SUSPICIOUS_ANOMALY", "NORMAL"]
    assert isinstance(data["raw_decision_score"], float)
    assert 0.0 <= data["risk_score"] <= 100.0
    assert data["risk_category"] in ["Low risk", "Medium risk", "High risk"]
    assert len(data["explanations"]) >= 1
    assert data["model_version"].startswith("IsolationForest")


# ---------------------------------------------------------------------------
# 4. GET /api/transactions Tests
# ---------------------------------------------------------------------------
def test_get_transactions_list():
    """Verifies retrieving paginated transactions list."""
    response = client.get("/api/transactions?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "transactions" in data
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert isinstance(data["transactions"], list)
    assert len(data["transactions"]) >= 1


def test_get_transactions_filtering():
    """Verifies filtering transactions by risk tier and sender UPI."""
    response = client.get("/api/transactions?risk_tier=HIGH")
    assert response.status_code == 200
    data = response.json()
    for tx in data["transactions"]:
        assert tx["risk_tier"] == "HIGH"


# ---------------------------------------------------------------------------
# 5. GET /api/transactions/{transaction_id} Tests
# ---------------------------------------------------------------------------
def test_get_transaction_by_id():
    """Submits a transaction and retrieves it by transaction_id."""
    # First submit a transaction
    post_resp = client.post(
        "/api/transactions",
        json={
            "sender_upi": "arjun.sharma@okaxis",
            "receiver_upi": "cafe.coffee@icici",
            "amount": 220.0,
            "channel": "QR_CODE",
            "device_id": "DEV-XIAOMI-12",
        },
    )
    tx_id = post_resp.json()["tx_id"]

    # Now retrieve it
    get_resp = client.get(f"/api/transactions/{tx_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["transaction"]["tx_id"] == tx_id
    assert detail["transaction"]["amount"] == 220.0


def test_get_transaction_by_id_not_found():
    """Verifies 404 response when transaction ID does not exist."""
    response = client.get("/api/transactions/NON_EXISTENT_TX_999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. GET & PATCH /api/alerts Tests
# ---------------------------------------------------------------------------
def test_get_alerts_list():
    """Verifies fetching alerts list from the database."""
    response = client.get("/api/alerts?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "alerts" in data
    assert isinstance(data["alerts"], list)


def test_alert_triage_flow():
    """Generates an alert via a high-risk transaction, retrieves it, and performs SOC action."""
    # 1. Trigger high-risk transaction to create an alert
    post_resp = client.post(
        "/api/transactions",
        json={
            "sender_upi": "sneha.reddy@okicici",
            "receiver_upi": "cashout.drain@ybl",
            "amount": 92000.0,
            "channel": "COLLECT_REQUEST",
            "device_id": "DEV-EMULATOR-ROOT",
            "velocity_15m": 5.0,
            "time_since_last_sec": 20.0,
            "is_new_recipient": 1,
            "is_new_device": 1,
        },
    )
    alert_id = post_resp.json().get("alert_id")
    assert alert_id is not None

    # 2. Retrieve alert details
    get_alert_resp = client.get(f"/api/alerts/{alert_id}")
    assert get_alert_resp.status_code == 200
    alert_data = get_alert_resp.json()
    assert alert_data["alert_id"] == alert_id
    assert alert_data["status"] == "PENDING"

    # 3. Perform SOC action: BLOCK
    patch_resp = client.patch(
        f"/api/alerts/{alert_id}",
        json={
            "action": "BLOCK",
            "notes": "Confirmed unauthorized SIM-swap account takeover. Blocked beneficiary VPA.",
            "reviewed_by": "SOC-Lead-Analyst",
        },
    )
    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()
    assert updated_data["status"] == "BLOCK"
    assert updated_data["reviewed_by"] == "SOC-Lead-Analyst"
    assert "SIM-swap" in updated_data["analyst_notes"]


def test_alert_not_found():
    """Verifies 404 response for non-existent alert ID."""
    response = client.get("/api/alerts/ALT-NON-EXISTENT-999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 7. GET /api/analytics Tests
# ---------------------------------------------------------------------------
def test_get_analytics_overview():
    """Verifies analytics metrics, risk distribution, hourly trends, and top vectors."""
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "total_evaluated" in data
    assert "total_flagged" in data
    assert "fraud_rate_percentage" in data
    assert "avg_risk_score" in data
    assert "pending_alerts" in data
    assert "distribution" in data
    assert "low" in data["distribution"]
    assert "medium" in data["distribution"]
    assert "high" in data["distribution"]
    assert "critical" in data["distribution"]
    assert "hourly_trends" in data
    assert len(data["hourly_trends"]) == 24
    assert "top_vectors" in data
    assert "active_model_version" in data


# ---------------------------------------------------------------------------
# 8. Simulation Endpoints Tests
# ---------------------------------------------------------------------------
def test_simulation_preset_trigger():
    """Verifies triggering all 5 primary simulation presets."""
    scenarios = [
        ("NORMAL_PAYMENT", "LOW", False),
        ("UNUSUALLY_LARGE", "HIGH", True),
        ("VELOCITY_BURST", "HIGH", True),
        ("NEW_RECIPIENT", "MEDIUM", False),
        ("UNUSUAL_PATTERN", "CRITICAL", True),
    ]
    for preset_name, expected_tier, expected_flag in scenarios:
        response = client.post("/api/simulation/preset", json={"preset": preset_name})
        assert response.status_code == 201, f"Failed for {preset_name}: {response.text}"
        data = response.json()
        assert "tx_id" in data
        assert data["tx_id"].startswith("TXN-SIM-")
        assert "risk_score" in data
        assert "explanations" in data
        assert len(data["explanations"]) >= 1
        if expected_flag:
            assert data["is_flagged"] is True


def test_simulation_stream_batch():
    """Verifies streaming a batch of simulated transactions."""
    response = client.post("/api/simulation/stream?count=5")
    assert response.status_code == 201
    data = response.json()
    assert data["batch_size"] == 5
    assert data["evaluated_count"] == 5
    assert len(data["transactions"]) == 5


# ---------------------------------------------------------------------------
# 9. Documentation and Discovery Tests
# ---------------------------------------------------------------------------
def test_swagger_docs_and_openapi():
    """Verifies OpenAPI schema and Swagger UI documentation endpoints."""
    # Root
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert root_resp.json()["docs_url"] == "/docs"

    # OpenAPI JSON schema
    schema_resp = client.get("/openapi.json")
    assert schema_resp.status_code == 200
    schema = schema_resp.json()
    assert "openapi" in schema
    assert "/api/transactions" in schema["paths"]
    assert "/api/predict" in schema["paths"]
    assert "/api/alerts" in schema["paths"]
    assert "/api/analytics" in schema["paths"]
    assert "/health" in schema["paths"]

    # Swagger UI
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200


def test_transactions_search_and_sorting():
    """Verifies search, date filtering, and column sorting on GET /api/transactions."""
    # Test search by VPA
    res_search = client.get("/api/transactions?search=okaxis")
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert "transactions" in data_search
    for tx in data_search["transactions"]:
        assert "okaxis" in tx["sender_upi"].lower() or "okaxis" in tx["receiver_upi"].lower() or "okaxis" in tx["tx_id"].lower() or "okaxis" in tx["location_city"].lower()

    # Test sorting by amount desc
    res_sort = client.get("/api/transactions?sort_by=amount&sort_order=desc&limit=10")
    assert res_sort.status_code == 200
    txs = res_sort.json()["transactions"]
    if len(txs) >= 2:
        assert txs[0]["amount"] >= txs[1]["amount"]

    # Test sorting by risk_score asc
    res_score_asc = client.get("/api/transactions?sort_by=risk_score&sort_order=asc&limit=10")
    assert res_score_asc.status_code == 200
    txs_score = res_score_asc.json()["transactions"]
    if len(txs_score) >= 2:
        assert txs_score[0]["risk_score"] <= txs_score[1]["risk_score"]
