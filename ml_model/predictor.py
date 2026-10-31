"""FraudShield AI - Reusable Production Inference & Prediction Engine.

Loads the trained Isolation Forest model, preprocessor, and calibration configuration
to score transactions in real time:
- Standardised prediction convention:
    * is_anomaly = True / 1 -> Suspicious Anomaly (Outlier)
    * is_anomaly = False / 0 -> Normal Legitimate Pattern
- Calibrated 0 to 100 Risk Score.
- Tier assignment: LOW (0–39.9), MEDIUM (40–69.9), HIGH (70–89.9), CRITICAL (90–100).
- Decision action recommendation: APPROVED, FLAGGED, or BLOCKED.

Important Notice:
Anomalous predictions indicate high statistical divergence from established baselines.
An anomaly flags elevated risk requiring step-up authentication or analyst inspection;
it is not definitive proof of criminal fraud.
"""

import json
from pathlib import Path
from typing import Any
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.core.config import settings
from ml_model.features.preprocessor import FraudShieldPreprocessor


class FraudShieldPredictor:
    """Production scoring engine for real-time and batch UPI anomaly evaluation."""

    def __init__(
        self,
        model_path: str | Path = settings.MODEL_PATH,
        preprocessor_path: str | Path = settings.SAVED_MODELS_DIR / "preprocessor.joblib",
        config_path: str | Path = settings.SAVED_MODELS_DIR / "model_config.json",
    ) -> None:
        self.model_path = Path(model_path)
        self.preprocessor_path = Path(preprocessor_path)
        self.config_path = Path(config_path)

        self._load_artifacts()

    def _load_artifacts(self) -> None:
        """Loads serialized model, preprocessor, and calibration settings."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Trained model not found at '{self.model_path.resolve()}'. "
                f"Please train the model first by running: python -m ml_model.training.train_isolation_forest"
            )

        self.model: IsolationForest = joblib.load(self.model_path)
        self.preprocessor = FraudShieldPreprocessor.load(self.preprocessor_path)

        # Default fallback calibration
        self.score_min = -0.35
        self.score_max = 0.25

        if self.config_path.exists():
            try:
                cfg = json.loads(self.config_path.read_text(encoding="utf-8"))
                calib = cfg.get("calibration", {})
                self.score_min = float(calib.get("score_min", self.score_min))
                self.score_max = float(calib.get("score_max", self.score_max))
            except Exception:
                pass

    def calculate_risk_score(self, decision_score: float) -> float:
        """Converts raw Isolation Forest decision score into calibrated 0-100 risk score."""
        clipped = np.clip(decision_score, self.score_min, self.score_max)
        normalized = (self.score_max - clipped) / (self.score_max - self.score_min + 1e-9)
        return float(np.round(np.clip(normalized * 100.0, 0.0, 100.0), 2))

    @staticmethod
    def get_risk_tier(risk_score: float) -> str:
        """Categorises numerical risk score into fintech severity tiers."""
        if risk_score <= settings.THRESHOLDS.LOW_MAX:
            return "LOW"
        elif risk_score <= settings.THRESHOLDS.MEDIUM_MAX:
            return "MEDIUM"
        elif risk_score <= settings.THRESHOLDS.HIGH_MAX:
            return "HIGH"
        else:
            return "CRITICAL"

    @staticmethod
    def get_action_status(risk_tier: str) -> str:
        """Assigns recommended decision status based on severity tier."""
        if risk_tier in ["LOW", "MEDIUM"]:
            return "APPROVED"
        elif risk_tier == "HIGH":
            return "FLAGGED"
        else:
            return "BLOCKED"

    def predict_single(
        self,
        tx_dict: dict[str, Any],
        user_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluates a single live payment event in real-time.

        Args:
            tx_dict: Dictionary containing incoming payment parameters.
            user_profile: User's historical profile data from SQLite.

        Returns:
            Dictionary with prediction results, risk scores, tier, and status.
        """
        # Transform raw transaction into feature vector with feature names
        features_2d = self.preprocessor.transform_single(tx_dict, user_profile)
        features_df = pd.DataFrame(features_2d, columns=self.preprocessor.feature_names)

        # Run Isolation Forest inference
        raw_pred = self.model.predict(features_df)[0]
        raw_score = float(self.model.decision_function(features_df)[0])

        # Standardise convention: 1 = anomaly/suspicious, 0 = normal
        is_anomaly = True if raw_pred == -1 else False

        risk_score = self.calculate_risk_score(raw_score)
        risk_tier = self.get_risk_tier(risk_score)
        status = self.get_action_status(risk_tier)

        # Primary risk factor identification
        primary_factor = "NORMAL_TRANSACTION"
        amt = float(tx_dict.get("amount", 0.0))
        user_avg = float((user_profile or {}).get("avg_amount", 2500.0))
        velocity = float(tx_dict.get("velocity_15m", 1.0))
        is_new_device = 1 if "NEW" in str(tx_dict.get("device_id", "")).upper() else 0

        if is_anomaly or risk_score >= 50.0:
            if amt / max(10.0, user_avg) >= 5.0:
                primary_factor = "UNUSUAL_AMOUNT_SPIKE"
            elif velocity >= 4.0:
                primary_factor = "HIGH_TRANSACTION_VELOCITY"
            elif is_new_device == 1:
                primary_factor = "UNRECOGNISED_DEVICE_LOGIN"
            elif str(tx_dict.get("channel", "")).upper() == "COLLECT_REQUEST":
                primary_factor = "SUSPICIOUS_COLLECT_REQUEST"
            else:
                primary_factor = "MULTIVARIATE_BEHAVIORAL_ANOMALY"

        return {
            "is_anomaly": is_anomaly,
            "prediction_label": "SUSPICIOUS_ANOMALY" if is_anomaly else "NORMAL",
            "risk_score": risk_score,
            "risk_tier": risk_tier,
            "status": status,
            "primary_factor": primary_factor,
            "raw_decision_score": round(raw_score, 4),
            "amount": amt,
            "sender_upi": tx_dict.get("sender_upi"),
            "receiver_upi": tx_dict.get("receiver_upi"),
        }

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Evaluates a batch of transactions and enriches DataFrame with prediction columns."""
        # Ensure input is transformed
        if "amount_scaled" not in df.columns:
            transformed_df = self.preprocessor.transform(df)
        else:
            transformed_df = df

        feature_matrix = transformed_df[self.preprocessor.feature_names]
        raw_preds = self.model.predict(feature_matrix)
        raw_scores = self.model.decision_function(feature_matrix)

        result_df = df.copy()
        result_df["is_anomaly"] = np.where(raw_preds == -1, 1, 0)
        result_df["raw_decision_score"] = np.round(raw_scores, 4)
        result_df["risk_score"] = [self.calculate_risk_score(s) for s in raw_scores]
        result_df["risk_tier"] = [self.get_risk_tier(rs) for rs in result_df["risk_score"]]
        result_df["action_status"] = [self.get_action_status(rt) for rt in result_df["risk_tier"]]

        return result_df


# Module-level singleton instance for zero-latency reuse
_predictor_instance: FraudShieldPredictor | None = None


def get_predictor() -> FraudShieldPredictor:
    """Returns or initialises the singleton FraudShieldPredictor instance."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = FraudShieldPredictor()
    return _predictor_instance


def evaluate_transaction(
    tx_dict: dict[str, Any],
    user_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience functional interface for scoring single transactions."""
    predictor = get_predictor()
    return predictor.predict_single(tx_dict, user_profile)
