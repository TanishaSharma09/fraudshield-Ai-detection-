"""FraudShield AI - Core Configuration Module.

Centralises application settings, risk scoring thresholds, file paths,
secret management, and environment defaults.
"""

import os
from pathlib import Path
from pydantic import BaseModel


class RiskThresholds(BaseModel):
    """Calibrated risk score boundaries (0 - 100)."""
    LOW_MAX: float = 39.99
    MEDIUM_MAX: float = 69.99
    HIGH_MAX: float = 89.99
    CRITICAL_MIN: float = 90.00


class Settings:
    """Project-wide settings and directory paths matching the modular architecture."""
    PROJECT_NAME: str = "FraudShield AI"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")

    # Root Directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # Core Application Directories
    FRONTEND_DIR: Path = BASE_DIR / "frontend"
    BACKEND_DIR: Path = BASE_DIR / "backend"
    ML_MODEL_DIR: Path = BASE_DIR / "ml_model"
    DATASET_DIR: Path = BASE_DIR / "dataset"
    DATABASE_DIR: Path = BASE_DIR / "database"
    TESTS_DIR: Path = BASE_DIR / "tests"
    DOCS_DIR: Path = BASE_DIR / "documentation"

    # Specific Subdirectories & Paths
    SAVED_MODELS_DIR: Path = ML_MODEL_DIR / "saved_models"
    MODEL_PATH: Path = SAVED_MODELS_DIR / "isolation_forest.joblib"
    FEATURE_SCALER_PATH: Path = SAVED_MODELS_DIR / "feature_scaler.joblib"

    RAW_DATASET_DIR: Path = DATASET_DIR / "raw"
    PROCESSED_DATASET_DIR: Path = DATASET_DIR / "processed"
    SYNTHETIC_DATA_PATH: Path = PROCESSED_DATASET_DIR / "upi_transactions_synthetic.csv"

    DATABASE_PATH: Path = DATABASE_DIR / "fraudshield.db"
    SCHEMA_PATH: Path = DATABASE_DIR / "schema.sql"
    SEEDS_DIR: Path = DATABASE_DIR / "seeds"

    # Risk Boundaries & Configurable Alert Thresholds
    THRESHOLDS: RiskThresholds = RiskThresholds()
    ALERT_MEDIUM_THRESHOLD: float = float(os.getenv("ALERT_MEDIUM_THRESHOLD", "40.0"))
    ALERT_HIGH_THRESHOLD: float = float(os.getenv("ALERT_HIGH_THRESHOLD", "70.0"))
    ALERT_TRIGGER_SCORE: float = ALERT_MEDIUM_THRESHOLD

    # CORS Settings: explicitly whitelist trusted origins for local dashboard and dev servers
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "FRAUDSHIELD_CORS_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    # -----------------------------------------------------------------------
    # Authentication & Secret Management (Environment Variables)
    # -----------------------------------------------------------------------
    # Loaded strictly from environment variables; falls back to a dev secret if unset
    SECRET_KEY: str = os.getenv(
        "FRAUDSHIELD_SECRET_KEY",
        "fraudshield-secure-dev-secret-key-32bytes-for-jwt-signing-2026-xyz",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

    # Initial account credentials configured via environment variables
    DEFAULT_ADMIN_USERNAME: str = os.getenv("FRAUDSHIELD_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("FRAUDSHIELD_ADMIN_PASSWORD", "Admin@FraudShield2026!")
    DEFAULT_ADMIN_EMAIL: str = os.getenv("FRAUDSHIELD_ADMIN_EMAIL", "admin@fraudshield.ai")

    DEFAULT_ANALYST_USERNAME: str = os.getenv("FRAUDSHIELD_ANALYST_USERNAME", "analyst")
    DEFAULT_ANALYST_PASSWORD: str = os.getenv("FRAUDSHIELD_ANALYST_PASSWORD", "Analyst@FraudShield2026!")
    DEFAULT_ANALYST_EMAIL: str = os.getenv("FRAUDSHIELD_ANALYST_EMAIL", "analyst@fraudshield.ai")

    def ensure_directories(self) -> None:
        """Ensure all required project directories exist."""
        for path in [
            self.FRONTEND_DIR / "css",
            self.FRONTEND_DIR / "js",
            self.FRONTEND_DIR / "assets",
            self.BACKEND_DIR / "api",
            self.BACKEND_DIR / "services",
            self.BACKEND_DIR / "schemas",
            self.BACKEND_DIR / "core",
            self.ML_MODEL_DIR / "training",
            self.ML_MODEL_DIR / "saved_models",
            self.ML_MODEL_DIR / "features",
            self.ML_MODEL_DIR / "explainability",
            self.DATASET_DIR / "raw",
            self.DATASET_DIR / "processed",
            self.DATASET_DIR / "generators",
            self.DATABASE_DIR / "seeds",
            self.TESTS_DIR / "unit",
            self.TESTS_DIR / "integration",
            self.DOCS_DIR,
        ]:
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
