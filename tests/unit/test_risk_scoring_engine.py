"""Unit tests for the TransactionRiskScoringEngine.

Tests diverse real-world transaction scenarios:
1. Everyday retail payment -> Low risk.
2. High-value payment by affluent user -> Low/Medium risk (confirms amount alone doesn't trigger High risk).
3. High-frequency velocity burst -> High risk.
4. SIM swap and nocturnal drain surge -> High risk.
5. Collect request phishing attempt -> Medium/High risk.
6. Separation of model anomaly prediction from rule-based risk indicators.
7. Validation of the 3 documented risk categories (Low risk, Medium risk, High risk).
"""

import pytest
from backend.services.risk_scoring_service import (
    TransactionRiskScoringEngine,
    get_risk_scoring_engine,
)


@pytest.fixture(scope="module")
def engine() -> TransactionRiskScoringEngine:
    return get_risk_scoring_engine()


def test_scenario_1_normal_grocery_payment(engine: TransactionRiskScoringEngine):
    """Everyday retail payment conforms to baseline -> Low risk."""
    tx = {
        "tx_id": "TXN_GROCERY_001",
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "supermarket.dmart@icici",
        "amount": 1250.0,
        "channel": "UPI_APP",
        "device_id": "DEV-XIAOMI-12",
        "velocity_15m": 1.0,
        "timestamp": "2026-10-15T16:00:00Z",  # 4:00 PM
    }
    user_profile = {
        "avg_amount": 2500.0,
        "known_devices": ["DEV-XIAOMI-12"],
        "known_recipients": ["supermarket.dmart@icici"],
    }

    result = engine.evaluate(tx, user_profile)

    assert result.transaction_id == "TXN_GROCERY_001"
    assert result.risk_category == "Low risk"
    assert result.risk_score < 40.0
    assert result.action_recommendation == "APPROVE"
    assert result.anomaly_prediction.is_anomaly is False


def test_scenario_2_affluent_user_high_value_payment(engine: TransactionRiskScoringEngine):
    """High absolute amount (₹35,000) for a user whose typical average is ₹30,000.
    Confirms amount alone does NOT arbitrarily force High risk.
    """
    tx = {
        "tx_id": "TXN_AFFLUENT_002",
        "sender_upi": "executive.wealth@okhdfcbank",
        "receiver_upi": "tanishq.jewelry@icici",
        "amount": 35000.0,  # High amount, but only 1.16x baseline
        "channel": "UPI_APP",
        "device_id": "DEV-IPHONE-15",
        "velocity_15m": 1.0,
        "timestamp": "2026-10-15T18:30:00Z",  # 6:30 PM
    }
    user_profile = {
        "avg_amount": 30000.0,  # User regularly spends ~₹30,000
        "known_devices": ["DEV-IPHONE-15"],
        "known_recipients": ["tanishq.jewelry@icici"],
    }

    result = engine.evaluate(tx, user_profile)

    # Must NOT be High risk because amount is normal for this user
    assert result.risk_category != "High risk"
    assert result.risk_score < 70.0
    # No amount spike indicator should be triggered
    codes = [ind.code for ind in result.detailed_indicators]
    assert "AMOUNT_SPIKE_EXTREME" not in codes
    assert "AMOUNT_SPIKE_MODERATE" not in codes


def test_scenario_3_velocity_burst_account_drain(engine: TransactionRiskScoringEngine):
    """Rapid sequential transactions (velocity = 7) -> High risk."""
    tx = {
        "tx_id": "TXN_VELOCITY_003",
        "sender_upi": "rahul.kumar@paytm",
        "receiver_upi": "unknown.payee@ybl",
        "amount": 8900.0,
        "channel": "UPI_APP",
        "device_id": "DEV-ONEPLUS-11",
        "velocity_15m": 7.0,  # Rapid burst
        "timestamp": "2026-10-15T19:15:00Z",
    }
    user_profile = {
        "avg_amount": 2000.0,
        "known_devices": ["DEV-ONEPLUS-11"],
        "known_recipients": [],
    }

    result = engine.evaluate(tx, user_profile)

    assert result.risk_category == "High risk"
    assert result.risk_score >= 70.0
    assert result.action_recommendation == "HOLD_FOR_REVIEW"
    codes = [ind.code for ind in result.detailed_indicators]
    assert "VELOCITY_BURST_CRITICAL" in codes


def test_scenario_4_sim_swap_midnight_drain(engine: TransactionRiskScoringEngine):
    """Compound attack: unrecognised hardware + off-peak sleep hour + high value spike -> High risk."""
    tx = {
        "tx_id": "TXN_SIM_SWAP_004",
        "sender_upi": "priya.verma@okhdfcbank",
        "receiver_upi": "mule.cash.drop@ybl",
        "amount": 88000.0,  # 73x higher than average
        "channel": "INTENT_FLOW",
        "device_id": "DEV-NEW-UNKNOWN-HARDWARE",  # New device
        "velocity_15m": 4.0,
        "timestamp": "2026-10-15T02:45:00Z",  # 2:45 AM
    }
    user_profile = {
        "avg_amount": 1200.0,
        "known_devices": ["DEV-SAMSUNG-S23"],
        "known_recipients": ["friend@axis"],
    }

    result = engine.evaluate(tx, user_profile)

    assert result.risk_category == "High risk"
    assert result.risk_score >= 70.0
    assert result.action_recommendation == "HOLD_FOR_REVIEW"
    assert result.anomaly_prediction.is_anomaly is True

    codes = [ind.code for ind in result.detailed_indicators]
    assert "NEW_DEVICE_HARDWARE_MISMATCH" in codes
    assert "OFF_PEAK_SLEEP_HOURS" in codes
    assert "AMOUNT_SPIKE_EXTREME" in codes


def test_scenario_5_collect_request_phishing(engine: TransactionRiskScoringEngine):
    """Collect request from unfamiliar payee -> Medium/High risk."""
    tx = {
        "tx_id": "TXN_PHISHING_005",
        "sender_upi": "victim.user@okaxis",
        "receiver_upi": "fraudster.collect@ybl",
        "amount": 18000.0,  # 6x user average
        "channel": "COLLECT_REQUEST",
        "device_id": "DEV-PHONE",
        "velocity_15m": 2.0,
        "timestamp": "2026-10-15T15:00:00Z",
    }
    user_profile = {
        "avg_amount": 3000.0,
        "known_devices": ["DEV-PHONE"],
        "known_recipients": [],
    }

    result = engine.evaluate(tx, user_profile)

    assert result.risk_category in ["Medium risk", "High risk"]
    assert result.risk_score >= 40.0
    codes = [ind.code for ind in result.detailed_indicators]
    assert "COLLECT_REQUEST_CHANNEL" in codes


def test_separation_of_model_and_rule_outputs(engine: TransactionRiskScoringEngine):
    """Verify that model evaluation is strictly decoupled from rule indicators."""
    tx = {
        "amount": 1500.0,
        "channel": "UPI_APP",
        "device_id": "DEV-TEST",
        "timestamp": "2026-10-15T12:00:00Z",
    }
    result = engine.evaluate(tx)

    # AnomalyModelOutput object exists independently
    assert hasattr(result.anomaly_prediction, "is_anomaly")
    assert hasattr(result.anomaly_prediction, "raw_decision_score")
    assert hasattr(result.anomaly_prediction, "model_risk_contribution")
    assert isinstance(result.anomaly_prediction.is_anomaly, bool)

    # Detailed rule indicators list exists independently
    assert isinstance(result.detailed_indicators, list)
    assert isinstance(result.relevant_risk_indicators, list)


def test_risk_category_three_tiers_only(engine: TransactionRiskScoringEngine):
    """Verify that risk_category strictly conforms to the 3 documented levels."""
    for score in [0.0, 25.5, 39.9, 40.0, 55.0, 69.9, 70.0, 85.0, 100.0]:
        cat, action = engine._determine_risk_category(score)
        assert cat in ["Low risk", "Medium risk", "High risk"]
        assert action in ["APPROVE", "STEP_UP_AUTHENTICATION", "HOLD_FOR_REVIEW"]
