-- ====================================================================
-- FraudShield AI - Database Schema Definition (SQLite)
-- Real-Time Fraud Detection for UPI and Digital Payments
-- ====================================================================

-- 1. Users Table: Individual customer profiles, credentials, and baseline metrics
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upi_id TEXT UNIQUE NOT NULL,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    avg_amount REAL NOT NULL DEFAULT 1500.0 CHECK(avg_amount >= 0),
    std_amount REAL NOT NULL DEFAULT 600.0 CHECK(std_amount >= 0),
    total_transactions INTEGER NOT NULL DEFAULT 0 CHECK(total_transactions >= 0),
    known_devices_json TEXT NOT NULL DEFAULT '[]',
    typical_cities_json TEXT NOT NULL DEFAULT '[]',
    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_upi ON users (upi_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- 2. Transactions Table: Stores incoming digital payment events and evaluation scores
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_id TEXT UNIQUE NOT NULL,
    sender_upi TEXT NOT NULL,
    receiver_upi TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    channel TEXT NOT NULL DEFAULT 'UPI_APP',
    device_id TEXT NOT NULL,
    ip_address TEXT DEFAULT '127.0.0.1',
    location_city TEXT DEFAULT 'Mumbai',
    timestamp TEXT NOT NULL,
    risk_score REAL NOT NULL DEFAULT 0.0 CHECK(risk_score >= 0.0 AND risk_score <= 100.0),
    risk_tier TEXT NOT NULL DEFAULT 'LOW',
    status TEXT NOT NULL DEFAULT 'APPROVED',
    primary_factor TEXT,
    is_flagged INTEGER NOT NULL DEFAULT 0 CHECK(is_flagged IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tx_id ON transactions (tx_id);
CREATE INDEX IF NOT EXISTS idx_tx_sender ON transactions (sender_upi);
CREATE INDEX IF NOT EXISTS idx_tx_receiver ON transactions (receiver_upi);
CREATE INDEX IF NOT EXISTS idx_tx_risk_tier ON transactions (risk_tier);
CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions (status);
CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions (timestamp);
CREATE INDEX IF NOT EXISTS idx_tx_created ON transactions (created_at);

-- 3. Fraud Alerts Table: Actionable alerts queue for SOC analyst review
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT UNIQUE NOT NULL,
    tx_id TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'Medium', 'High', 'Critical')),
    primary_reason TEXT NOT NULL,
    explanations_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'REVIEWED', 'APPROVED', 'BLOCKED', 'DISMISSED')),
    reviewed_by TEXT,
    analyst_notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tx_id) REFERENCES transactions (tx_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alert_alert_id ON fraud_alerts (alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_tx_id ON fraud_alerts (tx_id);
CREATE INDEX IF NOT EXISTS idx_alert_status ON fraud_alerts (status);
CREATE INDEX IF NOT EXISTS idx_alert_severity ON fraud_alerts (severity);

-- 4. Model Prediction Records Table: Granular MLOps audit records for every evaluation
CREATE TABLE IF NOT EXISTS model_prediction_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id TEXT UNIQUE NOT NULL,
    tx_id TEXT NOT NULL,
    model_name TEXT NOT NULL DEFAULT 'IsolationForest',
    model_version TEXT NOT NULL DEFAULT '1.0.0',
    is_anomaly INTEGER NOT NULL DEFAULT 0 CHECK(is_anomaly IN (0, 1)),
    raw_decision_score REAL NOT NULL,
    model_risk_score REAL NOT NULL CHECK(model_risk_score >= 0.0 AND model_risk_score <= 100.0),
    final_risk_score REAL NOT NULL CHECK(final_risk_score >= 0.0 AND final_risk_score <= 100.0),
    risk_category TEXT NOT NULL,
    feature_vector_json TEXT NOT NULL DEFAULT '{}',
    explanation_summary TEXT NOT NULL,
    detailed_explanations_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tx_id) REFERENCES transactions (tx_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pred_prediction_id ON model_prediction_records (prediction_id);
CREATE INDEX IF NOT EXISTS idx_pred_tx_id ON model_prediction_records (tx_id);
CREATE INDEX IF NOT EXISTS idx_pred_is_anomaly ON model_prediction_records (is_anomaly);
CREATE INDEX IF NOT EXISTS idx_pred_model ON model_prediction_records (model_name, model_version);

-- 5. User Profiles Table: Backward-compatible alias view/table for rolling behavioral baselines
CREATE TABLE IF NOT EXISTS user_profiles (
    upi_id TEXT PRIMARY KEY,
    avg_amount REAL NOT NULL DEFAULT 1500.0,
    std_amount REAL NOT NULL DEFAULT 600.0,
    total_transactions INTEGER NOT NULL DEFAULT 0,
    known_devices_json TEXT NOT NULL DEFAULT '[]',
    typical_cities_json TEXT NOT NULL DEFAULT '[]',
    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Model Metrics Table: Historical telemetry, model versions, and drift logs
CREATE TABLE IF NOT EXISTS model_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    contamination REAL NOT NULL,
    total_evaluated INTEGER NOT NULL DEFAULT 0,
    total_flagged INTEGER NOT NULL DEFAULT 0,
    accuracy_score REAL,
    last_trained TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7. Application Users Table: Role-based accounts for SOC Analysts and Security Administrators
CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ADMIN', 'ANALYST')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    last_login TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_app_users_username ON app_users (username);
CREATE INDEX IF NOT EXISTS idx_app_users_email ON app_users (email);
CREATE INDEX IF NOT EXISTS idx_app_users_role ON app_users (role);

-- 8. Token Blacklist Table: Revoked JWT session tokens (Logout tracking)
CREATE TABLE IF NOT EXISTS token_blacklist (
    token_jti TEXT PRIMARY KEY,
    expires_at TEXT NOT NULL,
    revoked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_blacklist_expires ON token_blacklist (expires_at);
