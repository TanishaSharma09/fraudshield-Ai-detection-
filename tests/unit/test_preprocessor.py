"""Unit tests for the FraudShieldPreprocessor module.

Tests:
1. Data cleaning and invalid value rejection.
2. Temporal leak-free feature engineering.
3. Consistency between batch transform and real-time transform_single.
4. Preprocessor persistence and roundtrip loading via joblib.
5. Train/test temporal split integrity.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml_model.features.preprocessor import (
    FraudShieldPreprocessor,
    FEATURE_COLUMNS,
)


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    """Creates a sample sequence of UPI transactions."""
    return pd.DataFrame([
        {
            "tx_id": "TX101",
            "timestamp": "2026-10-01T10:00:00Z",
            "sender_upi": "alice@okaxis",
            "receiver_upi": "bob@paytm",
            "amount": 1000.0,
            "channel": "UPI_APP",
            "device_id": "DEV-IPHONE",
            "is_fraud": 0,
        },
        {
            "tx_id": "TX102",
            "timestamp": "2026-10-01T10:05:00Z",  # 5 min later
            "sender_upi": "alice@okaxis",
            "receiver_upi": "charlie@icici",     # New recipient
            "amount": 2000.0,
            "channel": "UPI_APP",
            "device_id": "DEV-IPHONE",
            "is_fraud": 0,
        },
        {
            "tx_id": "TX103",
            "timestamp": "2026-10-01T10:10:00Z",  # 5 min later
            "sender_upi": "alice@okaxis",
            "receiver_upi": "mule@ybl",          # Another new recipient
            "amount": 45000.0,                   # Big spike
            "channel": "INTENT_FLOW",
            "device_id": "DEV-NEW-ANDROID",      # New device
            "is_fraud": 1,
        },
        {
            "tx_id": "TX104",
            "timestamp": "2026-10-02T02:30:00Z",  # Next day at 2:30 AM (unusual hour)
            "sender_upi": "alice@okaxis",
            "receiver_upi": "bob@paytm",
            "amount": 500.0,
            "channel": "COLLECT_REQUEST",
            "device_id": "DEV-IPHONE",
            "is_fraud": 0,
        },
    ])


def test_data_cleaning_drops_duplicates_and_invalids():
    """Verify that duplicate tx_ids and non-positive amounts are dropped."""
    dirty_df = pd.DataFrame([
        {"tx_id": "DUP1", "amount": 100.0, "timestamp": "2026-10-01T09:00:00Z"},
        {"tx_id": "DUP1", "amount": 100.0, "timestamp": "2026-10-01T09:01:00Z"},  # Duplicate
        {"tx_id": "INV1", "amount": -50.0, "timestamp": "2026-10-01T09:02:00Z"},  # Invalid
        {"tx_id": "INV2", "amount": 0.0, "timestamp": "2026-10-01T09:03:00Z"},    # Zero
        {"tx_id": "VAL1", "amount": 500.0, "timestamp": "2026-10-01T09:04:00Z"},  # Valid
    ])

    preprocessor = FraudShieldPreprocessor()
    clean = preprocessor.clean_raw_data(dirty_df)

    assert len(clean) == 2
    assert list(clean["tx_id"]) == ["DUP1", "VAL1"]


def test_leak_free_causality(sample_raw_df: pd.DataFrame):
    """Verify historical features at index K only reflect transactions before K."""
    preprocessor = FraudShieldPreprocessor()
    eng = preprocessor.engineer_batch_features(sample_raw_df)

    # First transaction (TX101): Cold-start, new recipient is 0 (first known recipient)
    assert eng.loc[0, "is_new_recipient"] == 0.0
    assert eng.loc[0, "is_new_device"] == 0.0
    assert eng.loc[0, "velocity_15m"] == 1.0

    # Second transaction (TX102): charlie is a new recipient (only bob was known)
    assert eng.loc[1, "is_new_recipient"] == 1.0
    assert eng.loc[1, "is_new_device"] == 0.0
    assert eng.loc[1, "velocity_15m"] == 2.0  # within 5 mins

    # Third transaction (TX103): new device DEV-NEW-ANDROID + new recipient
    assert eng.loc[2, "is_new_device"] == 1.0
    assert eng.loc[2, "is_new_recipient"] == 1.0
    assert eng.loc[2, "velocity_15m"] == 3.0  # 3 txs in 10 mins

    # Fourth transaction (TX104): 2:30 AM -> unusual hour = 1
    assert eng.loc[3, "is_unusual_hour"] == 1.0
    # Bob was already paid in TX101, so NOT a new recipient
    assert eng.loc[3, "is_new_recipient"] == 0.0
    # Over 16 hours elapsed, velocity in 15m is back to 1
    assert eng.loc[3, "velocity_15m"] == 1.0


def test_transform_single_consistency(sample_raw_df: pd.DataFrame):
    """Verify that transform_single returns correctly shaped vector with identical feature columns."""
    preprocessor = FraudShieldPreprocessor()
    preprocessor.fit(sample_raw_df)

    live_tx = {
        "amount": 2500.0,
        "channel": "UPI_APP",
        "device_id": "DEV-IPHONE",
        "receiver_upi": "merchant@icici",
        "timestamp": "2026-10-02T14:00:00Z",
    }
    user_profile = {
        "avg_amount": 1800.0,
        "known_devices": ["DEV-IPHONE"],
        "known_recipients": ["merchant@icici"],
    }

    vec = preprocessor.transform_single(live_tx, user_profile)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (1, len(FEATURE_COLUMNS))
    assert not np.isnan(vec).any()


def test_serialization_roundtrip(tmp_path: Path, sample_raw_df: pd.DataFrame):
    """Verify that preprocessor can be saved and reloaded via joblib identically."""
    preprocessor = FraudShieldPreprocessor()
    preprocessor.fit(sample_raw_df)

    dest = tmp_path / "test_preprocessor.joblib"
    preprocessor.save(dest)
    assert dest.exists()

    loaded = FraudShieldPreprocessor.load(dest)
    assert loaded.is_fitted is True
    assert loaded.population_mean_amount == preprocessor.population_mean_amount

    # Test transformation equivalence
    vec_orig = preprocessor.transform_single({"amount": 1500.0})
    vec_loaded = loaded.transform_single({"amount": 1500.0})
    np.testing.assert_allclose(vec_orig, vec_loaded)


def test_split_dataset_temporal(sample_raw_df: pd.DataFrame):
    """Verify split_dataset divides data chronologically without leakage."""
    preprocessor = FraudShieldPreprocessor()
    split = preprocessor.split_dataset(sample_raw_df, test_size=0.5, temporal=True)

    assert len(split.X_train) == 2
    assert len(split.X_test) == 2
    assert split.X_train.shape[1] == len(FEATURE_COLUMNS)
    assert split.X_test.shape[1] == len(FEATURE_COLUMNS)
    assert len(split.y_train) == 2
    assert len(split.y_test) == 2
