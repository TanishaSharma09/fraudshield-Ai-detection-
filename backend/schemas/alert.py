"""FraudShield AI - Fraud Alert Schemas.

Pydantic models for managing actionable high-risk alerts and analyst review workflows.
"""

from typing import Literal
from pydantic import BaseModel, Field
from backend.schemas.transaction import FeatureExplanation

AlertSeverity = Literal["MEDIUM", "HIGH", "CRITICAL", "Medium", "High", "Critical"]
AlertStatus = Literal["PENDING", "REVIEWED", "APPROVED", "BLOCKED", "DISMISSED", "Pending", "Reviewed", "Approved", "Blocked", "Dismissed"]


class AlertActionRequest(BaseModel):
    """Analyst action to resolve or update a flagged alert."""
    action: Literal[
        "APPROVE", "BLOCK", "DISMISS", "REVIEW", "REVIEWED",
        "approve", "block", "dismiss", "review", "reviewed"
    ] = Field(
        ..., description="Decision taken by the security analyst (REVIEWED, APPROVE, BLOCK, DISMISS)"
    )
    notes: str | None = Field(default=None, max_length=500, description="Optional justification or investigation notes")
    reviewed_by: str = Field(default="SOC-Analyst-1", description="Analyst identifier")


class FraudAlertResponse(BaseModel):
    """Complete fraud alert representation returned by the API."""
    id: int
    alert_id: str
    tx_id: str
    amount: float | None = None
    sender_upi: str | None = None
    receiver_upi: str | None = None
    channel: str | None = None
    location_city: str | None = None
    risk_score: float | None = None
    risk_category: str | None = None
    tx_timestamp: str | None = None
    device_id: str | None = None
    tx_status: str | None = None
    severity: str
    primary_reason: str
    explanations: list[FeatureExplanation] = []
    status: str
    reviewed_by: str | None = None
    analyst_notes: str | None = None
    created_at: str
    updated_at: str


class AlertListResponse(BaseModel):
    """Paginated list of fraud alerts."""
    total: int
    limit: int
    offset: int
    alerts: list[FraudAlertResponse]
