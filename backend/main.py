"""FraudShield AI - FastAPI Application Gateway.

Entry point for real-time UPI fraud scoring, risk analytics, and alert management:
- Loads the Scikit-Learn Isolation Forest machine learning model and preprocessor.
- Configures modular REST routers for authentication, user management, transactions,
  predictions, alerts, analytics, and simulation.
- Enforces role-based access control (RBAC) for ADMIN and ANALYST privileges.
- Configures CORS for local and web frontend clients.
- Provides interactive OpenAPI / Swagger UI documentation at /docs with BearerAuth.
"""

import sys
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from backend.core.config import settings
from database.init_db import init_database
from ml_model.predictor import get_predictor
from backend.api import (
    routes_health,
    routes_auth,
    routes_users,
    routes_transactions,
    routes_predict,
    routes_alerts,
    routes_analytics,
    routes_simulation,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("fraudshield.gateway")

# OpenAPI Tags Metadata for Swagger UI
tags_metadata = [
    {
        "name": "Health & System",
        "description": "Deep operational health checks probing database, SQLite tables, and ML artifacts.",
    },
    {
        "name": "Authentication & Access Control",
        "description": "Secure login, token-based authentication (JWT), session inspection, and logout revocation.",
    },
    {
        "name": "User Administration (ADMIN Only)",
        "description": "Management of application security accounts (SOC Analysts and Administrators). Requires ADMIN role.",
    },
    {
        "name": "Transactions",
        "description": "Real-time UPI payment ingestion, scoring, persistence, and audit ledger queries.",
    },
    {
        "name": "Machine Learning Inference",
        "description": "Direct, stateless Isolation Forest anomaly scoring with transparent feature explainability.",
    },
    {
        "name": "Alerts & SOC Triage",
        "description": "Security Operations Center (SOC) review queue and analyst triage actions (APPROVE, BLOCK, DISMISS).",
    },
    {
        "name": "Analytics & Dashboard KPIs",
        "description": "Aggregated metrics, risk tier distributions, and hourly attack trends for Chart.js dashboards (ADMIN Only).",
    },
    {
        "name": "Simulation & Demo",
        "description": "One-click scenario triggers (SIM swap, velocity burst, phishing) and transaction traffic streaming.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager: runs on startup and shutdown."""
    logger.info("Starting FraudShield AI Gateway...")

    # 1. Initialize SQLite tables, baseline profiles, and initial admin/analyst users
    try:
        init_database()
        logger.info("SQLite database verified: tables, baselines, and initial accounts ready.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

    # 2. Warm up and verify Isolation Forest ML model
    try:
        predictor = get_predictor()
        logger.info(
            f"Machine Learning model loaded: {type(predictor.model).__name__} "
            f"({len(predictor.preprocessor.feature_names)} features, contamination={predictor.model.contamination})"
        )
    except Exception as e:
        logger.warning(f"ML Model artifact warning during startup: {e}")

    yield

    logger.info("Shutting down FraudShield AI Gateway.")


app = FastAPI(
    title="FraudShield AI - UPI Real-Time Fraud Detection Gateway",
    version=settings.VERSION,
    description=(
        "Production-grade Real-Time Fraud Detection for UPI and Digital Payments. "
        "Fuses unsupervised Scikit-Learn Isolation Forest anomaly detection with empirical behavioral "
        "baselines to assign calibrated risk scores (0-100) and provide transparent, explainable alerts. "
        "Protected by Role-Based Access Control (RBAC) with ADMIN and ANALYST roles."
    ),
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# -------------------------------------------------------------------------
# CORS Configuration
# -------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------------
# Custom Exception Handlers
# -------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Provides structured, human-readable errors for schema validation failures."""
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field,
            "message": err.get("msg", "Invalid input value"),
            "type": err.get("type", "value_error"),
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": "Request payload failed Pydantic validation.",
            "field_errors": errors,
        },
    )


# -------------------------------------------------------------------------
# Modular API Routers Registration
# -------------------------------------------------------------------------
# 1. Root and Health Endpoints
app.include_router(routes_health.router)

# 2. Primary /api routes
app.include_router(routes_auth.router, prefix="/api")
app.include_router(routes_users.router, prefix="/api")
app.include_router(routes_transactions.router, prefix="/api")
app.include_router(routes_predict.router, prefix="/api")
app.include_router(routes_alerts.router, prefix="/api")
app.include_router(routes_analytics.router, prefix="/api")
app.include_router(routes_simulation.router, prefix="/api")

# 3. Also alias under /api/v1 for versioned clients and backward compatibility
app.include_router(routes_auth.router, prefix="/api/v1")
app.include_router(routes_users.router, prefix="/api/v1")
app.include_router(routes_transactions.router, prefix="/api/v1")
app.include_router(routes_predict.router, prefix="/api/v1")
app.include_router(routes_alerts.router, prefix="/api/v1")
app.include_router(routes_analytics.router, prefix="/api/v1")
app.include_router(routes_simulation.router, prefix="/api/v1")


# -------------------------------------------------------------------------
# Root Welcome & Discovery Endpoint
# -------------------------------------------------------------------------
@app.get("/", tags=["Health & System"])
def root() -> dict[str, Any]:
    """Welcome gateway and API route index."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/health",
        "api_endpoints": {
            "health": "/health",
            "login": "/api/auth/login",
            "logout": "/api/auth/logout",
            "current_user": "/api/auth/me",
            "manage_users": "/api/users",
            "submit_transaction": "/api/transactions",
            "predict": "/api/predict",
            "list_transactions": "/api/transactions",
            "get_transaction": "/api/transactions/{transaction_id}",
            "list_alerts": "/api/alerts",
            "analytics": "/api/analytics",
            "simulation_preset": "/api/simulation/preset",
            "simulation_stream": "/api/simulation/stream",
        },
    }


# -------------------------------------------------------------------------
# Static File Mounting (Frontend UI)
# -------------------------------------------------------------------------
if settings.FRONTEND_DIR.exists():
    app.mount(
        "/ui",
        StaticFiles(directory=str(settings.FRONTEND_DIR), html=True),
        name="frontend_ui",
    )
