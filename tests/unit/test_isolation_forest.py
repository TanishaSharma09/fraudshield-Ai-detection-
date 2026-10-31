"""Unit tests for the Isolation Forest model and prediction engine."""

import pytest
import numpy as np
import pandas as pd
from backend.core.config import settings
from ml_model.predictor import FraudShieldPredictor, evaluate_transaction


@pytest.fixture(scope="module")
def predictor() -> FraudShieldPredictor:
    """Initialises predictor using saved model and preprocessor artifacts."""
    return FraudShieldPredictor()


def test_model_artifacts_exist():
    """Verify that model, preprocessor, and configuration artifacts exist."""
    assert settings.MODEL_PATH.exists()
    assert (settings.SAVED_MODELS_DIR / "preprocessor.joblib").exists()
    assert (settings.SAVED_MODELS_DIR / "model_config.json").exists()


def test_predict_normal_transaction(predictor: FraudShieldPredictor):
    """Verify that a normal everyday grocery payment receives low risk score."""
    normal_tx = {
        "amount": 750.0,
        "channel": "UPI_APP",
        "device_id": "DEV-XIAOMI-12",
        "receiver_upi": "supermarket@icici",
        "sender_upi": "arjun.sharma@okaxis",
        "velocity_15m": 1.0,
        "timestamp": "2026-10-15T14:30:00Z",  # Normal 2:30 PM
    }
    user_profile = {
        "avg_amount": 1500.0,
        "known_devices": ["DEV-XIAOMI-12"],
        "known_recipients": ["supermarket@icici"],
    }

    result = predictor.predict_single(normal_tx, user_profile)

    assert result["is_anomaly"] is False
    assert result["prediction_label"] == "NORMAL"
    assert result["risk_score"] < 50.0
    assert result["risk_tier"] in ["LOW", "MEDIUM"]
    assert result["status"] == "APPROVED"


def test_predict_severe_anomaly(predictor: FraudShieldPredictor):
    """Verify that an off-peak high-amount velocity burst is flagged as anomalous."""
    suspicious_tx = {
        "amount": 92000.0,                     # Massive amount near limit
        "channel": "INTENT_FLOW",
        "device_id": "DEV-NEW-UNKNOWN-HARDWARE", # Brand new device
        "receiver_upi": "fast.cash.mule@ybl",    # Unseen mule
        "sender_upi": "priya.verma@okhdfcbank",
        "velocity_15m": 8.0,                    # Rapid burst
        "timestamp": "2026-10-15T02:45:00Z",    # 2:45 AM
    }
    user_profile = {
        "avg_amount": 1200.0,                   # User usually spends only ₹1,200
        "known_devices": ["DEV-SAMSUNG-S23"],
        "known_recipients": ["friend@axis"],
    }

    result = predictor.predict_single(suspicious_tx, user_profile)

    assert result["is_anomaly"] is True
    assert result["prediction_label"] == "SUSPICIOUS_ANOMALY"
    assert result["risk_score"] >= 70.0
    assert result["risk_tier"] in ["HIGH", "CRITICAL"]
    assert result["status"] in ["FLAGGED", "BLOCKED"]
    assert result["primary_factor"] in [
        "UNUSUAL_AMOUNT_SPIKE", "HIGH_TRANSACTION_VELOCITY", "UNRECOGNISED_DEVICE_LOGIN", "MULTIVARIATE_BEHAVIORAL_ANOMALY"
    ]


def test_predict_batch(predictor: FraudShieldPredictor):
    """Verify batch inference enriches DataFrame with prediction columns."""
    sample_df = pd.DataFrame([
        {
            "tx_id": "TX_B1",
            "amount": 500.0,
            "channel": "QR_CODE",
            "device_id": "DEV-1",
            "sender_upi": "user1@okaxis",
            "receiver_upi": "tea.stall@paytm",
            "timestamp": "2026-10-10T11:00:00Z",
        },
        {
            "tx_id": "TX_B2",
            "amount": 95000.0,
            "channel": "COLLECT_REQUEST",
            "device_id": "DEV-NEW-UNKNOWN",
            "sender_upi": "user2@paytm",
            "receiver_upi": "scam.collect@ybl",
            "timestamp": "2026-10-10T03:15:00Z",
        },
    ])

    batch_res = predictor.predict_batch(sample_df)

    assert "is_anomaly" in batch_res.columns
    assert "risk_score" in batch_res.columns
    assert "risk_tier" in batch_res.columns
    assert "action_status" in batch_res.columns
    assert len(batch_res) == 2


def test_convenience_evaluate_transaction_wrapper():
    """Verify that module-level evaluate_transaction function works."""
    tx = {
        "amount": 1200.0,
        "channel": "UPI_APP",
        "device_id": "DEV-TEST",
        "timestamp": "2026-10-10T12:00:00Z",
    }
    res = evaluate_transaction(tx)
    assert "risk_score" in res
    assert 0.0 <= res["risk_score"] <= 100.0
