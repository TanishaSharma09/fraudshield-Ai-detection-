"""FraudShield AI - SQLite CRUD Data Access Layer.

Provides structured CRUD operations, connection management, transaction handling,
and safe conflict resolution for:
1. Users
2. Transactions
3. Fraud Alerts
4. Model Prediction Records
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Literal

from database.connection import execute_stmt, query_all, query_one


class DuplicateTransactionError(Exception):
    """Raised when an attempt is made to insert a duplicate transaction ID in strict mode."""
    pass


class RecordNotFoundError(Exception):
    """Raised when a requested record is not found."""
    pass


# ===========================================================================
# 1. Users CRUD
# ===========================================================================
class UserCRUD:
    """CRUD operations for the `users` table."""

    @staticmethod
    def create_user(
        upi_id: str,
        full_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        avg_amount: float = 1500.0,
        std_amount: float = 600.0,
        total_transactions: int = 0,
        known_devices: list[str] | None = None,
        typical_cities: list[str] | None = None,
        db_path: str | None = None,
    ) -> dict[str, Any]:
        """Creates a new user profile or updates existing baseline."""
        clean_upi = upi_id.strip().lower()
        now_utc = datetime.now(timezone.utc).isoformat()
        devices_json = json.dumps(known_devices or [])
        cities_json = json.dumps(typical_cities or [])

        execute_stmt(
            """
            INSERT INTO users 
            (upi_id, full_name, email, phone, avg_amount, std_amount, total_transactions,
             known_devices_json, typical_cities_json, last_seen, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(upi_id) DO UPDATE SET
                full_name = COALESCE(excluded.full_name, users.full_name),
                email = COALESCE(excluded.email, users.email),
                phone = COALESCE(excluded.phone, users.phone),
                avg_amount = excluded.avg_amount,
                std_amount = excluded.std_amount,
                total_transactions = excluded.total_transactions,
                known_devices_json = excluded.known_devices_json,
                typical_cities_json = excluded.typical_cities_json,
                last_seen = excluded.last_seen,
                updated_at = excluded.updated_at;
            """,
            (
                clean_upi,
                full_name,
                email,
                phone,
                avg_amount,
                std_amount,
                total_transactions,
                devices_json,
                cities_json,
                now_utc,
                now_utc,
                now_utc,
            ),
            db_path=db_path,
        )

        # Also maintain user_profiles mirror for compatibility
        execute_stmt(
            """
            INSERT OR REPLACE INTO user_profiles
            (upi_id, avg_amount, std_amount, total_transactions, known_devices_json, typical_cities_json, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (clean_upi, avg_amount, std_amount, total_transactions, devices_json, cities_json, now_utc),
            db_path=db_path,
        )

        return UserCRUD.get_user_by_upi(clean_upi, db_path=db_path)  # type: ignore

    @staticmethod
    def get_user_by_upi(upi_id: str, db_path: str | None = None) -> dict[str, Any] | None:
        """Retrieves a user by UPI VPA."""
        row = query_one("SELECT * FROM users WHERE upi_id = ?;", (upi_id.strip().lower(),), db_path=db_path)
        if not row:
            return None
        user = dict(row)
        user["known_devices"] = json.loads(user.get("known_devices_json", "[]"))
        user["typical_cities"] = json.loads(user.get("typical_cities_json", "[]"))
        return user

    @staticmethod
    def get_user_by_id(user_id: int, db_path: str | None = None) -> dict[str, Any] | None:
        """Retrieves a user by numeric primary key."""
        row = query_one("SELECT * FROM users WHERE id = ?;", (user_id,), db_path=db_path)
        if not row:
            return None
        user = dict(row)
        user["known_devices"] = json.loads(user.get("known_devices_json", "[]"))
        user["typical_cities"] = json.loads(user.get("typical_cities_json", "[]"))
        return user

    @staticmethod
    def list_users(limit: int = 50, offset: int = 0, db_path: str | None = None) -> tuple[list[dict[str, Any]], int]:
        """Lists users with pagination."""
        count_row = query_one("SELECT COUNT(*) AS total FROM users;", db_path=db_path)
        total = count_row["total"] if count_row else 0
        rows = query_all("SELECT * FROM users ORDER BY id ASC LIMIT ? OFFSET ?;", (limit, offset), db_path=db_path)
        users = []
        for r in rows:
            u = dict(r)
            u["known_devices"] = json.loads(u.get("known_devices_json", "[]"))
            u["typical_cities"] = json.loads(u.get("typical_cities_json", "[]"))
            users.append(u)
        return users, total

    @staticmethod
    def update_user(upi_id: str, update_data: dict[str, Any], db_path: str | None = None) -> dict[str, Any] | None:
        """Updates specific fields of an existing user profile."""
        clean_upi = upi_id.strip().lower()
        existing = UserCRUD.get_user_by_upi(clean_upi, db_path=db_path)
        if not existing:
            return None

        now_utc = datetime.now(timezone.utc).isoformat()
        devices = json.dumps(update_data["known_devices"]) if "known_devices" in update_data else existing["known_devices_json"]
        cities = json.dumps(update_data["typical_cities"]) if "typical_cities" in update_data else existing["typical_cities_json"]

        execute_stmt(
            """
            UPDATE users SET
                full_name = COALESCE(?, full_name),
                email = COALESCE(?, email),
                phone = COALESCE(?, phone),
                avg_amount = COALESCE(?, avg_amount),
                std_amount = COALESCE(?, std_amount),
                total_transactions = COALESCE(?, total_transactions),
                known_devices_json = ?,
                typical_cities_json = ?,
                last_seen = ?,
                updated_at = ?
            WHERE upi_id = ?;
            """,
            (
                update_data.get("full_name"),
                update_data.get("email"),
                update_data.get("phone"),
                update_data.get("avg_amount"),
                update_data.get("std_amount"),
                update_data.get("total_transactions"),
                devices,
                cities,
                now_utc,
                now_utc,
                clean_upi,
            ),
            db_path=db_path,
        )
        return UserCRUD.get_user_by_upi(clean_upi, db_path=db_path)

    @staticmethod
    def delete_user(upi_id: str, db_path: str | None = None) -> bool:
        """Deletes a user record."""
        clean_upi = upi_id.strip().lower()
        count = execute_stmt("DELETE FROM users WHERE upi_id = ?;", (clean_upi,), db_path=db_path)
        execute_stmt("DELETE FROM user_profiles WHERE upi_id = ?;", (clean_upi,), db_path=db_path)
        return count > 0


# ===========================================================================
# 2. Transactions CRUD (With Safe Duplicate Handling)
# ===========================================================================
class TransactionCRUD:
    """CRUD operations for the `transactions` table."""

    @staticmethod
    def create_transaction(
        tx: dict[str, Any],
        on_duplicate: Literal["update", "ignore", "raise"] = "update",
        db_path: str | None = None,
    ) -> dict[str, Any]:
        """Safely inserts a transaction handling duplicate transaction IDs without unhandled crashes.

        Args:
            tx: Transaction parameters dictionary.
            on_duplicate: Strategy for duplicate tx_id:
                - 'update': Upserts fields if tx_id already exists.
                - 'ignore': Leaves existing intact and returns existing record.
                - 'raise': Raises DuplicateTransactionError if tx_id already exists.
            db_path: Optional custom SQLite path.

        Returns:
            Dictionary of stored transaction.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        tx_id = str(tx.get("tx_id") or f"UPI-{now_utc.replace(':', '').replace('-', '')[:15]}")
        timestamp = str(tx.get("timestamp") or now_utc)

        existing = TransactionCRUD.get_transaction_by_tx_id(tx_id, db_path=db_path)
        if existing:
            if on_duplicate == "raise":
                raise DuplicateTransactionError(f"Transaction with tx_id '{tx_id}' already exists in ledger.")
            elif on_duplicate == "ignore":
                res = dict(existing)
                res["is_duplicate"] = True
                return res

        # Strategy 'update' or new record insert
        execute_stmt(
            """
            INSERT INTO transactions 
            (tx_id, sender_upi, receiver_upi, amount, channel, device_id, ip_address,
             location_city, timestamp, risk_score, risk_tier, status, primary_factor, is_flagged, created_at)
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
                str(tx.get("sender_upi", "")).strip().lower(),
                str(tx.get("receiver_upi", "")).strip().lower(),
                float(tx.get("amount", 0.0)),
                str(tx.get("channel", "UPI_APP")),
                str(tx.get("device_id", "DEV-UNKNOWN")),
                str(tx.get("ip_address", "127.0.0.1")),
                str(tx.get("location_city", "Mumbai")),
                timestamp,
                float(tx.get("risk_score", 0.0)),
                str(tx.get("risk_tier", "LOW")),
                str(tx.get("status", "APPROVED")),
                tx.get("primary_factor"),
                int(tx.get("is_flagged", 0)),
                now_utc,
            ),
            db_path=db_path,
        )

        return TransactionCRUD.get_transaction_by_tx_id(tx_id, db_path=db_path)  # type: ignore

    @staticmethod
    def get_transaction_by_tx_id(tx_id: str, db_path: str | None = None) -> dict[str, Any] | None:
        """Retrieves transaction by business tx_id."""
        row = query_one("SELECT * FROM transactions WHERE tx_id = ?;", (tx_id.strip(),), db_path=db_path)
        return dict(row) if row else None

    @staticmethod
    def get_transaction_by_id(tx_pk: int, db_path: str | None = None) -> dict[str, Any] | None:
        """Retrieves transaction by auto-incrementing ID."""
        row = query_one("SELECT * FROM transactions WHERE id = ?;", (tx_pk,), db_path=db_path)
        return dict(row) if row else None

    @staticmethod
    def list_transactions(
        limit: int = 50,
        offset: int = 0,
        risk_tier: str | None = None,
        sender_upi: str | None = None,
        is_flagged: int | None = None,
        db_path: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Lists transactions with filters and pagination."""
        where_clauses: list[str] = []
        params: list[Any] = []

        if risk_tier:
            where_clauses.append("UPPER(risk_tier) = ?")
            params.append(risk_tier.strip().upper())

        if sender_upi:
            where_clauses.append("LOWER(sender_upi) LIKE ?")
            params.append(f"%{sender_upi.strip().lower()}%")

        if is_flagged is not None:
            where_clauses.append("is_flagged = ?")
            params.append(int(is_flagged))

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cnt = query_one(f"SELECT COUNT(*) AS total FROM transactions {where_sql};", tuple(params), db_path=db_path)
        total = cnt["total"] if cnt else 0

        rows = query_all(
            f"SELECT * FROM transactions {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?;",
            tuple(params + [limit, offset]),
            db_path=db_path,
        )
        return [dict(r) for r in rows], total

    @staticmethod
    def update_transaction_status(tx_id: str, new_status: str, db_path: str | None = None) -> bool:
        """Updates the status of a transaction (APPROVED, FLAGGED, BLOCKED)."""
        count = execute_stmt(
            "UPDATE transactions SET status = ? WHERE tx_id = ?;",
            (new_status.strip().upper(), tx_id.strip()),
            db_path=db_path,
        )
        return count > 0

    @staticmethod
    def delete_transaction(tx_id: str, db_path: str | None = None) -> bool:
        """Deletes transaction and cascades to alerts and prediction records."""
        count = execute_stmt("DELETE FROM transactions WHERE tx_id = ?;", (tx_id.strip(),), db_path=db_path)
        return count > 0


# ===========================================================================
# 3. Fraud Alerts CRUD
# ===========================================================================
class AlertCRUD:
    """CRUD operations for the `fraud_alerts` table."""

    @staticmethod
    def create_alert(
        alert_data: dict[str, Any],
        on_duplicate: Literal["update", "ignore"] = "update",
        db_path: str | None = None,
    ) -> dict[str, Any]:
        """Creates a fraud alert linked to a transaction via foreign key."""
        now_utc = datetime.now(timezone.utc).isoformat()
        alert_id = str(alert_data["alert_id"])
        tx_id = str(alert_data["tx_id"])
        severity = str(alert_data.get("severity", "MEDIUM")).upper()
        reason = str(alert_data.get("primary_reason", "ANOMALOUS_ACTIVITY"))
        status = str(alert_data.get("status", "PENDING")).upper()

        explanations = alert_data.get("explanations_json") or json.dumps(alert_data.get("explanations", []))
        if not isinstance(explanations, str):
            explanations = json.dumps(explanations)

        execute_stmt(
            """
            INSERT INTO fraud_alerts 
            (alert_id, tx_id, severity, primary_reason, explanations_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(alert_id) DO UPDATE SET
                severity = excluded.severity,
                primary_reason = excluded.primary_reason,
                explanations_json = excluded.explanations_json,
                status = excluded.status,
                updated_at = excluded.updated_at;
            """,
            (alert_id, tx_id, severity, reason, explanations, status, now_utc, now_utc),
            db_path=db_path,
        )

        return AlertCRUD.get_alert_by_id(alert_id, db_path=db_path)  # type: ignore

    @staticmethod
    def get_alert_by_id(alert_id: str, db_path: str | None = None) -> dict[str, Any] | None:
        """Retrieves alert by alert_id or primary key."""
        clean_id = alert_id.strip()
        row = query_one(
            """
            SELECT a.*, t.amount, t.sender_upi, t.receiver_upi, t.channel
            FROM fraud_alerts a
            LEFT JOIN transactions t ON a.tx_id = t.tx_id
            WHERE a.alert_id = ? OR CAST(a.id AS TEXT) = ?;
            """,
            (clean_id, clean_id),
            db_path=db_path,
        )
        if not row:
            return None
        res = dict(row)
        try:
            res["explanations"] = json.loads(res.get("explanations_json", "[]"))
        except Exception:
            res["explanations"] = []
        return res

    @staticmethod
    def get_alert_by_tx_id(tx_id: str, db_path: str | None = None) -> dict[str, Any] | None:
        """Retrieves alert attached to a transaction."""
        row = query_one("SELECT * FROM fraud_alerts WHERE tx_id = ?;", (tx_id.strip(),), db_path=db_path)
        if not row:
            return None
        res = dict(row)
        try:
            res["explanations"] = json.loads(res.get("explanations_json", "[]"))
        except Exception:
            res["explanations"] = []
        return res

    @staticmethod
    def list_alerts(
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        severity: str | None = None,
        db_path: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Lists fraud alerts joined with transaction metadata."""
        where_clauses: list[str] = []
        params: list[Any] = []

        if status:
            where_clauses.append("UPPER(a.status) = ?")
            params.append(status.strip().upper())

        if severity:
            where_clauses.append("UPPER(a.severity) = ?")
            params.append(severity.strip().upper())

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cnt = query_one(f"SELECT COUNT(*) AS total FROM fraud_alerts a {where_sql};", tuple(params), db_path=db_path)
        total = cnt["total"] if cnt else 0

        rows = query_all(
            f"""
            SELECT a.*, t.amount, t.sender_upi, t.receiver_upi
            FROM fraud_alerts a
            LEFT JOIN transactions t ON a.tx_id = t.tx_id
            {where_sql}
            ORDER BY a.id DESC
            LIMIT ? OFFSET ?;
            """,
            tuple(params + [limit, offset]),
            db_path=db_path,
        )

        alerts = []
        for r in rows:
            al = dict(r)
            try:
                al["explanations"] = json.loads(al.get("explanations_json", "[]"))
            except Exception:
                al["explanations"] = []
            alerts.append(al)

        return alerts, total

    @staticmethod
    def update_alert_status(
        alert_id: str,
        action: str,
        notes: str | None = None,
        reviewed_by: str = "SOC-Analyst-1",
        db_path: str | None = None,
    ) -> dict[str, Any] | None:
        """Updates alert status and synchronizes linked transaction status."""
        action_clean = action.strip().upper()
        now_utc = datetime.now(timezone.utc).isoformat()

        alert = AlertCRUD.get_alert_by_id(alert_id, db_path=db_path)
        if not alert:
            return None

        execute_stmt(
            """
            UPDATE fraud_alerts
            SET status = ?, analyst_notes = ?, reviewed_by = ?, updated_at = ?
            WHERE alert_id = ?;
            """,
            (action_clean, notes, reviewed_by, now_utc, alert["alert_id"]),
            db_path=db_path,
        )

        # Synchronize transaction status
        tx_status = "APPROVED" if action_clean in ["APPROVE", "APPROVED", "DISMISS", "DISMISSED"] else "BLOCKED"
        TransactionCRUD.update_transaction_status(alert["tx_id"], tx_status, db_path=db_path)

        return AlertCRUD.get_alert_by_id(alert["alert_id"], db_path=db_path)

    @staticmethod
    def delete_alert(alert_id: str, db_path: str | None = None) -> bool:
        """Deletes a fraud alert."""
        count = execute_stmt("DELETE FROM fraud_alerts WHERE alert_id = ?;", (alert_id.strip(),), db_path=db_path)
        return count > 0


# ===========================================================================
# 4. Model Prediction Records CRUD
# ===========================================================================
class ModelPredictionCRUD:
    """CRUD operations for the `model_prediction_records` table."""

    @staticmethod
    def create_prediction_record(
        pred_data: dict[str, Any],
        on_duplicate: Literal["update", "ignore"] = "update",
        db_path: str | None = None,
    ) -> dict[str, Any]:
        """Stores comprehensive ML prediction telemetry for an evaluated transaction."""
        now_utc = datetime.now(timezone.utc).isoformat()
        pred_id = str(pred_data.get("prediction_id") or f"PRED-{pred_data['tx_id']}")
        tx_id = str(pred_data["tx_id"])
        model_name = str(pred_data.get("model_name", "IsolationForest"))
        version = str(pred_data.get("model_version", "1.0.0"))
        is_anomaly = 1 if pred_data.get("is_anomaly") else 0
        raw_score = float(pred_data.get("raw_decision_score", 0.0))
        model_risk = float(pred_data.get("model_risk_score", 0.0))
        final_risk = float(pred_data.get("final_risk_score", 0.0))
        category = str(pred_data.get("risk_category", "Low risk"))

        features = pred_data.get("feature_vector_json") or json.dumps(pred_data.get("feature_vector", {}))
        if not isinstance(features, str):
            features = json.dumps(features)

        summary = str(pred_data.get("explanation_summary", "NORMAL_TRANSACTION"))

        explanations = pred_data.get("detailed_explanations_json") or json.dumps(pred_data.get("detailed_explanations", []))
        if not isinstance(explanations, str):
            explanations = json.dumps(explanations)

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
                model_name,
                version,
                is_anomaly,
                raw_score,
                model_risk,
                final_risk,
                category,
                features,
                summary,
                explanations,
                now_utc,
            ),
            db_path=db_path,
        )

        return ModelPredictionCRUD.get_prediction_by_id(pred_id, db_path=db_path)  # type: ignore

    @staticmethod
    def get_prediction_by_id(prediction_id: str, db_path: str | None = None) -> dict[str, Any] | None:
        """Retrieves prediction record by its prediction_id."""
        row = query_one(
            "SELECT * FROM model_prediction_records WHERE prediction_id = ?;",
            (prediction_id.strip(),),
            db_path=db_path,
        )
        if not row:
            return None
        res = dict(row)
        try:
            res["feature_vector"] = json.loads(res.get("feature_vector_json", "{}"))
            res["detailed_explanations"] = json.loads(res.get("detailed_explanations_json", "[]"))
        except Exception:
            pass
        return res

    @staticmethod
    def get_prediction_by_tx_id(tx_id: str, db_path: str | None = None) -> dict[str, Any] | None:
        """Retrieves prediction record by linked transaction ID."""
        row = query_one(
            "SELECT * FROM model_prediction_records WHERE tx_id = ?;",
            (tx_id.strip(),),
            db_path=db_path,
        )
        if not row:
            return None
        res = dict(row)
        try:
            res["feature_vector"] = json.loads(res.get("feature_vector_json", "{}"))
            res["detailed_explanations"] = json.loads(res.get("detailed_explanations_json", "[]"))
        except Exception:
            pass
        return res

    @staticmethod
    def list_predictions(
        limit: int = 50,
        offset: int = 0,
        anomalies_only: bool = False,
        db_path: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Lists prediction audit logs with optional anomaly filtering."""
        where_sql = "WHERE is_anomaly = 1" if anomalies_only else ""
        cnt = query_one(f"SELECT COUNT(*) AS total FROM model_prediction_records {where_sql};", db_path=db_path)
        total = cnt["total"] if cnt else 0

        rows = query_all(
            f"SELECT * FROM model_prediction_records {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?;",
            (limit, offset),
            db_path=db_path,
        )

        preds = []
        for r in rows:
            p = dict(r)
            try:
                p["feature_vector"] = json.loads(p.get("feature_vector_json", "{}"))
                p["detailed_explanations"] = json.loads(p.get("detailed_explanations_json", "[]"))
            except Exception:
                pass
            preds.append(p)
        return preds, total

    @staticmethod
    def delete_prediction(prediction_id: str, db_path: str | None = None) -> bool:
        """Deletes a model prediction record."""
        count = execute_stmt(
            "DELETE FROM model_prediction_records WHERE prediction_id = ?;",
            (prediction_id.strip(),),
            db_path=db_path,
        )
        return count > 0
