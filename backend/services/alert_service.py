"""FraudShield AI - Alert & Persistence Service.

Coordinates real-time risk scoring, explainability generation, and SQLite persistence:
- Scores transactions via TransactionRiskScoringEngine.
- Generates structured, transparent explainable alerts via TransparentFeatureExplainer.
- Persists transaction records in the `transactions` table.
- Persists actionable alert queues in the `fraud_alerts` table for SOC analyst review.
- Manages alert queries, pagination, and analyst review action state transitions.
"""

import json
from datetime import datetime, timezone
from typing import Any

from backend.core.config import settings
from backend.services.risk_scoring_service import get_risk_scoring_engine
from ml_model.explainability.explainer import get_explainer
from database.connection import execute_stmt, query_all, query_one


class AlertService:
    """Service managing risk evaluation, explainability, and database persistence."""

    def __init__(self) -> None:
        self.scoring_engine = get_risk_scoring_engine()
        self.explainer = get_explainer()

    def process_transaction(
        self,
        transaction: dict[str, Any],
        user_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluates, explains, and persists an incoming digital payment."""
        sender_vpa = str(transaction.get("sender_upi", "")).strip().lower()
        now_utc = datetime.now(timezone.utc).isoformat()
        tx_timestamp = transaction.get("timestamp") or now_utc

        # Fetch leak-free user baseline from SQLite if not explicitly supplied
        if user_profile is None and sender_vpa:
            from ml_model.behavioural.baseline_tracker import get_baseline_tracker
            tracker = get_baseline_tracker()
            baseline = tracker.get_user_baseline_from_db(sender_vpa, as_of_timestamp=tx_timestamp)
            user_profile = {
                "avg_amount": baseline.avg_amount,
                "std_amount": baseline.std_amount,
                "known_devices": list(baseline.known_devices),
                "known_recipients": list(baseline.known_recipients),
                "daily_frequency_mean": baseline.daily_frequency_mean,
            }
            if "velocity_15m" not in transaction:
                transaction["velocity_15m"] = float(baseline.recent_15m_count + 1)
            if "time_since_last_tx" not in transaction and baseline.seconds_since_last_tx is not None:
                transaction["time_since_last_tx"] = float(baseline.seconds_since_last_tx / 3600.0)

        # 1. Evaluate Risk Score & Level
        scoring_result = self.scoring_engine.evaluate(transaction, user_profile)

        # 2. Generate Transparent Explainable Alert
        explainable_alert = self.explainer.explain(transaction, user_profile, scoring_result)

        tx_details = scoring_result.transaction_details
        tx_id = scoring_result.transaction_id
        risk_score = scoring_result.risk_score
        risk_tier = scoring_result.risk_category.upper().replace(" RISK", "")
        status = scoring_result.action_recommendation
        primary_factor = explainable_alert.primary_reason
        is_flagged = 1 if scoring_result.risk_category == "High risk" else 0

        now_utc = datetime.now(timezone.utc).isoformat()
        tx_timestamp = tx_details.get("timestamp") or transaction.get("timestamp") or now_utc

        # 3. Persist to SQLite transactions table (use ON CONFLICT DO UPDATE to prevent foreign key cascade)
        try:
            execute_stmt(
                """
                INSERT INTO transactions 
                (tx_id, sender_upi, receiver_upi, amount, channel, device_id, ip_address, location_city,
                 timestamp, risk_score, risk_tier, status, primary_factor, is_flagged, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tx_id) DO UPDATE SET
                    sender_upi = excluded.sender_upi,
                    receiver_upi = excluded.receiver_upi,
                    amount = excluded.amount,
                    channel = excluded.channel,
                    device_id = excluded.device_id,
                    ip_address = excluded.ip_address,
                    location_city = excluded.location_city,
                    timestamp = excluded.timestamp,
                    risk_score = excluded.risk_score,
                    risk_tier = excluded.risk_tier,
                    status = excluded.status,
                    primary_factor = excluded.primary_factor,
                    is_flagged = excluded.is_flagged;
                """,
                (
                    tx_id,
                    tx_details.get("sender_upi"),
                    tx_details.get("receiver_upi"),
                    tx_details.get("amount"),
                    tx_details.get("channel", "UPI_APP"),
                    tx_details.get("device_id", "DEV-UNKNOWN"),
                    transaction.get("ip_address", "127.0.0.1"),
                    tx_details.get("location_city", "Mumbai"),
                    tx_timestamp,
                    risk_score,
                    risk_tier,
                    status,
                    primary_factor,
                    is_flagged,
                    now_utc,
                ),
            )
        except Exception as e:
            print(f"Warning: Could not persist transaction to database: {e}")

        # 4. Persist Model Prediction Record (every processed transaction)
        try:
            pred_id = f"PRED-{tx_id}"
            factors_json = json.dumps([f.to_dict() for f in explainable_alert.contributing_factors])
            anomaly_flag = 1 if scoring_result.anomaly_prediction.is_anomaly else 0
            execute_stmt(
                """
                INSERT INTO model_prediction_records
                (prediction_id, tx_id, model_name, model_version, is_anomaly, raw_decision_score,
                 model_risk_score, final_risk_score, risk_category, feature_vector_json,
                 explanation_summary, detailed_explanations_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(prediction_id) DO UPDATE SET
                    is_anomaly = excluded.is_anomaly,
                    raw_decision_score = excluded.raw_decision_score,
                    model_risk_score = excluded.model_risk_score,
                    final_risk_score = excluded.final_risk_score,
                    risk_category = excluded.risk_category,
                    feature_vector_json = excluded.feature_vector_json,
                    explanation_summary = excluded.explanation_summary,
                    detailed_explanations_json = excluded.detailed_explanations_json;
                """,
                (
                    pred_id,
                    tx_id,
                    "IsolationForest",
                    scoring_result.anomaly_prediction.model_version,
                    anomaly_flag,
                    scoring_result.anomaly_prediction.raw_decision_score,
                    scoring_result.anomaly_prediction.model_risk_contribution,
                    risk_score,
                    scoring_result.risk_category,
                    json.dumps(tx_details),
                    primary_factor,
                    factors_json,
                    now_utc,
                ),
            )
        except Exception as e:
            print(f"Warning: Could not persist model prediction record: {e}")

        # 5. Configurable threshold alert creation with deduplication
        db_alert_id = None
        is_alert_worthy = (
            scoring_result.risk_category in ["High risk", "Medium risk"]
            or risk_score >= settings.ALERT_TRIGGER_SCORE
        )
        if is_alert_worthy:
            severity = "HIGH" if scoring_result.risk_category == "High risk" or risk_score >= settings.ALERT_HIGH_THRESHOLD else "MEDIUM"
            factors_json = json.dumps([f.to_dict() for f in explainable_alert.contributing_factors])

            # Deduplication: check if an alert already exists for this tx_id
            existing = query_one(
                "SELECT alert_id, status FROM fraud_alerts WHERE tx_id = ?;",
                (tx_id,),
            )
            if existing:
                # Reuse existing alert_id and update without generating duplicate rows
                db_alert_id = existing["alert_id"]
                current_status = existing["status"]
                # Retain review status if already reviewed/approved/blocked
                retained_status = current_status if current_status in ["REVIEWED", "APPROVED", "BLOCKED", "DISMISSED"] else "PENDING"
                try:
                    execute_stmt(
                        """
                        UPDATE fraud_alerts
                        SET severity = ?, primary_reason = ?, explanations_json = ?, status = ?, updated_at = ?
                        WHERE alert_id = ?;
                        """,
                        (severity, primary_factor, factors_json, retained_status, now_utc, db_alert_id),
                    )
                except Exception as e:
                    print(f"Warning: Could not update existing fraud alert: {e}")
            else:
                db_alert_id = explainable_alert.alert_id
                try:
                    execute_stmt(
                        """
                        INSERT INTO fraud_alerts 
                        (alert_id, tx_id, severity, primary_reason, explanations_json, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?);
                        """,
                        (
                            db_alert_id,
                            tx_id,
                            severity,
                            primary_factor,
                            factors_json,
                            now_utc,
                            now_utc,
                        ),
                    )
                except Exception as e:
                    print(f"Warning: Could not persist fraud alert to database: {e}")

        # Combine into complete response
        return {
            "transaction_id": tx_id,
            "alert_id": db_alert_id,
            "risk_score": risk_score,
            "risk_category": scoring_result.risk_category,
            "action_recommendation": status,
            "anomaly_prediction": scoring_result.anomaly_prediction.to_dict(),
            "explainable_alert": explainable_alert.to_dict(),
            "transaction_details": tx_details,
            "evaluated_at": now_utc,
        }

    def get_alerts(
        self,
        status: str | None = None,
        severity: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Queries fraud alerts enriched with transaction data, with filtering and pagination."""
        where_clauses: list[str] = []
        params: list[Any] = []

        if status:
            where_clauses.append("UPPER(a.status) = ?")
            params.append(status.strip().upper())

        if severity:
            where_clauses.append("UPPER(a.severity) = ?")
            params.append(severity.strip().upper())

        if search:
            search_param = f"%{search.strip().lower()}%"
            where_clauses.append(
                "(LOWER(a.alert_id) LIKE ? OR LOWER(a.tx_id) LIKE ? OR LOWER(a.primary_reason) LIKE ? OR LOWER(COALESCE(t.sender_upi, '')) LIKE ? OR LOWER(COALESCE(t.receiver_upi, '')) LIKE ?)"
            )
            params.extend([search_param, search_param, search_param, search_param, search_param])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Total count query
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM fraud_alerts a
            LEFT JOIN transactions t ON a.tx_id = t.tx_id
            {where_sql};
        """
        count_row = query_one(count_sql, tuple(params))
        total = count_row["total"] if count_row else 0

        # Data query joined with transactions
        data_sql = f"""
            SELECT a.id, a.alert_id, a.tx_id, a.severity, a.primary_reason, a.explanations_json,
                   a.status, a.reviewed_by, a.analyst_notes, a.created_at, a.updated_at,
                   t.amount, t.sender_upi, t.receiver_upi, t.risk_score, t.risk_tier,
                   t.channel, t.location_city, t.timestamp AS tx_timestamp
            FROM fraud_alerts a
            LEFT JOIN transactions t ON a.tx_id = t.tx_id
            {where_sql}
            ORDER BY a.id DESC
            LIMIT ? OFFSET ?;
        """
        rows = query_all(data_sql, tuple(params + [limit, offset]))

        formatted_alerts = []
        for r in rows:
            alert = dict(r)
            explanations = []
            try:
                raw_expl = json.loads(alert.get("explanations_json", "[]"))
                explanations = [
                    {
                        "factor_name": f.get("factor_name", "UNKNOWN"),
                        "weight": float(f.get("weight", 0.0)),
                        "severity": f.get("severity", "NORMAL"),
                        "description": f.get("description", ""),
                    }
                    for f in raw_expl
                ]
            except Exception:
                explanations = []

            alert["explanations"] = explanations
            raw_tier = str(alert.get("risk_tier") or alert["severity"]).title()
            alert["risk_category"] = f"{raw_tier} risk" if not raw_tier.lower().endswith("risk") else raw_tier
            alert["risk_score"] = float(alert.get("risk_score") if alert.get("risk_score") is not None else (85.0 if alert["severity"] in ("CRITICAL", "HIGH") else 55.0))
            alert["channel"] = alert.get("channel") or "UPI_APP"
            alert["location_city"] = alert.get("location_city") or "Mumbai"
            formatted_alerts.append(alert)

        return formatted_alerts, total

    def get_alert_by_id(self, alert_id: str) -> dict[str, Any] | None:
        """Retrieves a single fraud alert by alert_id, numeric id, or linked tx_id."""
        clean_id = alert_id.strip()

        row = query_one(
            """
            SELECT a.id, a.alert_id, a.tx_id, a.severity, a.primary_reason, a.explanations_json,
                   a.status, a.reviewed_by, a.analyst_notes, a.created_at, a.updated_at,
                   t.amount, t.sender_upi, t.receiver_upi, t.risk_score, t.risk_tier,
                   t.channel, t.location_city, t.device_id, t.status AS tx_status, t.timestamp AS tx_timestamp
            FROM fraud_alerts a
            LEFT JOIN transactions t ON a.tx_id = t.tx_id
            WHERE a.alert_id = ? OR CAST(a.id AS TEXT) = ? OR a.tx_id = ?;
            """,
            (clean_id, clean_id, clean_id),
        )

        if not row:
            # Check if clean_id is a valid transaction in transactions table
            tx_row = query_one("SELECT * FROM transactions WHERE tx_id = ?;", (clean_id,))
            if tx_row:
                tx = dict(tx_row)
                now_utc = datetime.now(timezone.utc).isoformat()
                return {
                    "id": tx.get("id", 0),
                    "alert_id": f"ALT-TX-{tx['tx_id']}",
                    "tx_id": tx["tx_id"],
                    "severity": tx.get("risk_tier") or "HIGH",
                    "primary_reason": tx.get("primary_factor") or "Evaluated Transaction Anomaly",
                    "explanations": [],
                    "status": "PENDING",
                    "reviewed_by": None,
                    "analyst_notes": None,
                    "created_at": tx.get("timestamp") or tx.get("created_at") or now_utc,
                    "updated_at": tx.get("created_at") or now_utc,
                    "amount": tx.get("amount"),
                    "sender_upi": tx.get("sender_upi"),
                    "receiver_upi": tx.get("receiver_upi"),
                    "risk_score": float(tx.get("risk_score") if tx.get("risk_score") is not None else 75.0),
                    "risk_category": f"{str(tx.get('risk_tier') or 'High').title()} risk",
                    "channel": tx.get("channel") or "UPI_APP",
                    "location_city": tx.get("location_city") or "Mumbai",
                    "device_id": tx.get("device_id") or "DEV-UNKNOWN",
                    "tx_status": tx.get("status") or "PENDING",
                    "tx_timestamp": tx.get("timestamp"),
                }
            return None

        alert = dict(row)
        explanations = []
        try:
            raw_expl = json.loads(alert.get("explanations_json", "[]"))
            explanations = [
                {
                    "factor_name": f.get("factor_name", "UNKNOWN"),
                    "weight": float(f.get("weight", 0.0)),
                    "severity": f.get("severity", "NORMAL"),
                    "description": f.get("description", ""),
                }
                for f in raw_expl
            ]
        except Exception:
            explanations = []

        alert["explanations"] = explanations
        raw_tier = str(alert.get("risk_tier") or alert["severity"]).title()
        alert["risk_category"] = f"{raw_tier} risk" if not raw_tier.lower().endswith("risk") else raw_tier
        alert["risk_score"] = float(alert.get("risk_score") if alert.get("risk_score") is not None else (85.0 if alert["severity"] in ("CRITICAL", "HIGH") else 55.0))
        alert["channel"] = alert.get("channel") or "UPI_APP"
        alert["location_city"] = alert.get("location_city") or "Mumbai"
        alert["device_id"] = alert.get("device_id") or "DEV-UNKNOWN"
        alert["tx_status"] = alert.get("tx_status") or "PENDING"
        return alert

    def update_alert_action(
        self,
        alert_id: str,
        action: str,
        notes: str | None = None,
        reviewed_by: str = "SOC-Analyst-1",
    ) -> dict[str, Any] | None:
        """Updates alert review status and updates corresponding transaction status."""
        alert = self.get_alert_by_id(alert_id)
        now_utc = datetime.now(timezone.utc).isoformat()

        if not alert:
            # Check if this alert_id belongs to a transaction and create alert on-the-fly
            tx_row = query_one("SELECT * FROM transactions WHERE tx_id = ?;", (alert_id.strip(),))
            if tx_row:
                tx = dict(tx_row)
                new_alt_id = f"ALT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{np.random.randint(100000, 999999)}"
                execute_stmt(
                    """
                    INSERT INTO fraud_alerts 
                    (alert_id, tx_id, severity, primary_reason, explanations_json, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?);
                    """,
                    (
                        new_alt_id,
                        tx["tx_id"],
                        tx.get("risk_tier") or "HIGH",
                        tx.get("primary_factor") or "Manual Security Escalation",
                        "[]",
                        now_utc,
                        now_utc,
                    ),
                )
                alert = self.get_alert_by_id(new_alt_id)

        if not alert:
            return None

        action_clean = action.strip().upper()

        # Map to alert status: normalize REVIEW to REVIEWED, retain explicit actions (APPROVE, BLOCK, DISMISS)
        alert_status_map = {
            "REVIEW": "REVIEWED",
            "REVIEWED": "REVIEWED",
            "UNDER_REVIEW": "REVIEWED",
        }
        new_alert_status = alert_status_map.get(action_clean, action_clean)

        # Update alert in fraud_alerts
        execute_stmt(
            """
            UPDATE fraud_alerts
            SET status = ?, analyst_notes = ?, reviewed_by = ?, updated_at = ?
            WHERE alert_id = ? OR tx_id = ?;
            """,
            (new_alert_status, notes, reviewed_by, now_utc, alert["alert_id"], alert.get("tx_id", alert["alert_id"])),
        )

        # Update linked transaction status accordingly
        tx_status_map = {
            "APPROVE": "APPROVED",
            "APPROVED": "APPROVED",
            "BLOCK": "BLOCKED",
            "BLOCKED": "BLOCKED",
            "DISMISS": "APPROVED",
            "DISMISSED": "APPROVED",
            "REVIEW": "UNDER_REVIEW",
            "REVIEWED": "UNDER_REVIEW",
            "UNDER_REVIEW": "UNDER_REVIEW",
        }
        new_tx_status = tx_status_map.get(action_clean, "FLAGGED")

        if alert.get("tx_id"):
            execute_stmt(
                """
                UPDATE transactions
                SET status = ?
                WHERE tx_id = ?;
                """,
                (new_tx_status, alert["tx_id"]),
            )

        return self.get_alert_by_id(alert["alert_id"])

    def get_alert_summary(self) -> dict[str, int]:
        """Returns accurate database-wide counts of fraud alerts by status and severity."""
        row = query_one(
            """
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN UPPER(status) = 'PENDING' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN UPPER(status) IN ('REVIEW', 'REVIEWED', 'UNDER_REVIEW') THEN 1 ELSE 0 END) AS under_review,
                SUM(CASE WHEN UPPER(status) IN ('APPROVE', 'APPROVED', 'DISMISSED') THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN UPPER(status) IN ('BLOCK', 'BLOCKED') THEN 1 ELSE 0 END) AS blocked,
                SUM(CASE WHEN UPPER(severity) = 'CRITICAL' THEN 1 ELSE 0 END) AS critical,
                SUM(CASE WHEN UPPER(severity) = 'HIGH' THEN 1 ELSE 0 END) AS high,
                SUM(CASE WHEN UPPER(severity) = 'MEDIUM' THEN 1 ELSE 0 END) AS medium,
                SUM(CASE WHEN UPPER(severity) = 'LOW' THEN 1 ELSE 0 END) AS low
            FROM fraud_alerts;
            """
        )
        if not row:
            return {
                "total": 0, "pending": 0, "under_review": 0, "approved": 0,
                "blocked": 0, "critical": 0, "high": 0, "medium": 0, "low": 0
            }
        return {
            "total": int(row["total"] or 0),
            "pending": int(row["pending"] or 0),
            "under_review": int(row["under_review"] or 0),
            "approved": int(row["approved"] or 0),
            "blocked": int(row["blocked"] or 0),
            "critical": int(row["critical"] or 0),
            "high": int(row["high"] or 0),
            "medium": int(row["medium"] or 0),
            "low": int(row["low"] or 0),
        }


# Singleton instance helper
_alert_service_instance: AlertService | None = None


def get_alert_service() -> AlertService:
    """Returns or initialises the singleton AlertService."""
    global _alert_service_instance
    if _alert_service_instance is None:
        _alert_service_instance = AlertService()
    return _alert_service_instance
