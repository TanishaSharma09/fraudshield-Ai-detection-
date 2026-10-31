"""FraudShield AI - Unit Test Suite for Behavioural Anomaly Detection & Graph Analysis.

Validates the 7 core behavioural detection features:
1. User-specific transaction baselines (strictly leak-free temporal causality).
2. Transaction frequency deviations.
3. Unusual payment amount detection.
4. New recipient patterns.
5. New device patterns (including rapid device switching).
6. Rapid transaction sequences (sub-60s burst and micro-probe drain).
7. Suspicious repeated interactions between synthetic accounts.
8. Account relationship graph generation and mule hub detection.
9. Backward compatibility with the existing Isolation Forest model.
"""

from datetime import datetime, timezone
import pytest

from ml_model.behavioural.baseline_tracker import (
    BehaviouralBaselineTracker,
    UserBaselineProfile,
    get_baseline_tracker,
)
from ml_model.behavioural.anomaly_detector import (
    BehaviouralAnomalyDetector,
    get_behavioural_detector,
)
from ml_model.behavioural.graph_analyzer import (
    AccountRelationshipGraphAnalyzer,
    get_graph_analyzer,
)
from backend.services.risk_scoring_service import get_risk_scoring_engine


# ---------------------------------------------------------------------------
# 1. Zero Future Data Leakage & User-Specific Baselines
# ---------------------------------------------------------------------------
def test_leak_free_user_baseline_tracking():
    """Verifies that user baselines only ingest transactions strictly prior to the current timestamp."""
    tracker = get_baseline_tracker()
    sender = "leaktest.user@upi"

    records = [
        {"sender_upi": sender, "receiver_upi": "store1@upi", "amount": 500.0, "device_id": "DEV-1", "timestamp": "2026-10-01T10:00:00Z"},
        {"sender_upi": sender, "receiver_upi": "store2@upi", "amount": 700.0, "device_id": "DEV-1", "timestamp": "2026-10-05T12:00:00Z"},
        {"sender_upi": sender, "receiver_upi": "store1@upi", "amount": 800.0, "device_id": "DEV-1", "timestamp": "2026-10-10T14:00:00Z"},
        # Future transaction with extreme whale amount
        {"sender_upi": sender, "receiver_upi": "mule.crypto@upi", "amount": 95000.0, "device_id": "DEV-NEW", "timestamp": "2026-10-20T16:00:00Z"},
    ]

    # Baseline evaluated as of 2026-10-06 (must only see tx 1 & 2)
    b_mid = tracker.compute_baseline_from_records(
        sender_upi=sender,
        historical_records=records,
        as_of_timestamp="2026-10-06T00:00:00Z",
    )
    assert b_mid.total_prior_transactions == 2
    assert b_mid.avg_amount == 600.0  # (500 + 700) / 2
    assert "DEV-NEW" not in b_mid.known_devices
    assert "mule.crypto@upi" not in b_mid.known_recipients
    assert "store1@upi" in b_mid.known_recipients
    assert "store2@upi" in b_mid.known_recipients

    # Baseline evaluated as of 2026-10-12 (must see tx 1, 2, and 3, but NOT 4)
    b_before_whale = tracker.compute_baseline_from_records(
        sender_upi=sender,
        historical_records=records,
        as_of_timestamp="2026-10-12T00:00:00Z",
    )
    assert b_before_whale.total_prior_transactions == 3
    assert round(b_before_whale.avg_amount, 2) == 666.67
    assert b_before_whale.max_amount == 800.0
    assert "mule.crypto@upi" not in b_before_whale.known_recipients
    assert "DEV-NEW" not in b_before_whale.known_devices


# ---------------------------------------------------------------------------
# 2. Unusual Payment Amount Detection
# ---------------------------------------------------------------------------
def test_unusual_payment_amount_detection():
    """Verifies personal baseline amount deviation ratios and whale spikes."""
    detector = get_behavioural_detector()
    baseline = UserBaselineProfile(
        sender_upi="user.baseline@upi",
        as_of_timestamp="2026-10-25T12:00:00Z",
        total_prior_transactions=15,
        avg_amount=1000.0,
        std_amount=250.0,
        min_amount=400.0,
        max_amount=1800.0,
        daily_frequency_mean=1.5,
        known_devices={"DEV-TRUSTED-1"},
        known_recipients={"friend@upi"},
    )

    # 1. Normal retail amount -> no amount indicator
    res_normal = detector.analyze(
        transaction={"sender_upi": "user.baseline@upi", "receiver_upi": "friend@upi", "amount": 1100.0, "device_id": "DEV-TRUSTED-1"},
        user_baseline=baseline,
    )
    amt_inds = [i for i in res_normal.indicators if i.category == "AMOUNT"]
    assert len(amt_inds) == 0

    # 2. Significant spike (5.0x baseline) -> AMOUNT_SIGNIFICANT_SPIKE
    res_spike = detector.analyze(
        transaction={"sender_upi": "user.baseline@upi", "receiver_upi": "friend@upi", "amount": 5000.0, "device_id": "DEV-TRUSTED-1"},
        user_baseline=baseline,
    )
    spike_inds = [i for i in res_spike.indicators if i.feature_id == "AMOUNT_SIGNIFICANT_SPIKE"]
    assert len(spike_inds) == 1
    assert spike_inds[0].severity == "HIGH"

    # 3. Extreme whale spike (15.0x baseline) -> AMOUNT_WHALE_SPIKE
    res_whale = detector.analyze(
        transaction={"sender_upi": "user.baseline@upi", "receiver_upi": "friend@upi", "amount": 15000.0, "device_id": "DEV-TRUSTED-1"},
        user_baseline=baseline,
    )
    whale_inds = [i for i in res_whale.indicators if i.feature_id == "AMOUNT_WHALE_SPIKE"]
    assert len(whale_inds) == 1
    assert whale_inds[0].severity == "CRITICAL"


# ---------------------------------------------------------------------------
# 3. Transaction Frequency Deviations
# ---------------------------------------------------------------------------
def test_transaction_frequency_deviation():
    """Verifies detection of frequency surges exceeding established daily cadence."""
    detector = get_behavioural_detector()
    baseline = UserBaselineProfile(
        sender_upi="freq.user@upi",
        as_of_timestamp="2026-10-25T12:00:00Z",
        total_prior_transactions=30,
        avg_amount=1500.0,
        std_amount=300.0,
        min_amount=500.0,
        max_amount=2500.0,
        daily_frequency_mean=1.0,  # Typically 1 transaction per day
        recent_15m_count=6,        # Critical burst of 6 past txs in 15m
        known_devices={"DEV-A"},
        known_recipients={"shop@upi"},
    )

    res = detector.analyze(
        transaction={"sender_upi": "freq.user@upi", "receiver_upi": "shop@upi", "amount": 1200.0, "device_id": "DEV-A"},
        user_baseline=baseline,
    )
    freq_inds = [i for i in res.indicators if i.category == "FREQUENCY"]
    assert len(freq_inds) >= 1
    assert freq_inds[0].feature_id == "FREQ_CRITICAL_DEVIATION"
    assert freq_inds[0].severity == "CRITICAL"


# ---------------------------------------------------------------------------
# 4. New Recipient & New Device Patterns
# ---------------------------------------------------------------------------
def test_new_recipient_and_device_patterns():
    """Verifies unfamiliar payee detection and rapid hardware switching."""
    detector = get_behavioural_detector()
    baseline = UserBaselineProfile(
        sender_upi="alice@upi",
        as_of_timestamp="2026-10-25T12:00:00Z",
        total_prior_transactions=10,
        avg_amount=2000.0,
        std_amount=400.0,
        min_amount=500.0,
        max_amount=3000.0,
        daily_frequency_mean=1.5,
        known_devices={"DEV-ALICE-PHONE"},
        known_recipients={"landlord@upi", "grocery@upi"},
        seconds_since_last_tx=120.0,  # 2 minutes ago
    )

    # 1. New recipient with large amount (₹8,000, 4.0x)
    res_rec = detector.analyze(
        transaction={
            "sender_upi": "alice@upi",
            "receiver_upi": "stranger.unknown@upi",
            "amount": 8000.0,
            "device_id": "DEV-ALICE-PHONE",
        },
        user_baseline=baseline,
    )
    rec_inds = [i for i in res_rec.indicators if i.feature_id == "RECIPIENT_NOVEL_LARGE_TRANSFER"]
    assert len(rec_inds) == 1
    assert rec_inds[0].severity == "HIGH"

    # 2. Rapid device switching (new device 120s after previous transaction)
    res_dev = detector.analyze(
        transaction={
            "sender_upi": "alice@upi",
            "receiver_upi": "grocery@upi",
            "amount": 1500.0,
            "device_id": "DEV-ATTACKER-ROUTER",
        },
        user_baseline=baseline,
    )
    dev_inds = [i for i in res_dev.indicators if i.feature_id == "DEVICE_RAPID_SWITCHING"]
    assert len(dev_inds) == 1
    assert dev_inds[0].severity == "CRITICAL"


# ---------------------------------------------------------------------------
# 5. Rapid Transaction Sequences & Micro-Probing
# ---------------------------------------------------------------------------
def test_rapid_transaction_sequences():
    """Verifies sub-60s burst detection and micro-probe drain sequence identification."""
    detector = get_behavioural_detector()

    # 1. Sub-60s Burst
    b_burst = UserBaselineProfile(
        sender_upi="bob@upi",
        as_of_timestamp="2026-10-25T12:00:00Z",
        total_prior_transactions=5,
        avg_amount=1000.0,
        std_amount=200.0,
        min_amount=500.0,
        max_amount=1500.0,
        daily_frequency_mean=1.0,
        recent_60s_count=2,  # 2 prior transfers in last minute
        known_devices={"DEV-BOB"},
        known_recipients={"friend@upi"},
    )
    res_burst = detector.analyze(
        transaction={"sender_upi": "bob@upi", "receiver_upi": "friend@upi", "amount": 1000.0, "device_id": "DEV-BOB"},
        user_baseline=b_burst,
    )
    seq_inds = [i for i in res_burst.indicators if i.feature_id == "SEQUENCE_SUB_60S_BURST"]
    assert len(seq_inds) == 1
    assert seq_inds[0].severity == "HIGH"

    # 2. Micro-Probe followed by Large Drain
    b_probe = UserBaselineProfile(
        sender_upi="carol@upi",
        as_of_timestamp="2026-10-25T12:00:00Z",
        total_prior_transactions=8,
        avg_amount=2000.0,
        std_amount=500.0,
        min_amount=10.0,  # nominal ₹10 test authorization observed
        max_amount=3000.0,
        daily_frequency_mean=1.2,
        seconds_since_last_tx=180.0,  # within 3 minutes of the test
        known_devices={"DEV-CAROL"},
        known_recipients={"merchant@upi"},
    )
    res_probe = detector.analyze(
        transaction={"sender_upi": "carol@upi", "receiver_upi": "unknown.drain@upi", "amount": 48000.0, "device_id": "DEV-CAROL"},
        user_baseline=b_probe,
    )
    probe_inds = [i for i in res_probe.indicators if i.feature_id == "SEQUENCE_MICRO_PROBE_DRAIN"]
    assert len(probe_inds) == 1
    assert probe_inds[0].severity == "CRITICAL"


# ---------------------------------------------------------------------------
# 6. Suspicious Repeated Interactions
# ---------------------------------------------------------------------------
def test_suspicious_repeated_interactions():
    """Verifies detection of high-frequency targeted transfers between synthetic account pairs."""
    detector = get_behavioural_detector()
    baseline = UserBaselineProfile(
        sender_upi="mulesender@upi",
        as_of_timestamp="2026-10-25T12:00:00Z",
        total_prior_transactions=12,
        avg_amount=5000.0,
        std_amount=1000.0,
        min_amount=2000.0,
        max_amount=8000.0,
        daily_frequency_mean=2.0,
        recent_15m_count=4,
        known_devices={"DEV-MULE"},
        known_recipients={"target.mule.hub@ybl"},
        recipient_interaction_counts={"target.mule.hub@ybl": 4},  # Already sent 4 times
    )

    res = detector.analyze(
        transaction={
            "sender_upi": "mulesender@upi",
            "receiver_upi": "target.mule.hub@ybl",
            "amount": 5000.0,
            "device_id": "DEV-MULE",
        },
        user_baseline=baseline,
    )
    pair_inds = [i for i in res.indicators if i.feature_id == "PAIR_REPEATED_HIGH_VELOCITY"]
    assert len(pair_inds) == 1
    assert pair_inds[0].severity == "HIGH"


# ---------------------------------------------------------------------------
# 7. Account Relationship Network Graph Analysis
# ---------------------------------------------------------------------------
def test_account_relationship_graph_analyzer():
    """Verifies graph generation, node degrees, edge properties, and mule hub identification."""
    analyzer = get_graph_analyzer()

    synthetic_txs = [
        {"sender_upi": "victim1@upi", "receiver_upi": "mule.collector@upi", "amount": 25000.0, "risk_score": 85.0, "is_flagged": 1, "channel": "INTENT_FLOW", "timestamp": "2026-10-25T10:00:00Z"},
        {"sender_upi": "victim2@upi", "receiver_upi": "mule.collector@upi", "amount": 35000.0, "risk_score": 88.0, "is_flagged": 1, "channel": "INTENT_FLOW", "timestamp": "2026-10-25T10:05:00Z"},
        {"sender_upi": "mule.collector@upi", "receiver_upi": "crypto.cashout@upi", "amount": 55000.0, "risk_score": 92.0, "is_flagged": 1, "channel": "INTENT_FLOW", "timestamp": "2026-10-25T10:15:00Z"},
        {"sender_upi": "normal.user@upi", "receiver_upi": "grocery.store@upi", "amount": 450.0, "risk_score": 8.0, "is_flagged": 0, "channel": "QR_CODE", "timestamp": "2026-10-25T10:20:00Z"},
    ]

    graph = analyzer.build_graph_from_records(synthetic_txs)
    assert "nodes" in graph
    assert "edges" in graph
    assert "metrics" in graph

    nodes = graph["nodes"]
    edges = graph["edges"]
    metrics = graph["metrics"]

    assert metrics["total_nodes"] >= 4
    assert metrics["total_edges"] >= 3
    assert metrics["suspicious_edges_count"] >= 2

    # Check that mule.collector@upi was flagged as a mule hub
    mule_nodes = [n for n in nodes if n["id"] == "mule.collector@upi"]
    assert len(mule_nodes) == 1
    assert mule_nodes[0]["is_mule_candidate"] is True
    assert mule_nodes[0]["is_suspicious"] is True


# ---------------------------------------------------------------------------
# 8. Backward Compatibility with Risk Scoring Engine & Isolation Forest
# ---------------------------------------------------------------------------
def test_risk_scoring_engine_integration_backward_compatibility():
    """Verifies that the enhanced risk engine works seamlessly without breaking Isolation Forest."""
    engine = get_risk_scoring_engine()

    # Normal transaction conforms to baseline -> Low risk
    tx_normal = {
        "tx_id": "TXN_INTEG_001",
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "supermarket.dmart@icici",
        "amount": 950.0,
        "channel": "UPI_APP",
        "device_id": "DEV-XIAOMI-12",
        "velocity_15m": 1.0,
        "timestamp": "2026-10-25T14:00:00Z",
    }
    profile_normal = {
        "avg_amount": 2500.0,
        "known_devices": ["DEV-XIAOMI-12"],
        "known_recipients": ["supermarket.dmart@icici"],
    }
    res_normal = engine.evaluate(tx_normal, profile_normal)
    assert res_normal.risk_category == "Low risk"
    assert res_normal.risk_score < 40.0
    assert res_normal.action_recommendation == "APPROVE"
    assert res_normal.anomaly_prediction.is_anomaly is False

    # Compound attack (velocity burst + device switch + extreme amount) -> High risk
    tx_attack = {
        "tx_id": "TXN_INTEG_002",
        "sender_upi": "arjun.sharma@okaxis",
        "receiver_upi": "unknown.mule.crypto@ybl",
        "amount": 85000.0,
        "channel": "INTENT_FLOW",
        "device_id": "DEV-ATTACKER-NEW",
        "velocity_15m": 7.0,
        "timestamp": "2026-10-25T02:30:00Z",  # Midnight off-peak
    }
    res_attack = engine.evaluate(tx_attack, profile_normal)
    assert res_attack.risk_category == "High risk"
    assert res_attack.risk_score >= 70.0
    assert res_attack.action_recommendation == "HOLD_FOR_REVIEW"
    assert len(res_attack.detailed_indicators) >= 3
