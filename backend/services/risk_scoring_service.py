"""FraudShield AI - Transaction Risk Scoring Engine.

Converts Scikit-Learn Isolation Forest anomaly outputs and transaction behavioral
signals into a calibrated, explainable 0–100 risk score with 3 documented risk categories:
- Low risk   (0.00 - 39.99): Normal everyday behavior, automated pass-through
- Medium risk(40.00 - 69.99): Moderate statistical variance or single mild anomaly, step-up MFA
- High risk  (70.00 - 100.0): Severe compound anomaly (velocity bursts, SIM swap, midnight drain), review/hold

Architectural Integrity:
- Model anomaly predictions are kept explicitly separate from rule-based risk indicators.
- Scores are never arbitrarily determined by transaction amount alone; instead, amounts
  are evaluated relative to the user's historical rolling baseline.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Literal
import numpy as np

from ml_model.predictor import FraudShieldPredictor, get_predictor
from ml_model.behavioural.anomaly_detector import (
    BehaviouralAnomalyDetector,
    get_behavioural_detector,
)

RiskCategory = Literal["Low risk", "Medium risk", "High risk"]
ActionRecommendation = Literal["APPROVE", "STEP_UP_AUTHENTICATION", "HOLD_FOR_REVIEW"]


@dataclass
class RiskIndicator:
    """Represents a specific behavioral risk signal contributing to the score."""
    code: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    description: str
    impact_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnomalyModelOutput:
    """Explicitly isolated machine learning model evaluation."""
    is_anomaly: bool
    raw_decision_score: float
    model_risk_contribution: float
    model_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TransactionScoringResult:
    """Complete, transparent evaluation output returned by the scoring engine."""
    transaction_id: str
    anomaly_prediction: AnomalyModelOutput
    risk_score: float
    risk_category: RiskCategory
    action_recommendation: ActionRecommendation
    relevant_risk_indicators: list[str]
    detailed_indicators: list[RiskIndicator]
    transaction_details: dict[str, Any]
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "anomaly_prediction": self.anomaly_prediction.to_dict(),
            "risk_score": self.risk_score,
            "risk_category": self.risk_category,
            "action_recommendation": self.action_recommendation,
            "relevant_risk_indicators": self.relevant_risk_indicators,
            "detailed_indicators": [ind.to_dict() for ind in self.detailed_indicators],
            "transaction_details": self.transaction_details,
            "evaluated_at": self.evaluated_at,
        }


class TransactionRiskScoringEngine:
    """Calibrated scoring service fusing unsupervised ML and domain behavioral signals."""

    def __init__(
        self,
        predictor: FraudShieldPredictor | None = None,
        behavioural_detector: BehaviouralAnomalyDetector | None = None,
    ) -> None:
        self.predictor = predictor or get_predictor()
        self.behavioural_detector = behavioural_detector or get_behavioural_detector()

    def evaluate(
        self,
        transaction: dict[str, Any],
        user_profile: dict[str, Any] | None = None,
    ) -> TransactionScoringResult:
        """Evaluates a digital payment transaction and computes a calibrated risk score.

        Args:
            transaction: Payment parameters (tx_id, amount, sender_upi, receiver_upi, channel, etc.)
            user_profile: Historical profile containing avg_amount, known_devices, etc.

        Returns:
            TransactionScoringResult containing isolated model output, composite score,
            3-tier risk category, and relevant indicators.
        """
        # Ensure transaction ID exists
        now_utc = datetime.now(timezone.utc)
        tx_id = str(transaction.get("tx_id") or f"UPI-{now_utc.strftime('%Y%m%d')}-{np.random.randint(100000, 999999)}")

        # 1. Independent Machine Learning Model Evaluation (Isolation Forest)
        ml_prediction = self.predictor.predict_single(transaction, user_profile)
        is_model_anomaly = bool(ml_prediction["is_anomaly"])
        raw_decision_score = float(ml_prediction["raw_decision_score"])
        model_risk_component = float(ml_prediction["risk_score"])

        model_output = AnomalyModelOutput(
            is_anomaly=is_model_anomaly,
            raw_decision_score=raw_decision_score,
            model_risk_contribution=model_risk_component,
            model_version="IsolationForest-v1.0",
        )

        # 2. Independent Transaction & Behavioral Signal Evaluation
        indicators, signal_penalty_points = self._extract_risk_signals(transaction, user_profile)

        # 3. Calibrated Score Fusion (70% ML Anomaly + 30% Domain Signals)
        # Note: If model detects severe anomaly and multiple signals fire, composite scales appropriately
        base_score = (0.70 * model_risk_component) + (0.30 * signal_penalty_points)

        # Calibration adjustments:
        # If model is normal and no severe signals exist, ensure score stays well in Low tier
        if not is_model_anomaly and signal_penalty_points <= 15.0:
            final_risk_score = min(base_score, 38.0)
        # If severe compound attack (e.g. velocity burst + new device + anomaly), ensure High tier
        elif (is_model_anomaly and signal_penalty_points >= 40.0) or signal_penalty_points >= 65.0:
            final_risk_score = max(base_score, 78.0)
        else:
            final_risk_score = base_score

        final_risk_score = float(round(np.clip(final_risk_score, 0.0, 100.0), 2))

        # 4. Three Risk Levels Assignment
        risk_category, action = self._determine_risk_category(final_risk_score)

        # 5. Extract Human-Readable Summary Descriptions
        relevant_indicators = [ind.description for ind in indicators]
        if not relevant_indicators:
            relevant_indicators = ["Transaction conforms to customer historical baseline and diurnal activity."]

        return TransactionScoringResult(
            transaction_id=tx_id,
            anomaly_prediction=model_output,
            risk_score=final_risk_score,
            risk_category=risk_category,
            action_recommendation=action,
            relevant_risk_indicators=relevant_indicators,
            detailed_indicators=indicators,
            transaction_details={
                "amount": float(transaction.get("amount", 0.0)),
                "sender_upi": transaction.get("sender_upi"),
                "receiver_upi": transaction.get("receiver_upi"),
                "channel": transaction.get("channel", "UPI_APP"),
                "device_id": transaction.get("device_id", "DEV-UNKNOWN"),
                "location_city": transaction.get("location_city", "Mumbai"),
                "timestamp": transaction.get("timestamp") or now_utc.isoformat(),
            },
            evaluated_at=now_utc.isoformat(),
        )

    def _extract_risk_signals(
        self,
        tx: dict[str, Any],
        user_profile: dict[str, Any] | None,
    ) -> tuple[list[RiskIndicator], float]:
        """Extracts deterministic behavioral signals without hardcoding amount alone."""
        indicators: list[RiskIndicator] = []
        total_points = 0.0

        profile = user_profile or {}
        user_avg = float(profile.get("avg_amount", 2500.0))
        amt = float(tx.get("amount", 0.0))
        channel = str(tx.get("channel", "UPI_APP")).upper()
        device = str(tx.get("device_id", "DEV-UNKNOWN"))
        receiver = str(tx.get("receiver_upi", "")).strip().lower()
        velocity = float(tx.get("velocity_15m", 1.0))

        known_devices = profile.get("known_devices", [])
        known_recipients = profile.get("known_recipients", [])

        # Parse timestamp for temporal checks
        ts_val = tx.get("timestamp")
        try:
            dt = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00")) if ts_val else datetime.now(timezone.utc)
        except Exception:
            dt = datetime.now(timezone.utc)
        hour = dt.hour

        # Signal 1: Amount Ratio relative to Personal Historical Baseline
        amount_ratio = amt / max(10.0, user_avg)
        if amount_ratio >= 8.0:
            pts = 35.0
            indicators.append(RiskIndicator(
                code="AMOUNT_SPIKE_EXTREME",
                severity="HIGH",
                description=f"Transaction value (₹{amt:,.2f}) is {amount_ratio:.1f}x higher than customer's average (₹{user_avg:,.2f}).",
                impact_score=pts,
            ))
            total_points += pts
        elif amount_ratio >= 4.0:
            pts = 20.0
            indicators.append(RiskIndicator(
                code="AMOUNT_SPIKE_MODERATE",
                severity="MEDIUM",
                description=f"Transaction value (₹{amt:,.2f}) is {amount_ratio:.1f}x higher than customer's average (₹{user_avg:,.2f}).",
                impact_score=pts,
            ))
            total_points += pts
        elif amount_ratio >= 2.5:
            pts = 10.0
            indicators.append(RiskIndicator(
                code="AMOUNT_SPIKE_MILD",
                severity="LOW",
                description=f"Transaction value (₹{amt:,.2f}) is {amount_ratio:.1f}x customer's baseline average.",
                impact_score=pts,
            ))
            total_points += pts

        # Signal 2: 15-Minute Transaction Velocity Spikes
        if velocity >= 6.0:
            pts = 40.0
            indicators.append(RiskIndicator(
                code="VELOCITY_BURST_CRITICAL",
                severity="HIGH",
                description=f"Critical transaction frequency: {int(velocity)} payments initiated within 15 minutes (rapid account drain pattern).",
                impact_score=pts,
            ))
            total_points += pts
        elif velocity >= 4.0:
            pts = 25.0
            indicators.append(RiskIndicator(
                code="VELOCITY_BURST_ELEVATED",
                severity="MEDIUM",
                description=f"Elevated payment frequency: {int(velocity)} transactions in trailing 15 minutes.",
                impact_score=pts,
            ))
            total_points += pts

        # Signal 3: Unrecognised Hardware Device Signature
        is_new_device = (len(known_devices) > 0 and device not in known_devices) or ("NEW" in device.upper())
        if is_new_device:
            pts = 25.0
            indicators.append(RiskIndicator(
                code="NEW_DEVICE_HARDWARE_MISMATCH",
                severity="HIGH",
                description=f"Transaction initiated from an unrecognised hardware device ID ('{device}').",
                impact_score=pts,
            ))
            total_points += pts

        # Signal 4: Off-Peak Nocturnal Transfer (01:00 AM – 04:59 AM)
        if hour in [1, 2, 3, 4]:
            pts = 20.0
            indicators.append(RiskIndicator(
                code="OFF_PEAK_SLEEP_HOURS",
                severity="MEDIUM",
                description=f"Transaction executed at {hour:02d}:{dt.minute:02d} UTC/IST during low-traffic off-peak hours.",
                impact_score=pts,
            ))
            total_points += pts

        # Signal 5: Collect Request Phishing Risk
        if channel == "COLLECT_REQUEST":
            pts = 20.0
            indicators.append(RiskIndicator(
                code="COLLECT_REQUEST_CHANNEL",
                severity="MEDIUM",
                description="Initiated via UPI Collect Request (frequent phishing vector for fraudulent fund draws).",
                impact_score=pts,
            ))
            total_points += pts

        # Signal 6: First-Time Payee VPA
        is_new_recipient = (len(known_recipients) > 0 and receiver not in known_recipients)
        if is_new_recipient:
            pts = 10.0
            indicators.append(RiskIndicator(
                code="NEW_BENEFICIARY_VPA",
                severity="LOW",
                description=f"First-time transfer to beneficiary VPA '{receiver}'.",
                impact_score=pts,
            ))
            total_points += pts

        # ------------------------------------------------------------------
        # Enhanced Behavioral Dimensions Integration
        # (Rapid sequences, micro-probing, repeated pair interactions, device hopping)
        # ------------------------------------------------------------------
        try:
            b_res = self.behavioural_detector.analyze(tx, user_baseline=None)
            for b_ind in b_res.indicators:
                # Avoid duplicating existing primary signals already added above
                if b_ind.category in ["AMOUNT", "RECIPIENT", "DEVICE"] and any(i.code.startswith(b_ind.category) for i in indicators):
                    continue
                if b_ind.feature_id in ["FREQ_CRITICAL_DEVIATION", "FREQ_ELEVATED_VELOCITY"] and velocity >= 4.0:
                    continue

                sev_mapped: Literal["LOW", "MEDIUM", "HIGH"] = "HIGH" if b_ind.severity in ["HIGH", "CRITICAL"] else (
                    "MEDIUM" if b_ind.severity == "MEDIUM" else "LOW"
                )
                indicators.append(RiskIndicator(
                    code=b_ind.feature_id,
                    severity=sev_mapped,
                    description=b_ind.explanation,
                    impact_score=min(35.0, b_ind.impact_points * 0.7),
                ))
                total_points += min(35.0, b_ind.impact_points * 0.7)
        except Exception:
            pass  # Fall back cleanly to core signals without disruption

        # Bound additive signal score to 100 max
        total_points = float(np.clip(total_points, 0.0, 100.0))
        return indicators, total_points

        # Bound additive signal score to 100 max
        total_points = float(np.clip(total_points, 0.0, 100.0))
        return indicators, total_points

    @staticmethod
    def _determine_risk_category(risk_score: float) -> tuple[RiskCategory, ActionRecommendation]:
        """Categorises score into strictly 3 documented risk levels."""
        if risk_score < 40.0:
            return "Low risk", "APPROVE"
        elif risk_score < 70.0:
            return "Medium risk", "STEP_UP_AUTHENTICATION"
        else:
            return "High risk", "HOLD_FOR_REVIEW"


# Singleton instance helper
_engine_instance: TransactionRiskScoringEngine | None = None


def get_risk_scoring_engine() -> TransactionRiskScoringEngine:
    """Returns or initialises the singleton TransactionRiskScoringEngine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TransactionRiskScoringEngine()
    return _engine_instance
