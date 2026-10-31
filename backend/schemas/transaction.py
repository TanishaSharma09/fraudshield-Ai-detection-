"""FraudShield AI - Transaction Schemas.

Pydantic models for incoming transaction validation, feature payloads,
risk evaluation outputs, persistence models, and ML prediction responses.
"""

import math
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

RiskTier = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL", "Low risk", "Medium risk", "High risk"]
TransactionStatus = Literal[
    "APPROVED", "FLAGGED", "BLOCKED",
    "APPROVE", "STEP_UP_AUTHENTICATION", "HOLD_FOR_REVIEW"
]
PaymentChannel = Literal["UPI_APP", "QR_CODE", "COLLECT_REQUEST", "INTENT_FLOW"]

UPI_REGEX = re.compile(r"^[\w\.\-]+@[\w\-]+$")


class TransactionBase(BaseModel):
    """Shared fields for UPI transactions."""
    sender_upi: str = Field(..., examples=["arjun.sharma@okaxis"], description="Sender UPI Virtual Payment Address (VPA)")
    receiver_upi: str = Field(..., examples=["merchant.supermarket@icici"], description="Receiver UPI VPA")
    amount: float = Field(..., gt=0, examples=[2500.0], description="Transaction amount in INR")
    channel: PaymentChannel = Field(default="UPI_APP", description="Payment initiation channel")
    device_id: str = Field(default="DEV-XIAOMI-12", examples=["DEV-XIAOMI-12"], description="Client device hardware/app fingerprint")
    ip_address: str = Field(default="127.0.0.1", examples=["49.207.180.12"], description="Originating IPv4/IPv6 address")
    location_city: str = Field(default="Mumbai", examples=["Mumbai"], description="City where transaction was initiated")
    timestamp: str | None = Field(
        default=None,
        examples=["2026-10-30T14:35:00Z"],
        description="ISO-8601 formatted transaction timestamp (defaults to current UTC time)",
    )

    # Optional behavioral signals (used for realistic simulation and feature engineering)
    velocity_15m: float = Field(default=1.0, ge=1.0, description="Transactions initiated by sender in trailing 15 min")
    time_since_last_sec: float = Field(default=3600.0, ge=0.0, description="Time elapsed since sender's previous transaction in seconds")
    is_new_recipient: int = Field(default=0, ge=0, le=1, description="1 if receiver VPA has never been paid by sender, 0 otherwise")
    is_new_device: int = Field(default=0, ge=0, le=1, description="1 if device ID is not in user's known devices, 0 otherwise")

    @field_validator("sender_upi", "receiver_upi")
    @classmethod
    def validate_upi_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not UPI_REGEX.match(v):
            raise ValueError(f"Invalid UPI format '{v}'. Expected format: username@provider (e.g., arjun@okaxis)")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v) or v <= 0:
            raise ValueError("Amount must be a valid finite number greater than zero.")
        if v > 1_000_000:
            raise ValueError("Amount exceeds single UPI transfer limit (₹10,00,000).")
        return round(v, 2)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        try:
            clean_ts = v.replace("Z", "+00:00")
            parsed_dt = datetime.fromisoformat(clean_ts)
        except (ValueError, TypeError):
            raise ValueError(
                f"Invalid timestamp format '{v}'. Must be a valid ISO-8601 string (e.g., 2026-10-31T14:30:00Z)."
            )

        if parsed_dt.tzinfo is None:
            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        # Disallow future timestamps (with 15 min leeway for clock drift)
        if parsed_dt > now + timedelta(minutes=15):
            raise ValueError(f"Transaction timestamp '{v}' cannot be set in the future.")

        # Disallow unreasonable historical timestamps
        if parsed_dt.year < 2020:
            raise ValueError(f"Transaction timestamp year {parsed_dt.year} is too far in the past for active UPI processing.")

        return v


class TransactionCreate(TransactionBase):
    """Incoming request to evaluate, score, and persist a transaction."""
    tx_id: str | None = Field(default=None, description="Optional custom transaction identifier (auto-generated if omitted)")


class FeatureExplanation(BaseModel):
    """Transparent factor attribution contributing to the risk score."""
    factor_name: str
    weight: float = Field(..., description="Contribution weight 0.0 to 1.0")
    severity: str = Field(..., description="Severity category (NORMAL, SUSPICIOUS, HIGHLY_ANOMALOUS)")
    description: str


class TransactionEvaluationResponse(BaseModel):
    """Evaluation result returned immediately to client upon transaction submission."""
    tx_id: str
    sender_upi: str
    receiver_upi: str
    amount: float
    channel: str = "UPI_APP"
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_tier: str
    risk_category: str
    status: str
    action_recommendation: str
    primary_factor: str
    is_flagged: bool
    explanations: list[FeatureExplanation]
    relevant_risk_indicators: list[str] = []
    alert_id: str | None = None
    evaluated_at: str


class TransactionRecord(BaseModel):
    """Stored transaction representation in database."""
    id: int
    tx_id: str
    sender_upi: str
    receiver_upi: str
    amount: float
    channel: str
    device_id: str
    ip_address: str
    location_city: str
    timestamp: str
    risk_score: float
    risk_tier: str
    status: str
    primary_factor: str | None = None
    is_flagged: int
    created_at: str


class TransactionListResponse(BaseModel):
    """Paginated list of transactions."""
    total: int
    limit: int
    offset: int
    transactions: list[TransactionRecord]


class TransactionDetailResponse(BaseModel):
    """Complete transaction record enriched with alert and explanation data."""
    transaction: TransactionRecord
    alert: dict[str, Any] | None = None
    explanations: list[FeatureExplanation] = []
    prediction: dict[str, Any] | None = None


class PredictRequest(TransactionBase):
    """Payload for direct ML prediction endpoint with optional user profile override."""
    tx_id: str | None = Field(default=None, description="Optional transaction identifier")
    user_profile: dict[str, Any] | None = Field(
        default=None,
        description="Optional customer historical profile override (avg_amount, std_amount, known_devices, etc.)"
    )


class PredictResponse(BaseModel):
    """Explicit machine learning prediction and scoring response."""
    transaction_id: str
    is_anomaly: bool
    prediction_label: str
    raw_decision_score: float
    anomaly_score: float
    risk_score: float
    risk_tier: str
    risk_category: str
    action_recommendation: str
    primary_factor: str
    relevant_risk_indicators: list[str]
    explanations: list[FeatureExplanation]
    model_version: str
    evaluated_at: str
