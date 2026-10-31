"""Unit test suite for SQLite connection management and CRUD operations.

Tests:
1. WAL mode, foreign keys, and connection management.
2. Users table CRUD operations.
3. Transactions table CRUD operations.
4. Safe duplicate transaction ID handling (update, ignore, raise).
5. Fraud Alerts table CRUD operations.
6. Model Prediction Records table CRUD operations.
7. Foreign key cascading and constraint enforcement.
8. End-to-end transaction processing storing model prediction, score, and explanation.
"""

import json
import pytest
import sqlite3
from database.init_db import init_database
from database.connection import get_db_connection, query_one, query_all
from database.crud import (
    UserCRUD,
    TransactionCRUD,
    AlertCRUD,
    ModelPredictionCRUD,
    DuplicateTransactionError,
)
from backend.services.alert_service import get_alert_service


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Initializes schema and baseline data."""
    init_database()


# ---------------------------------------------------------------------------
# 1. Connection & Configuration Tests
# ---------------------------------------------------------------------------
def test_wal_mode_and_foreign_keys_enabled():
    """Verifies that SQLite WAL mode and foreign key constraints are active."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.lower() == "wal"

        cursor.execute("PRAGMA foreign_keys;")
        fk = cursor.fetchone()[0]
        assert fk == 1


# ---------------------------------------------------------------------------
# 2. Users CRUD Tests
# ---------------------------------------------------------------------------
def test_user_crud_lifecycle():
    """Tests Create, Read, Update, and Delete on users table."""
    test_upi = "rohit.sen@oksbi"

    # Create
    user = UserCRUD.create_user(
        upi_id=test_upi,
        full_name="Rohit Sen",
        email="rohit.sen@banksecure.in",
        phone="+91-9876500001",
        avg_amount=3200.0,
        std_amount=900.0,
        known_devices=["DEV-ROHIT-PIXEL"],
        typical_cities=["Kolkata"],
    )
    assert user is not None
    assert user["upi_id"] == test_upi
    assert user["full_name"] == "Rohit Sen"
    assert user["avg_amount"] == 3200.0
    assert "DEV-ROHIT-PIXEL" in user["known_devices"]

    # Read by ID and UPI
    fetched_by_upi = UserCRUD.get_user_by_upi(test_upi)
    assert fetched_by_upi is not None
    assert fetched_by_upi["id"] == user["id"]

    fetched_by_id = UserCRUD.get_user_by_id(user["id"])
    assert fetched_by_id is not None
    assert fetched_by_id["upi_id"] == test_upi

    # Update
    updated = UserCRUD.update_user(test_upi, {"avg_amount": 4500.0, "total_transactions": 10})
    assert updated is not None
    assert updated["avg_amount"] == 4500.0
    assert updated["total_transactions"] == 10

    # List
    users_list, total = UserCRUD.list_users(limit=10, offset=0)
    assert total >= 1
    assert any(u["upi_id"] == test_upi for u in users_list)

    # Delete
    deleted = UserCRUD.delete_user(test_upi)
    assert deleted is True
    assert UserCRUD.get_user_by_upi(test_upi) is None


# ---------------------------------------------------------------------------
# 3. Transactions CRUD & Safe Duplicate Handling Tests
# ---------------------------------------------------------------------------
def test_transaction_crud_lifecycle():
    """Tests Create, Read, List, Update status, and Delete on transactions table."""
    tx_id = "TX-UNIT-TEST-1001"
    tx_data = {
        "tx_id": tx_id,
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "merchant.books@icici",
        "amount": 750.0,
        "channel": "UPI_APP",
        "device_id": "DEV-XIAOMI-12",
        "ip_address": "49.207.180.12",
        "location_city": "Mumbai",
        "timestamp": "2026-10-31T00:00:00Z",
        "risk_score": 15.0,
        "risk_tier": "LOW",
        "status": "APPROVED",
        "primary_factor": "NORMAL_TRANSACTION",
        "is_flagged": 0,
    }

    # Create
    created = TransactionCRUD.create_transaction(tx_data)
    assert created["tx_id"] == tx_id
    assert created["amount"] == 750.0

    # Read
    fetched = TransactionCRUD.get_transaction_by_tx_id(tx_id)
    assert fetched is not None
    assert fetched["sender_upi"] == "arjun.sharma@okaxis"

    # Update status
    updated = TransactionCRUD.update_transaction_status(tx_id, "BLOCKED")
    assert updated is True
    assert TransactionCRUD.get_transaction_by_tx_id(tx_id)["status"] == "BLOCKED"

    # Clean up
    TransactionCRUD.delete_transaction(tx_id)
    assert TransactionCRUD.get_transaction_by_tx_id(tx_id) is None


def test_safe_duplicate_transaction_handling():
    """Verifies that duplicate transaction IDs are handled safely across strategies."""
    tx_id = "TX-DUP-SAFETY-TEST"
    base_tx = {
        "tx_id": tx_id,
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "merchant@icici",
        "amount": 1000.0,
        "channel": "UPI_APP",
        "device_id": "DEV-1",
        "timestamp": "2026-10-31T00:00:00Z",
        "risk_score": 20.0,
        "risk_tier": "LOW",
        "status": "APPROVED",
    }

    # 1. Initial insert
    t1 = TransactionCRUD.create_transaction(base_tx, on_duplicate="raise")
    assert t1["tx_id"] == tx_id

    # 2. Strategy 'ignore': does not crash, flags duplicate, leaves amount 1000
    dup_tx_ignore = dict(base_tx, amount=5000.0)
    t2 = TransactionCRUD.create_transaction(dup_tx_ignore, on_duplicate="ignore")
    assert t2["is_duplicate"] is True
    assert t2["amount"] == 1000.0  # Kept original

    # 3. Strategy 'update': upserts smoothly without crashing
    dup_tx_update = dict(base_tx, amount=8888.0, status="FLAGGED")
    t3 = TransactionCRUD.create_transaction(dup_tx_update, on_duplicate="update")
    assert t3["amount"] == 8888.0
    assert t3["status"] == "FLAGGED"

    # 4. Strategy 'raise': raises explicit DuplicateTransactionError
    with pytest.raises(DuplicateTransactionError):
        TransactionCRUD.create_transaction(base_tx, on_duplicate="raise")

    # Clean up
    TransactionCRUD.delete_transaction(tx_id)


# ---------------------------------------------------------------------------
# 4. Fraud Alerts CRUD Tests
# ---------------------------------------------------------------------------
def test_fraud_alert_crud_lifecycle():
    """Tests alert creation, querying, SOC triage updates, and deletion."""
    tx_id = "TX-ALERT-TEST-2002"
    alert_id = "ALT-ALERT-TEST-2002"

    # Parent transaction
    TransactionCRUD.create_transaction({
        "tx_id": tx_id,
        "sender_upi": "priya.verma@okhdfcbank",
        "receiver_upi": "suspicious@paytm",
        "amount": 65000.0,
        "channel": "COLLECT_REQUEST",
        "device_id": "DEV-EMULATOR",
        "timestamp": "2026-10-31T00:00:00Z",
        "risk_score": 88.0,
        "risk_tier": "HIGH",
        "status": "FLAGGED",
        "is_flagged": 1,
    })

    # Create alert
    alert = AlertCRUD.create_alert({
        "alert_id": alert_id,
        "tx_id": tx_id,
        "severity": "HIGH",
        "primary_reason": "UNUSUAL_AMOUNT_SPIKE",
        "explanations": [{"factor_name": "AMOUNT_SPIKE", "impact_weight": 0.45, "description": "8x baseline"}],
        "status": "PENDING",
    })
    assert alert["alert_id"] == alert_id
    assert alert["severity"] == "HIGH"
    assert len(alert["explanations"]) == 1

    # Read by alert_id and tx_id
    fetched_alert = AlertCRUD.get_alert_by_id(alert_id)
    assert fetched_alert is not None
    assert fetched_alert["tx_id"] == tx_id

    fetched_by_tx = AlertCRUD.get_alert_by_tx_id(tx_id)
    assert fetched_by_tx is not None
    assert fetched_by_tx["alert_id"] == alert_id

    # Update alert (SOC Action: BLOCK)
    updated = AlertCRUD.update_alert_status(
        alert_id=alert_id,
        action="BLOCK",
        notes="High risk confirmed. Beneficiary VPA blacklisted.",
        reviewed_by="Lead-Analyst",
    )
    assert updated["status"] == "BLOCK"
    assert updated["reviewed_by"] == "Lead-Analyst"

    # Verify that linked transaction status was synchronized to BLOCKED
    linked_tx = TransactionCRUD.get_transaction_by_tx_id(tx_id)
    assert linked_tx["status"] == "BLOCKED"

    # Clean up
    TransactionCRUD.delete_transaction(tx_id)


# ---------------------------------------------------------------------------
# 5. Model Prediction Records CRUD Tests
# ---------------------------------------------------------------------------
def test_model_prediction_records_crud_lifecycle():
    """Tests model prediction records storage, querying, and filtering."""
    tx_id = "TX-PRED-TEST-3003"
    pred_id = f"PRED-{tx_id}"

    # Parent transaction
    TransactionCRUD.create_transaction({
        "tx_id": tx_id,
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "store@icici",
        "amount": 900.0,
        "channel": "UPI_APP",
        "device_id": "DEV-XIAOMI-12",
        "timestamp": "2026-10-31T00:00:00Z",
        "risk_score": 14.5,
        "risk_tier": "LOW",
        "status": "APPROVED",
    })

    # Create Model Prediction Record
    pred_data = {
        "prediction_id": pred_id,
        "tx_id": tx_id,
        "model_name": "IsolationForest",
        "model_version": "1.0.0",
        "is_anomaly": 0,
        "raw_decision_score": 0.145,
        "model_risk_score": 18.2,
        "final_risk_score": 14.5,
        "risk_category": "Low risk",
        "feature_vector": {"amount_scaled": -0.25, "velocity_15m": 1.0},
        "explanation_summary": "NORMAL_TRANSACTION",
        "detailed_explanations": [{"factor_name": "AMOUNT_VS_BASELINE", "impact_weight": 0.15}],
    }

    pred_record = ModelPredictionCRUD.create_prediction_record(pred_data)
    assert pred_record is not None
    assert pred_record["prediction_id"] == pred_id
    assert pred_record["is_anomaly"] == 0
    assert pred_record["final_risk_score"] == 14.5
    assert pred_record["feature_vector"]["amount_scaled"] == -0.25

    # Fetch by tx_id
    fetched = ModelPredictionCRUD.get_prediction_by_tx_id(tx_id)
    assert fetched is not None
    assert fetched["prediction_id"] == pred_id

    # List
    preds_list, total = ModelPredictionCRUD.list_predictions(limit=10, offset=0)
    assert total >= 1

    # Clean up
    TransactionCRUD.delete_transaction(tx_id)


# ---------------------------------------------------------------------------
# 6. Foreign Key Cascading Tests
# ---------------------------------------------------------------------------
def test_foreign_key_cascading_delete():
    """Verifies that deleting a transaction automatically cascades to alerts and prediction records."""
    tx_id = "TX-CASCADE-TEST-4004"
    alert_id = f"ALT-{tx_id}"
    pred_id = f"PRED-{tx_id}"

    # 1. Create parent transaction
    TransactionCRUD.create_transaction({
        "tx_id": tx_id,
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "burner@paytm",
        "amount": 45000.0,
        "channel": "COLLECT_REQUEST",
        "device_id": "DEV-TEST",
        "timestamp": "2026-10-31T00:00:00Z",
    })

    # 2. Create child alert
    AlertCRUD.create_alert({
        "alert_id": alert_id,
        "tx_id": tx_id,
        "severity": "HIGH",
        "primary_reason": "COLLECT_PHISHING",
    })

    # 3. Create child prediction record
    ModelPredictionCRUD.create_prediction_record({
        "prediction_id": pred_id,
        "tx_id": tx_id,
        "is_anomaly": 1,
        "raw_decision_score": -0.15,
        "model_risk_score": 85.0,
        "final_risk_score": 82.0,
        "risk_category": "High risk",
    })

    # Verify both exist
    assert AlertCRUD.get_alert_by_id(alert_id) is not None
    assert ModelPredictionCRUD.get_prediction_by_id(pred_id) is not None

    # 4. Delete parent transaction
    deleted = TransactionCRUD.delete_transaction(tx_id)
    assert deleted is True

    # 5. Verify children were cascade-deleted by SQLite foreign key ON DELETE CASCADE
    assert AlertCRUD.get_alert_by_id(alert_id) is None
    assert ModelPredictionCRUD.get_prediction_by_id(pred_id) is None


# ---------------------------------------------------------------------------
# 7. End-to-End AlertService Storage Verification
# ---------------------------------------------------------------------------
def test_alert_service_stores_transaction_prediction_and_alert():
    """Verifies that AlertService.process_transaction() stores transaction, model prediction record, and alert."""
    service = get_alert_service()
    tx_payload = {
        "sender_upi": "sneha.patel@icici",
        "receiver_upi": "urgent.cashout.scam@ybl",
        "amount": 78000.0,
        "channel": "COLLECT_REQUEST",
        "device_id": "DEV-UNKNOWN-TOR-LOGIN",
        "ip_address": "185.220.101.5",
        "location_city": "Kolkata",
        "velocity_15m": 5.0,
        "time_since_last_sec": 25.0,
        "is_new_recipient": 1,
        "is_new_device": 1,
    }

    result = service.process_transaction(tx_payload)
    tx_id = result["transaction_id"]

    # 1. Verify transaction in transactions table
    tx_row = TransactionCRUD.get_transaction_by_tx_id(tx_id)
    assert tx_row is not None
    assert tx_row["amount"] == 78000.0
    assert tx_row["risk_score"] >= 70.0

    # 2. Verify model prediction record in model_prediction_records table
    pred_row = ModelPredictionCRUD.get_prediction_by_tx_id(tx_id)
    assert pred_row is not None
    assert pred_row["tx_id"] == tx_id
    assert pred_row["model_name"] == "IsolationForest"
    assert pred_row["is_anomaly"] in [0, 1]
    assert pred_row["final_risk_score"] == tx_row["risk_score"]
    assert len(pred_row["detailed_explanations"]) >= 1

    # 3. Verify alert in fraud_alerts table (high-risk transaction)
    alert_row = AlertCRUD.get_alert_by_tx_id(tx_id)
    assert alert_row is not None
    assert alert_row["tx_id"] == tx_id
    assert alert_row["severity"] == "HIGH"
    assert alert_row["status"] == "PENDING"

    # Clean up
    TransactionCRUD.delete_transaction(tx_id)
