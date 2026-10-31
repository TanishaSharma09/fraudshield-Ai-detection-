"""FraudShield AI - Analytics & Dashboard Schemas.

Pydantic models for aggregating system-wide metrics, risk distributions,
hourly fraud trends, amount distributions, frequency velocity,
fraud-labeled comparisons, model evaluation metrics, and CSV report exports.
"""

from pydantic import BaseModel, Field


class RiskDistribution(BaseModel):
    """Counts grouped by risk tier."""
    low: int = Field(default=0, description="Score 0 - 39.99")
    medium: int = Field(default=0, description="Score 40 - 69.99")
    high: int = Field(default=0, description="Score 70 - 89.99")
    critical: int = Field(default=0, description="Score 90 - 100")


class HourlyTrendPoint(BaseModel):
    """Aggregate counts for a single hour or time interval."""
    hour_label: str
    total_count: int
    flagged_count: int
    total_volume: float = 0.0
    flagged_volume: float = 0.0


class TopRiskVector(BaseModel):
    """Summary of common fraud indicators detected."""
    factor_name: str
    occurrence_count: int
    average_impact: float


class AmountDistributionBracket(BaseModel):
    """Histogram bracket for transaction amounts."""
    bracket_label: str
    min_amount: float
    max_amount: float | None = None
    total_count: int
    flagged_count: int
    total_volume: float = 0.0


class FrequencyDistributionPoint(BaseModel):
    """Velocity frequency bracket of transactions in rolling interval."""
    frequency_label: str
    count: int
    percentage: float
    flagged_count: int


class ChannelVolumePoint(BaseModel):
    """Transaction volume and anomaly breakdown by payment channel."""
    channel: str
    transaction_count: int
    total_volume: float
    flagged_count: int


class FraudVsLegitMetrics(BaseModel):
    """Comparison of confirmed fraud vs legitimate transactions, distinguishing model anomalies."""
    has_ground_truth_labels: bool = True
    ground_truth_fraud: int = 0
    ground_truth_legitimate: int = 0
    operational_confirmed_fraud: int = 0
    operational_confirmed_legit: int = 0
    operational_under_review: int = 0
    model_flagged_anomalies: int = 0
    anomaly_vs_fraud_explanation: str = Field(
        default=(
            "Distinction: An Isolation Forest anomaly represents an unsupervised statistical deviation "
            "(unusual velocity, device, or amount). Confirmed fraud requires verified chargeback labels or "
            "explicit SOC analyst blocking (BLOCKED status)."
        )
    )


class ModelEvaluationSummary(BaseModel):
    """Rigorous statistical performance metrics for the active ML model."""
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    false_negative_rate: float
    specificity: float
    balanced_accuracy: float
    roc_auc: float
    pr_auc: float
    confusion_matrix: dict[str, int]
    model_name: str = "IsolationForest"
    contamination: float = 0.035
    total_evaluated_samples: int = 6458


class AnalyticsOverview(BaseModel):
    """System-level operational metrics for dashboard KPI cards and interactive charts."""
    total_evaluated: int
    total_flagged: int
    fraud_rate_percentage: float
    avg_risk_score: float
    pending_alerts: int
    active_model_version: str
    distribution: RiskDistribution
    hourly_trends: list[HourlyTrendPoint]
    top_vectors: list[TopRiskVector]

    # Enhanced Analytics Module Extensions
    total_volume_inr: float = 0.0
    amount_distribution: list[AmountDistributionBracket] = []
    frequency_distribution: list[FrequencyDistributionPoint] = []
    channel_distribution: list[ChannelVolumePoint] = []
    fraud_vs_legit: FraudVsLegitMetrics | None = None
    model_metrics: ModelEvaluationSummary | None = None
    date_filter_applied: dict[str, str | None] = {}
    risk_filter_applied: str | None = None
