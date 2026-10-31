"""FraudShield AI - Behavioural Anomaly Detection Engine.

Implements deep behavioural feature analysis across 7 distinct dimensions:
1. User-Specific Transaction Baselines (empirical personal profile vs population prior).
2. Transaction Frequency Deviations (rolling transaction rate vs historical daily cadence).
3. Unusual Payment Amount Detection (amount ratio and z-score relative to personal history).
4. New Recipient Patterns (unseen payee VPA, sudden high-value transfer to novel payee).
5. New Device Patterns (unseen hardware fingerprint, rapid device hopping/switching).
6. Rapid Transaction Sequences (micro-probing patterns, sub-60s burst account draining).
7. Suspicious Repeated Interactions (high-frequency sender-receiver pair cycles, mule dispersal).

Includes transparent, structured explanations and impact scores for each indicator,
operating causally without future-data leakage.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
import numpy as np

from ml_model.behavioural.baseline_tracker import (
    BehaviouralBaselineTracker,
    UserBaselineProfile,
    get_baseline_tracker,
)

SeverityLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass
class BehaviouralAnomalyIndicator:
    """Detailed behavioural signal resulting from deep profile deviation analysis."""
    feature_id: str
    feature_name: str
    category: str  # "BASELINE", "FREQUENCY", "AMOUNT", "RECIPIENT", "DEVICE", "SEQUENCE", "PAIR_INTERACTION"
    severity: SeverityLevel
    impact_points: float  # Points contributed to composite risk (0.0 to 45.0)
    observed_value: Any
    baseline_value: Any
    explanation: str
    review_recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "feature_name": self.feature_name,
            "category": self.category,
            "severity": self.severity,
            "impact_points": round(self.impact_points, 2),
            "observed_value": self.observed_value,
            "baseline_value": self.baseline_value,
            "explanation": self.explanation,
            "review_recommendation": self.review_recommendation,
        }


@dataclass
class BehaviouralAnalysisResult:
    """Comprehensive evaluation payload for all 7 behavioural dimensions."""
    sender_upi: str
    receiver_upi: str
    evaluated_at: str
    baseline: UserBaselineProfile
    indicators: list[BehaviouralAnomalyIndicator] = field(default_factory=list)
    total_penalty_points: float = 0.0
    highest_severity: SeverityLevel = "LOW"
    is_behavioural_anomaly: bool = False
    primary_factor: str = "NORMAL_BEHAVIOUR"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender_upi": self.sender_upi,
            "receiver_upi": self.receiver_upi,
            "evaluated_at": self.evaluated_at,
            "baseline": self.baseline.to_dict(),
            "indicators": [ind.to_dict() for ind in self.indicators],
            "total_penalty_points": round(self.total_penalty_points, 2),
            "highest_severity": self.highest_severity,
            "is_behavioural_anomaly": self.is_behavioural_anomaly,
            "primary_factor": self.primary_factor,
        }


class BehaviouralAnomalyDetector:
    """Engine executing leak-free multi-dimensional behavioural anomaly detection."""

    def __init__(self, baseline_tracker: BehaviouralBaselineTracker | None = None) -> None:
        self.tracker = baseline_tracker or get_baseline_tracker()

    def analyze(
        self,
        transaction: dict[str, Any],
        user_baseline: UserBaselineProfile | None = None,
        db_path: str | None = None,
    ) -> BehaviouralAnalysisResult:
        """Analyzes an incoming payment across all 7 behavioural anomaly dimensions."""
        sender_vpa = str(transaction.get("sender_upi", "")).strip().lower()
        receiver_vpa = str(transaction.get("receiver_upi", "")).strip().lower()
        amt = float(transaction.get("amount", 0.0))
        device_id = str(transaction.get("device_id", "DEV-UNKNOWN")).strip()
        channel = str(transaction.get("channel", "UPI_APP")).upper()
        tx_ts = transaction.get("timestamp") or datetime.now(timezone.utc).isoformat()

        # 1. Establish leak-free User Baseline Profile
        if user_baseline is None:
            user_baseline = self.tracker.get_user_baseline_from_db(
                sender_upi=sender_vpa,
                as_of_timestamp=tx_ts,
                db_path=db_path,
            )

        indicators: list[BehaviouralAnomalyIndicator] = []
        user_avg = max(10.0, user_baseline.avg_amount)
        user_std = max(50.0, user_baseline.std_amount)

        # ------------------------------------------------------------------
        # FEATURE 1 & 3: Unusual Payment Amount Detection & Personal Baseline
        # ------------------------------------------------------------------
        amount_ratio = amt / user_avg
        z_score = (amt - user_avg) / user_std

        if amount_ratio >= 10.0:
            indicators.append(BehaviouralAnomalyIndicator(
                feature_id="AMOUNT_WHALE_SPIKE",
                feature_name="Extreme Amount Outlier",
                category="AMOUNT",
                severity="CRITICAL",
                impact_points=38.0,
                observed_value=f"₹{amt:,.2f} ({amount_ratio:.1f}x baseline)",
                baseline_value=f"₹{user_avg:,.2f} (σ=₹{user_std:,.2f})",
                explanation=(
                    f"Payment amount of ₹{amt:,.2f} is {amount_ratio:.1f}x higher than customer's established "
                    f"mean (₹{user_avg:,.2f}), representing an extreme statistical deviation (z={z_score:.1f})."
                ),
                review_recommendation="Temporarily hold transaction; require step-up out-of-band biometric authentication.",
            ))
        elif amount_ratio >= 4.0 or z_score >= 3.0:
            indicators.append(BehaviouralAnomalyIndicator(
                feature_id="AMOUNT_SIGNIFICANT_SPIKE",
                feature_name="Significant Amount Elevation",
                category="AMOUNT",
                severity="HIGH",
                impact_points=24.0,
                observed_value=f"₹{amt:,.2f} ({amount_ratio:.1f}x baseline)",
                baseline_value=f"₹{user_avg:,.2f}",
                explanation=(
                    f"Transaction value of ₹{amt:,.2f} is {amount_ratio:.1f}x customer's historical average. "
                    "Noticeable divergence from routine grocery or retail payments."
                ),
                review_recommendation="Verify payee identity and request 2FA confirmation.",
            ))
        elif amount_ratio >= 2.5:
            indicators.append(BehaviouralAnomalyIndicator(
                feature_id="AMOUNT_MILD_ELEVATION",
                feature_name="Mild Amount Variance",
                category="AMOUNT",
                severity="MEDIUM",
                impact_points=12.0,
                observed_value=f"₹{amt:,.2f}",
                baseline_value=f"₹{user_avg:,.2f}",
                explanation=f"Payment value is {amount_ratio:.1f}x higher than typical baseline spending.",
                review_recommendation="Permit with inline risk banner in banking application.",
            ))

        # ------------------------------------------------------------------
        # FEATURE 2: Transaction Frequency Deviations
        # ------------------------------------------------------------------
        # Trailing 15m rate scaled to 24h daily rate
        if "velocity_15m" in transaction:
            recent_15m = int(float(transaction["velocity_15m"]))
        elif transaction.get("time_since_last_sec") is not None and float(transaction["time_since_last_sec"]) >= 900.0:
            recent_15m = 1
        else:
            recent_15m = user_baseline.recent_15m_count + 1  # Including current

        inferred_hourly_rate = recent_15m * 4.0
        daily_freq_base = max(0.5, user_baseline.daily_frequency_mean)
        freq_ratio = inferred_hourly_rate / daily_freq_base

        if recent_15m >= 6 or freq_ratio >= 8.0:
            indicators.append(BehaviouralAnomalyIndicator(
                feature_id="FREQ_CRITICAL_DEVIATION",
                feature_name="Critical Frequency Burst",
                category="FREQUENCY",
                severity="CRITICAL",
                impact_points=35.0,
                observed_value=f"{recent_15m} txs / 15m ({freq_ratio:.1f}x daily cadence)",
                baseline_value=f"{daily_freq_base:.1f} txs / day",
                explanation=(
                    f"Observed {recent_15m} transactions in 15 minutes, representing a {freq_ratio:.1f}x frequency surge "
                    f"over customer normal cadence ({daily_freq_base:.1f} payments/day). Characteristic of botnet account drains."
                ),
                review_recommendation="Freeze rapid egress queue and trigger velocity threshold cool-off.",
            ))
        elif recent_15m >= 4 or freq_ratio >= 4.0:
            indicators.append(BehaviouralAnomalyIndicator(
                feature_id="FREQ_ELEVATED_VELOCITY",
                feature_name="Elevated Velocity Deviation",
                category="FREQUENCY",
                severity="HIGH",
                impact_points=20.0,
                observed_value=f"{recent_15m} txs / 15m",
                baseline_value=f"{daily_freq_base:.1f} txs / day",
                explanation=f"Payment velocity ({recent_15m} in trailing 15 min) significantly exceeds normal daily rate.",
                review_recommendation="Step up authentication before allowing subsequent transfers.",
            ))

        # ------------------------------------------------------------------
        # FEATURE 4: New Recipient Patterns
        # ------------------------------------------------------------------
        if transaction.get("is_new_recipient") is not None:
            is_new_recipient = bool(transaction.get("is_new_recipient"))
        else:
            is_known_rec = receiver_vpa in user_baseline.known_recipients
            is_new_recipient = not is_known_rec and (user_baseline.total_prior_transactions > 0 or len(user_baseline.known_recipients) > 0)

        if is_new_recipient:
            # Check if paired with a high amount
            if amount_ratio >= 3.0:
                indicators.append(BehaviouralAnomalyIndicator(
                    feature_id="RECIPIENT_NOVEL_LARGE_TRANSFER",
                    feature_name="High-Value Transfer to New Payee",
                    category="RECIPIENT",
                    severity="HIGH",
                    impact_points=26.0,
                    observed_value=f"New Payee: '{receiver_vpa}', Amount: ₹{amt:,.2f}",
                    baseline_value=f"{len(user_baseline.known_recipients)} verified payees",
                    explanation=(
                        f"First transfer ever to beneficiary '{receiver_vpa}', coupled with an elevated amount "
                        f"(₹{amt:,.2f}, {amount_ratio:.1f}x baseline). Common social engineering/phishing risk indicator."
                    ),
                    review_recommendation="Enforce beneficiary addition cool-off and OTP challenge.",
                ))
            else:
                indicators.append(BehaviouralAnomalyIndicator(
                    feature_id="RECIPIENT_FIRST_TIME",
                    feature_name="First-Time Beneficiary",
                    category="RECIPIENT",
                    severity="LOW",
                    impact_points=8.0,
                    observed_value=receiver_vpa,
                    baseline_value=f"{len(user_baseline.known_recipients)} previous payees",
                    explanation=f"First recorded transfer to payee VPA '{receiver_vpa}'.",
                    review_recommendation="Standard review; monitor recipient for subsequent velocity.",
                ))

        # ------------------------------------------------------------------
        # FEATURE 5: New Device Patterns & Device Hopping
        # ------------------------------------------------------------------
        known_devs = user_baseline.known_devices
        if transaction.get("is_new_device") is not None:
            is_new_dev = bool(transaction.get("is_new_device"))
        else:
            is_new_dev = (
                (len(known_devs) > 0 and device_id not in known_devs) or
                ("NEW" in device_id.upper())
            )

        if is_new_dev:
            # Check rapid device hopping (new device within 300s of prior transaction)
            if user_baseline.seconds_since_last_tx is not None and user_baseline.seconds_since_last_tx <= 300.0:
                indicators.append(BehaviouralAnomalyIndicator(
                    feature_id="DEVICE_RAPID_SWITCHING",
                    feature_name="Rapid Device Switching / SIM Swap",
                    category="DEVICE",
                    severity="CRITICAL",
                    impact_points=32.0,
                    observed_value=f"Hardware '{device_id}' ({int(user_baseline.seconds_since_last_tx)}s after prior tx)",
                    baseline_value=f"Known devices: {list(known_devs)}",
                    explanation=(
                        f"Transaction from unrecognised hardware '{device_id}' initiated only "
                        f"{int(user_baseline.seconds_since_last_tx)}s after a transaction from a different device. "
                        "High probability of credential takeover, session hijacking, or SIM swap."
                    ),
                    review_recommendation="Halt session immediately; verify SIM binding and device telemetry.",
                ))
            else:
                indicators.append(BehaviouralAnomalyIndicator(
                    feature_id="DEVICE_UNRECOGNISED_SIGNATURE",
                    feature_name="Unrecognised Device Hardware",
                    category="DEVICE",
                    severity="HIGH",
                    impact_points=22.0,
                    observed_value=device_id,
                    baseline_value=f"{len(known_devs)} trusted devices",
                    explanation=f"Payment initiated on hardware signature '{device_id}' never previously verified for this user.",
                    review_recommendation="Request hardware device re-registration via SMS OTP.",
                ))

        # ------------------------------------------------------------------
        # FEATURE 6: Rapid Transaction Sequences (Sub-60s & Micro-Probing)
        # ------------------------------------------------------------------
        time_since = transaction.get("time_since_last_sec")
        if time_since is None:
            time_since = transaction.get("time_since_last_tx")
            if time_since is not None:
                time_since = float(time_since) * 3600.0
            else:
                time_since = user_baseline.seconds_since_last_tx

        velocity_15m = transaction.get("velocity_15m")
        if velocity_15m is None:
            velocity_15m = float(user_baseline.recent_15m_count + 1)
        else:
            velocity_15m = float(velocity_15m)

        is_sub_60s = False
        if time_since is not None:
            if float(time_since) < 60.0 and (user_baseline.recent_60s_count >= 1 or velocity_15m > 1.0):
                is_sub_60s = True
        elif user_baseline.recent_60s_count >= 2:
            is_sub_60s = True

        if is_sub_60s:
            recent_count = max(2, user_baseline.recent_60s_count + 1)
            indicators.append(BehaviouralAnomalyIndicator(
                feature_id="SEQUENCE_SUB_60S_BURST",
                feature_name="Ultra-Rapid Transaction Sequence",
                category="SEQUENCE",
                severity="HIGH",
                impact_points=28.0,
                observed_value=f"{recent_count} transactions in <60 seconds",
                baseline_value="Human pacing (>60s spacing)",
                explanation=(
                    f"Rapid payment sequence: {recent_count} transfers initiated in under 60 seconds. "
                    "Exceeds physiological manual entry speeds; indicates automated API scripting."
                ),
                review_recommendation="Enforce mandatory rate limiting and CAPTCHA challenge.",
            ))

        # Micro-probing pattern: Previous transaction was tiny (< ₹50) and current is large (>= ₹10,000)
        if (
            user_baseline.seconds_since_last_tx is not None
            and user_baseline.seconds_since_last_tx <= 600.0  # within 10 minutes
            and user_baseline.min_amount <= 50.0
            and amt >= 10000.0
        ):
            indicators.append(BehaviouralAnomalyIndicator(
                feature_id="SEQUENCE_MICRO_PROBE_DRAIN",
                feature_name="Micro-Probe Followed by Account Drain",
                category="SEQUENCE",
                severity="CRITICAL",
                impact_points=34.0,
                observed_value=f"₹{amt:,.2f} following ₹{user_baseline.min_amount:,.2f} test in {int(user_baseline.seconds_since_last_tx)}s",
                baseline_value="Consistent transaction sizing",
                explanation=(
                    f"Micro-probing sequence detected: A nominal test authorization (₹{user_baseline.min_amount:.2f}) "
                    f"was followed within {int(user_baseline.seconds_since_last_tx)}s by a large transfer of ₹{amt:,.2f}. "
                    "Classic signature of carders or fraudsters testing balance limits."
                ),
                review_recommendation="Halt transaction and flag account for urgent SOC investigation.",
            ))

        # ------------------------------------------------------------------
        # FEATURE 7: Suspicious Repeated Interactions (Pair Velocity & Mule Loops)
        # ------------------------------------------------------------------
        prior_pair_count = user_baseline.recipient_interaction_counts.get(receiver_vpa, 0)
        
        # Check repeated rapid transfers to the same recipient in current sequence
        if prior_pair_count >= 3 and recent_15m >= 3:
            indicators.append(BehaviouralAnomalyIndicator(
                feature_id="PAIR_REPEATED_HIGH_VELOCITY",
                feature_name="Repeated Pair Rapid Interaction",
                category="PAIR_INTERACTION",
                severity="HIGH",
                impact_points=26.0,
                observed_value=f"{prior_pair_count + 1} transfers to '{receiver_vpa}' ({recent_15m} in 15m)",
                baseline_value="Dispersed everyday transactions",
                explanation=(
                    f"Repeated targeted payments: {prior_pair_count + 1} transfers sent to beneficiary '{receiver_vpa}', "
                    "concentrated in a rapid session. Characteristic of smurfing or mule account loading."
                ),
                review_recommendation="Review relationship between sender and receiver; inspect counterparty risk history.",
            ))
        elif "MULE" in receiver_vpa.upper() or "CRYPTO" in receiver_vpa.upper() or "COLLECT" in receiver_vpa.upper():
            if prior_pair_count >= 1:
                indicators.append(BehaviouralAnomalyIndicator(
                    feature_id="PAIR_REPEATED_HIGH_RISK_COUNTERPARTY",
                    feature_name="Repeated Transfers to High-Risk Counterparty",
                    category="PAIR_INTERACTION",
                    severity="HIGH",
                    impact_points=22.0,
                    observed_value=f"Repeated payee: '{receiver_vpa}' ({prior_pair_count + 1} times)",
                    baseline_value="Legitimate merchant/P2P counterparties",
                    explanation=f"Repeated transactions directed towards flagged/high-risk counterparty handle '{receiver_vpa}'.",
                    review_recommendation="Review counterparty account network in AML graph.",
                ))

        # ------------------------------------------------------------------
        # Compute Composite Results
        # ------------------------------------------------------------------
        total_penalty = sum(ind.impact_points for ind in indicators)
        total_penalty = float(np.clip(total_penalty, 0.0, 100.0))

        severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        highest_sev: SeverityLevel = "LOW"
        highest_rank = 0

        for ind in indicators:
            r = severity_rank.get(ind.severity, 1)
            if r > highest_rank:
                highest_rank = r
                highest_sev = ind.severity

        primary_factor = indicators[0].feature_id if indicators else "NORMAL_BEHAVIOUR"

        return BehaviouralAnalysisResult(
            sender_upi=sender_vpa,
            receiver_upi=receiver_vpa,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            baseline=user_baseline,
            indicators=indicators,
            total_penalty_points=total_penalty,
            highest_severity=highest_sev,
            is_behavioural_anomaly=len(indicators) > 0 and total_penalty >= 20.0,
            primary_factor=primary_factor,
        )


# Singleton instance helper
_detector_instance: BehaviouralAnomalyDetector | None = None


def get_behavioural_detector() -> BehaviouralAnomalyDetector:
    """Returns or initialises the singleton BehaviouralAnomalyDetector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = BehaviouralAnomalyDetector()
    return _detector_instance
