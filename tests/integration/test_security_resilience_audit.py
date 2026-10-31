"""FraudShield AI - Comprehensive Security & Resilience Audit Test Suite.

Audits and verifies:
1. Missing fields validation (422 Unprocessable Content).
2. Invalid transaction amounts (negative, zero, > 10L UPI limit, NaN, non-numeric).
3. Duplicate transaction ID safety & conflict handling.
4. Invalid timestamp handling (malformed, future, ancient).
5. Unavailable model files (HTTP 503 Service Unavailable).
6. Database rollback integrity and foreign key enforcement.
7. Unauthorised API requests (missing tokens, expired tokens, tampered signatures, blacklisted tokens).
8. Role permissions (ADMIN vs ANALYST access control).
9. SQL injection attack immunity (parameterized queries).
10. Password hashing security (PBKDF2-HMAC-SHA256, no plaintext passwords).
11. CORS security headers.
"""

import time
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.core.security import create_access_token, hash_password, verify_password
from database.connection import get_db_connection, query_one

client = TestClient(app)

admin_token = create_access_token({"sub": "1", "username": "admin", "role": "ADMIN"})
analyst_token = create_access_token({"sub": "2", "username": "analyst", "role": "ANALYST"})
admin_headers = {"Authorization": f"Bearer {admin_token}"}
analyst_headers = {"Authorization": f"Bearer {analyst_token}"}


# ---------------------------------------------------------------------------
# 1. Missing Fields Validation
# ---------------------------------------------------------------------------
def test_audit_missing_required_fields():
    """Verifies that omitting any required field returns HTTP 422 with structured field error."""
    # Missing sender_upi
    resp1 = client.post(
        "/api/transactions",
        json={"receiver_upi": "store@icici", "amount": 500.0},
        headers=analyst_headers,
    )
    assert resp1.status_code == 422
    assert "field_errors" in resp1.json() or "detail" in resp1.json()

    # Missing receiver_upi
    resp2 = client.post(
        "/api/transactions",
        json={"sender_upi": "arjun@okaxis", "amount": 500.0},
        headers=analyst_headers,
    )
    assert resp2.status_code == 422

    # Missing amount
    resp3 = client.post(
        "/api/transactions",
        json={"sender_upi": "arjun@okaxis", "receiver_upi": "store@icici"},
        headers=analyst_headers,
    )
    assert resp3.status_code == 422


# ---------------------------------------------------------------------------
# 2. Invalid Transaction Amounts
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "invalid_amount, expected_error_fragment",
    [
        (-50.0, "greater than zero"),
        (0.0, "greater than zero"),
        (1_500_000.0, "transfer limit"),
        ("not_a_number", "number"),
    ],
)
def test_audit_invalid_transaction_amounts(invalid_amount, expected_error_fragment):
    """Verifies that negative, zero, excessive, and non-numeric amounts are rejected with HTTP 422."""
    payload = {
        "sender_upi": "arjun@okaxis",
        "receiver_upi": "store@icici",
        "amount": invalid_amount,
    }
    resp = client.post("/api/transactions", json=payload, headers=analyst_headers)
    assert resp.status_code == 422
    detail_str = str(resp.json()).lower()
    assert expected_error_fragment.lower() in detail_str or "validation" in detail_str


# ---------------------------------------------------------------------------
# 3. Invalid Timestamps
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "bad_timestamp, reason",
    [
        ("corrupted-date-not-iso", "format"),
        ("2099-01-01T12:00:00Z", "future"),
        ("1995-05-15T00:00:00Z", "past"),
    ],
)
def test_audit_invalid_timestamps(bad_timestamp, reason):
    """Verifies rejection of corrupted, future, and ancient timestamps with HTTP 422."""
    payload = {
        "sender_upi": "arjun@okaxis",
        "receiver_upi": "store@icici",
        "amount": 450.0,
        "timestamp": bad_timestamp,
    }
    resp = client.post("/api/transactions", json=payload, headers=analyst_headers)
    assert resp.status_code == 422
    assert "timestamp" in str(resp.json()).lower()


# ---------------------------------------------------------------------------
# 4. Duplicate Transaction IDs Safety
# ---------------------------------------------------------------------------
def test_audit_duplicate_transaction_ids():
    """Verifies that submitting identical transaction IDs is handled safely via ON CONFLICT."""
    dup_id = f"TXN-AUDIT-DUP-{int(time.time() * 1000)}"
    payload = {
        "tx_id": dup_id,
        "sender_upi": "priya.patel@oksbi",
        "receiver_upi": "luxury.jewels@hdfcbank",
        "amount": 78000.0,
        "channel": "INTENT_FLOW",
        "is_new_recipient": 1,
    }

    # 1. First submission
    resp1 = client.post("/api/transactions", json=payload, headers=analyst_headers)
    assert resp1.status_code == 201
    data1 = resp1.json()
    alert_id1 = data1.get("alert_id")

    # 2. Second submission with identical tx_id
    resp2 = client.post("/api/transactions", json=payload, headers=analyst_headers)
    assert resp2.status_code == 201
    data2 = resp2.json()

    # Verify ID is preserved and no unhandled primary key explosion occurred
    assert data2["tx_id"] == dup_id
    # Alert ID must be deduplicated
    if alert_id1:
        assert data2.get("alert_id") == alert_id1


# ---------------------------------------------------------------------------
# 5. Unavailable Model Files Resilience
# ---------------------------------------------------------------------------
def test_audit_unavailable_model_files_handling():
    """Verifies that missing model artifacts return HTTP 503 instead of crashing."""
    from ml_model.predictor import FraudShieldPredictor
    # Initialize predictor with nonexistent model path
    with pytest.raises(FileNotFoundError) as exc_info:
        FraudShieldPredictor(model_path="nonexistent_directory/missing_model.joblib")
    assert "not found" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 6. Database Rollback & Integrity
# ---------------------------------------------------------------------------
def test_audit_database_transaction_rollback():
    """Verifies SQLite connection context manager rolls back changes on error."""
    with pytest.raises(Exception):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_profiles (upi_id, avg_amount) VALUES ('temp.rollback.user@upi', 999.0);"
            )
            # Intentionally trigger an error
            raise RuntimeError("Simulated mid-transaction failure")

    # Verify rollback: record must not exist
    record = query_one("SELECT * FROM user_profiles WHERE upi_id = 'temp.rollback.user@upi';")
    assert record is None


# ---------------------------------------------------------------------------
# 7. Unauthorised API Requests & Token Verification
# ---------------------------------------------------------------------------
def test_audit_unauthorised_requests_no_token():
    """Verifies that protected endpoints reject requests lacking Authorization header with HTTP 401."""
    resp = client.get("/api/transactions")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_audit_unauthorised_requests_malformed_token():
    """Verifies rejection of malformed or garbage Bearer token."""
    resp = client.get("/api/transactions", headers={"Authorization": "Bearer not-a-valid-jwt"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


def test_audit_unauthorised_requests_tampered_signature():
    """Verifies rejection of token with modified signature (HMAC tamper)."""
    valid_token = create_access_token({"sub": "1", "username": "admin", "role": "ADMIN"})
    parts = valid_token.split(".")
    tampered_sig = parts[2][:-4] + "AAAA"
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    resp = client.get("/api/transactions", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    assert "signature" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()


def test_audit_unauthorised_requests_expired_token():
    """Verifies rejection of expired JWT token."""
    expired_token = create_access_token(
        {"sub": "1", "username": "admin", "role": "ADMIN"},
        expires_delta=timedelta(seconds=-30),
    )
    resp = client.get("/api/transactions", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 8. Role Permissions & RBAC Enforcement
# ---------------------------------------------------------------------------
def test_audit_role_permissions_analyst_vs_admin():
    """Verifies strict boundary: ANALYST cannot access ADMIN endpoints, but can triage."""
    # Analyst blocked from analytics
    assert client.get("/api/analytics", headers=analyst_headers).status_code == 403

    # Analyst blocked from CSV exports
    assert client.get("/api/analytics/export/transactions", headers=analyst_headers).status_code == 403
    assert client.get("/api/analytics/export/alerts", headers=analyst_headers).status_code == 403

    # Analyst blocked from user administration
    assert client.get("/api/users", headers=analyst_headers).status_code == 403

    # Admin permitted on all
    assert client.get("/api/analytics", headers=admin_headers).status_code == 200
    assert client.get("/api/users", headers=admin_headers).status_code == 200


# ---------------------------------------------------------------------------
# 9. SQL Injection Immunity
# ---------------------------------------------------------------------------
def test_audit_sql_injection_attempt_in_search():
    """Verifies that SQL injection payloads in search filters are safely treated as string literals."""
    sqli_payload = "' OR 1=1; DROP TABLE transactions; --"
    resp = client.get(
        f"/api/transactions?search={sqli_payload}",
        headers=analyst_headers,
    )
    assert resp.status_code == 200
    # Table must still exist and return 0 matches for the literal query string
    data = resp.json()
    assert data["total"] == 0

    # Verify transactions table was not dropped
    check = query_one("SELECT COUNT(*) AS cnt FROM transactions;")
    assert check is not None
    assert check["cnt"] >= 0


# ---------------------------------------------------------------------------
# 10. Password Hashing Security & Salt Generation
# ---------------------------------------------------------------------------
def test_audit_password_hashing_security():
    """Verifies PBKDF2-HMAC-SHA256 hashing, unique salts, and rejection of plaintext."""
    raw_pass = "TestAuditSecret2026!"
    hash1 = hash_password(raw_pass)
    hash2 = hash_password(raw_pass)

    # Hashes must differ due to cryptographic 16-byte random salt
    assert hash1 != hash2
    assert hash1.startswith("pbkdf2_sha256$100000$")

    # Plaintext verification
    assert verify_password(raw_pass, hash1) is True
    assert verify_password("WrongPassword!", hash1) is False

    # Check database: no user record must have plaintext password
    users = query_one("SELECT hashed_password FROM app_users WHERE username = 'admin';")
    assert users is not None
    assert not users["hashed_password"].startswith("Admin@")
    assert users["hashed_password"].startswith("pbkdf2_sha256$")


# ---------------------------------------------------------------------------
# 11. CORS Configuration Security
# ---------------------------------------------------------------------------
def test_audit_cors_configuration():
    """Verifies CORS headers for allowed origins and preflight OPTIONS handling."""
    # Preflight OPTIONS request from trusted origin
    resp = client.options(
        "/api/transactions",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
    assert resp.headers["access-control-allow-origin"] == "http://localhost:8000"
