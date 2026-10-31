"""FraudShield AI - Prediction API Route.

Dedicated endpoint for direct machine learning inference and risk scoring:
- Executes unsupervised Scikit-Learn Isolation Forest anomaly evaluation.
- Applies calibrated risk scoring engine (0-100) and 3 documented risk categories.
- Generates transparent feature-based explanation breakdown.
- Requires ANALYST or ADMIN role.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.schemas.transaction import PredictRequest, PredictResponse, FeatureExplanation
from backend.services.risk_scoring_service import get_risk_scoring_engine
from ml_model.explainability.explainer import get_explainer
from backend.api.deps import require_analyst_or_admin

router = APIRouter(tags=["Machine Learning Inference"])


@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct Machine Learning Fraud Prediction",
    description="Scores a transaction in real-time using Isolation Forest and generates transparent explainability factors. Requires ANALYST or ADMIN role.",
)
def predict_transaction(
    payload: PredictRequest,
    current_user: dict = Depends(require_analyst_or_admin),
) -> PredictResponse:
    """Evaluates payment with the Isolation Forest model and returns risk scores and explanations."""
    try:
        scoring_engine = get_risk_scoring_engine()
        explainer = get_explainer()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Machine learning model is not available: {str(e)}. Please run model training first.",
        )

    # Convert Pydantic request to dictionary
    tx_dict = payload.model_dump()
    user_profile = tx_dict.pop("user_profile", None)

    try:
        # 1. Run calibrated scoring
        scoring_result = scoring_engine.evaluate(tx_dict, user_profile)

        # 2. Run transparent explanation
        explainable_alert = explainer.explain(tx_dict, user_profile, scoring_result)

        # 3. Format explanations for response model
        explanations = [
            FeatureExplanation(
                factor_name=getattr(factor, "factor_name", "UNKNOWN"),
                weight=float(getattr(factor, "impact_weight", getattr(factor, "weight", 0.0))),
                severity=str(getattr(factor, "severity", "NORMAL")),
                description=str(getattr(factor, "explanation", getattr(factor, "description", ""))),
            )
            for factor in explainable_alert.contributing_factors
        ]

        anomaly_output = scoring_result.anomaly_prediction

        return PredictResponse(
            transaction_id=scoring_result.transaction_id,
            is_anomaly=anomaly_output.is_anomaly,
            prediction_label="SUSPICIOUS_ANOMALY" if anomaly_output.is_anomaly else "NORMAL",
            raw_decision_score=round(anomaly_output.raw_decision_score, 4),
            anomaly_score=round(anomaly_output.model_risk_contribution, 2),
            risk_score=scoring_result.risk_score,
            risk_tier=scoring_result.risk_category.upper().replace(" RISK", ""),
            risk_category=scoring_result.risk_category,
            action_recommendation=scoring_result.action_recommendation,
            primary_factor=explainable_alert.primary_reason,
            relevant_risk_indicators=scoring_result.relevant_risk_indicators,
            explanations=explanations,
            model_version=anomaly_output.model_version,
            evaluated_at=scoring_result.evaluated_at,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Data processing error during inference: {str(ve)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference pipeline execution error: {str(exc)}",
        )
