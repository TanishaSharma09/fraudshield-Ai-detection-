"""Unit tests for the TransparentFeatureExplainer and AlertService modules."""

import pytest
from database.init_db import init_database
from database.connection import query_one
from backend.services.risk_scoring_service import get_risk_scoring_engine
from ml_model.explainability.explainer import (
    TransparentFeatureExplainer,
    get_explainer,
    generate_explainable_alert,
)
from backend.services.alert_service import AlertService, get_alert_service


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_database()


@pytest.fixture(scope="module")
def explainer() -> TransparentFeatureExplainer:
    return get_explainer()


@pytest.fixture(scope="module")
def scoring_engine():
    return get_risk_scoring_engine()


def test_explainer_initialization(explainer: TransparentFeatureExplainer):
    """Verify explainer initializes with baseline feature statistics."""
    assert len(explainer.feature_stats) > 0
    assert "amount_scaled" in explainer.feature_stats


def test_explain_high_risk_compound_attack(
    explainer: TransparentFeatureExplainer,
    scoring_engine,
):
    """Verify that an attack generates structured, weighted contributing factors."""
    attack_tx = {
        "tx_id": "TX_EXP_001",
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "unknown.mule@ybl",
        "amount": 89000.0,
        "channel": "INTENT_FLOW",
        "device_id": "DEV-NEW-UNKNOWN",
        "velocity_15m": 7.0,
        "timestamp": "2026-10-15T02:30:00Z",  # 2:30 AM
    }
    user_profile = {
        "avg_amount": 2500.0,
        "known_devices": ["DEV-XIAOMI-12"],
        "known_recipients": ["merchant@icici"],
    }

    score_res = scoring_engine.evaluate(attack_tx, user_profile)
    alert = explainer.explain(attack_tx, user_profile, score_res)

    assert alert.transaction_id == "TX_EXP_001"
    assert alert.risk_level == "High risk"
    assert alert.risk_score >= 70.0
    assert len(alert.contributing_factors) >= 3

    factor_ids = [f.factor_id for f in alert.contributing_factors]
    assert "AMOUNT_DEVIATION" in factor_ids
    assert "VELOCITY_BURST" in factor_ids
    assert "HARDWARE_DEVICE_MISMATCH" in factor_ids
    assert "NOCTURNAL_OFF_PEAK_TIMING" in factor_ids

    # Verify weights are sorted descending and sum to ~1.0
    weights = [f.impact_weight for f in alert.contributing_factors]
    assert weights == sorted(weights, reverse=True)
    assert abs(sum(weights) - 1.0) < 0.05

    # Verify legal disclaimer
    assert "does not constitute definitive proof of criminal fraud" in alert.disclaimer


def test_explain_normal_transaction(
    explainer: TransparentFeatureExplainer,
    scoring_engine,
):
    """Verify normal transaction produces benign factor and automated approval."""
    normal_tx = {
        "tx_id": "TX_EXP_NORM",
        "sender_upi": "priya.verma@okhdfcbank",
        "receiver_upi": "grocery@icici",
        "amount": 850.0,
        "channel": "UPI_APP",
        "device_id": "DEV-SAMSUNG-S23",
        "velocity_15m": 1.0,
        "timestamp": "2026-10-15T15:00:00Z",
    }
    user_profile = {
        "avg_amount": 1200.0,
        "known_devices": ["DEV-SAMSUNG-S23"],
        "known_recipients": ["grocery@icici"],
    }

    score_res = scoring_engine.evaluate(normal_tx, user_profile)
    alert = explainer.explain(normal_tx, user_profile, score_res)

    assert alert.risk_level == "Low risk"
    assert "AUTOMATED APPROVAL" in alert.recommended_review_action


def test_alert_service_persistence():
    """Verify that AlertService persists scored payment and high-risk alert to SQLite."""
    service = get_alert_service()

    tx = {
        "tx_id": "TX_PERSIST_ALERT_01",
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "mule.drop@ybl",
        "amount": 95000.0,
        "channel": "INTENT_FLOW",
        "device_id": "DEV-NEW-SUSPICIOUS",
        "velocity_15m": 6.0,
        "timestamp": "2026-10-15T03:00:00Z",
    }

    res = service.process_transaction(tx)

    assert res["transaction_id"] == "TX_PERSIST_ALERT_01"
    assert res["risk_category"] == "High risk"
    assert res["alert_id"] is not None

    # Query SQLite database to verify physical persistence
    db_tx = query_one("SELECT * FROM transactions WHERE tx_id = ?;", ("TX_PERSIST_ALERT_01",))
    assert db_tx is not None
    assert db_tx["amount"] == 95000.0
    assert db_tx["is_flagged"] == 1

    db_alert = query_one("SELECT * FROM fraud_alerts WHERE tx_id = ?;", ("TX_PERSIST_ALERT_01",))
    assert db_alert is not None
    assert db_alert["severity"] == "HIGH"
    assert db_alert["status"] == "PENDING"
