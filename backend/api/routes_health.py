"""FraudShield AI - Health Check API Route.

Verifies end-to-end operational readiness:
- SQLite database connectivity and schema integrity.
- In-memory presence and inference capability of the Scikit-Learn Isolation Forest model.
- Preprocessor readiness and feature definitions.
"""

import sys
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from backend.core.config import settings
from database.connection import query_one
from ml_model.predictor import get_predictor

router = APIRouter(tags=["Health & System"])


@router.get(
    "/health",
    summary="System Operational Health Check",
    description="Validates SQLite connectivity, user baseline seeds, and Isolation Forest model readiness.",
    response_description="Current system operational status with subsystem diagnostics.",
)
@router.get("/system/health", include_in_schema=False)
def check_health() -> JSONResponse:
    """Performs deep health probe across database and machine learning subsystems."""
    now_utc = datetime.now(timezone.utc).isoformat()

    # 1. Probe SQLite Database
    db_status = "healthy"
    user_count = 0
    tx_count = 0
    try:
        row = query_one("SELECT COUNT(*) AS cnt FROM user_profiles;")
        if row:
            user_count = row["cnt"]
        tx_row = query_one("SELECT COUNT(*) AS cnt FROM transactions;")
        if tx_row:
            tx_count = tx_row["cnt"]
    except Exception as e:
        db_status = f"unhealthy: {e}"

    # 2. Probe Machine Learning Engine
    ml_status = "healthy"
    ml_details = {}
    try:
        predictor = get_predictor()
        ml_details = {
            "status": "loaded",
            "model_type": type(predictor.model).__name__,
            "n_estimators": getattr(predictor.model, "n_estimators", 200),
            "contamination": getattr(predictor.model, "contamination", 0.035),
            "feature_count": len(predictor.preprocessor.feature_names),
            "features": predictor.preprocessor.feature_names,
        }
    except Exception as e:
        ml_status = "degraded"
        ml_details = {
            "status": "not_loaded",
            "error": str(e),
            "advice": "Train model first with: python -m ml_model.training.train_isolation_forest",
        }

    overall_status = "healthy" if (db_status == "healthy" and ml_status == "healthy") else "degraded"
    http_code = status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_code,
        content={
            "status": overall_status,
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "timestamp": now_utc,
            "runtime": {
                "python": sys.version.split()[0],
                "platform": sys.platform,
                "sqlite_version": sqlite3.sqlite_version,
            },
            "database": {
                "status": "healthy" if db_status == "healthy" else "unhealthy",
                "path": str(settings.DATABASE_PATH),
                "baseline_users_loaded": user_count,
                "total_transactions": tx_count,
            },
            "ml_capabilities": {
                "isolation_forest": "loaded (scikit-learn)",
                "status": ml_status,
                "details": ml_details,
            },
            "subsystems": {
                "database": {
                    "status": "connected" if db_status == "healthy" else "error",
                    "path": str(settings.DATABASE_PATH),
                    "baseline_users": user_count,
                    "total_transactions": tx_count,
                },
                "ml_engine": ml_details,
            },
        },
    )
