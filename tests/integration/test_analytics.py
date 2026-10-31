"""FraudShield AI - Integration Test Suite for Analytics & Forensics Module.

Verifies:
1. GET /api/analytics endpoint payload containing all 7 chart data models:
   - Chart 1: Total Transactions (count and INR volume)
   - Chart 2: Risk Tier Distribution (Low, Medium, High, Critical)
   - Chart 3: Suspicious Transaction Trends Over Time
   - Chart 4: Transaction Amount Distribution (Histogram brackets)
   - Chart 5: Transaction Frequency & Velocity Bursts
   - Chart 6: Fraud-Labelled vs. Legitimate Transactions (Ground Truth & SOC Dispositions)
   - Chart 7: Model Evaluation Metrics (Precision, Recall, F1, ROC-AUC, PR-AUC, Confusion Matrix)
2. Date range filtering and Risk tier filtering.
3. Separation of statistical anomaly flags from confirmed fraud.
4. CSV Report Exports:
   - GET /api/analytics/export/transactions
   - GET /api/analytics/export/alerts
5. RBAC security enforcement (ADMIN required, ANALYST blocked).
6. Frontend index.html components for all 7 charts and export controls.
"""

import csv
import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.security import create_access_token

# Admin authentication client
admin_token = create_access_token({"sub": "1", "username": "admin", "role": "ADMIN"})
client = TestClient(app, headers={"Authorization": f"Bearer {admin_token}"})

# Analyst client for RBAC negative checks
analyst_token = create_access_token({"sub": "2", "username": "analyst", "role": "ANALYST"})
analyst_client = TestClient(app, headers={"Authorization": f"Bearer {analyst_token}"})


def test_analytics_overview_7_charts_payload():
    """Verifies that GET /api/analytics returns complete data for all 7 required visualisations."""
    resp = client.get("/api/analytics")
    assert resp.status_code == 200
    data = resp.json()

    # Chart 1: Total Transactions & Volume
    assert "total_evaluated" in data
    assert "total_volume_inr" in data
    assert isinstance(data["total_volume_inr"], (int, float))
    assert "hourly_trends" in data
    assert len(data["hourly_trends"]) == 24
    sample_hour = data["hourly_trends"][0]
    assert "hour_label" in sample_hour
    assert "total_count" in sample_hour
    assert "total_volume" in sample_hour

    # Chart 2: Risk Tier Distribution (Low, Medium, High, Critical)
    assert "distribution" in data
    dist = data["distribution"]
    assert "low" in dist
    assert "medium" in dist
    assert "high" in dist
    assert "critical" in dist

    # Chart 3: Suspicious Transaction Trends Over Time
    assert "flagged_count" in sample_hour
    assert "flagged_volume" in sample_hour

    # Chart 4: Transaction Amount Distribution Brackets
    assert "amount_distribution" in data
    assert len(data["amount_distribution"]) >= 6
    b0 = data["amount_distribution"][0]
    assert "bracket_label" in b0
    assert "min_amount" in b0
    assert "total_count" in b0
    assert "flagged_count" in b0
    assert "total_volume" in b0

    # Chart 5: Transaction Frequency & Velocity Bursts
    assert "frequency_distribution" in data
    assert len(data["frequency_distribution"]) >= 4
    f0 = data["frequency_distribution"][0]
    assert "frequency_label" in f0
    assert "count" in f0
    assert "percentage" in f0
    assert "flagged_count" in f0

    # Chart 6: Fraud-Labelled vs Legitimate Transactions
    assert "fraud_vs_legit" in data
    fvl = data["fraud_vs_legit"]
    assert fvl is not None
    assert "has_ground_truth_labels" in fvl
    assert "ground_truth_fraud" in fvl
    assert "ground_truth_legitimate" in fvl
    assert "operational_confirmed_fraud" in fvl
    assert "operational_confirmed_legit" in fvl
    assert "model_flagged_anomalies" in fvl
    assert "anomaly_vs_fraud_explanation" in fvl

    # Chart 7: Model Evaluation Metrics
    assert "model_metrics" in data
    mm = data["model_metrics"]
    assert mm is not None
    assert 0.0 <= mm["precision"] <= 1.0
    assert 0.0 <= mm["recall"] <= 1.0
    assert 0.0 <= mm["f1_score"] <= 1.0
    assert 0.0 <= mm["specificity"] <= 1.0
    assert 0.0 <= mm["roc_auc"] <= 1.0
    assert 0.0 <= mm["pr_auc"] <= 1.0
    assert "confusion_matrix" in mm
    cm = mm["confusion_matrix"]
    assert "true_positives" in cm
    assert "false_positives" in cm
    assert "true_negatives" in cm
    assert "false_negatives" in cm


def test_analytics_date_and_risk_filtering():
    """Verifies parameterized date and risk tier query filtering."""
    # 1. Filter by Risk Tier = LOW
    resp_low = client.get("/api/analytics?risk_tier=LOW")
    assert resp_low.status_code == 200
    data_low = resp_low.json()
    assert data_low["risk_filter_applied"] == "LOW"

    # 2. Filter by Risk Tier = HIGH
    resp_high = client.get("/api/analytics?risk_tier=HIGH")
    assert resp_high.status_code == 200
    data_high = resp_high.json()
    assert data_high["risk_filter_applied"] == "HIGH"

    # 3. Filter by Date Range
    resp_date = client.get("/api/analytics?start_date=2026-01-01&end_date=2026-12-31")
    assert resp_date.status_code == 200
    data_date = resp_date.json()
    assert data_date["date_filter_applied"]["start"] == "2026-01-01"
    assert data_date["date_filter_applied"]["end"] == "2026-12-31"


def test_anomaly_vs_confirmed_fraud_conceptual_separation():
    """Verifies that model-flagged anomaly is explicitly documented as distinct from confirmed fraud."""
    resp = client.get("/api/analytics")
    data = resp.json()
    explanation = data["fraud_vs_legit"]["anomaly_vs_fraud_explanation"]
    assert "Isolation Forest anomaly" in explanation
    assert "Confirmed fraud" in explanation or "criminal" in explanation.lower() or "chargeback" in explanation.lower()


def test_export_transactions_csv_endpoint():
    """Verifies RFC-4180 compliant CSV stream for transaction records."""
    resp = client.get("/api/analytics/export/transactions")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment; filename=" in resp.headers["content-disposition"]
    assert "fraudshield_transactions_" in resp.headers["content-disposition"]

    # Parse and validate CSV rows
    content = resp.text
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert len(rows) >= 1  # At least header
    header = rows[0]
    assert "Transaction ID" in header
    assert "Sender VPA" in header
    assert "Receiver VPA" in header
    assert "Amount (INR)" in header
    assert "Risk Score (0-100)" in header
    assert "Review Status" in header


def test_export_alerts_csv_endpoint():
    """Verifies RFC-4180 compliant CSV stream for fraud alerts triage queue."""
    resp = client.get("/api/analytics/export/alerts")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment; filename=" in resp.headers["content-disposition"]
    assert "fraudshield_alerts_" in resp.headers["content-disposition"]

    # Parse and validate CSV rows
    content = resp.text
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert len(rows) >= 1
    header = rows[0]
    assert "Alert ID" in header
    assert "Transaction ID" in header
    assert "Severity" in header
    assert "Risk Score" in header
    assert "Primary Flag Reason" in header
    assert "Status" in header


def test_rbac_analyst_forbidden_from_analytics_and_exports():
    """Verifies that ANALYST role is strictly forbidden (403) from analytics and CSV export endpoints."""
    resp_overview = analyst_client.get("/api/analytics")
    assert resp_overview.status_code == 403

    resp_tx_csv = analyst_client.get("/api/analytics/export/transactions")
    assert resp_tx_csv.status_code == 403

    resp_al_csv = analyst_client.get("/api/analytics/export/alerts")
    assert resp_al_csv.status_code == 403


def test_frontend_analytics_dom_components():
    """Verifies that index.html contains all 7 analytics chart canvases and required controls."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Dedicated View Panel
    assert 'id="view-analytics"' in html
    assert 'id="nav-analytics"' in html

    # All 7 Chart Canvases
    assert 'id="chart-analytics-total-tx"' in html
    assert 'id="chart-analytics-risk-dist"' in html
    assert 'id="chart-analytics-suspicious-trends"' in html
    assert 'id="chart-analytics-amount-dist"' in html
    assert 'id="chart-analytics-frequency-dist"' in html
    assert 'id="chart-analytics-fraud-vs-legit"' in html
    assert 'id="chart-analytics-model-eval"' in html

    # Controls and Export Buttons
    assert 'id="btn-export-transactions-csv"' in html
    assert 'id="btn-export-alerts-csv"' in html
    assert 'id="btn-analytics-refresh"' in html
    assert 'id="analytics-date-presets"' in html
    assert 'id="analytics-filter-risk"' in html
    assert 'id="analytics-filter-start"' in html
    assert 'id="analytics-filter-end"' in html

    # Forensic distinction text present
    assert "Statistical Anomaly Flags vs. Confirmed Fraud" in html
