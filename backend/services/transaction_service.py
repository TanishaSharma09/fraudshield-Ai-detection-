"""FraudShield AI - Transaction Service.

Coordinates transaction creation, real-time evaluation, querying,
filtering, pagination, and single transaction retrieval.
"""

from typing import Any
from backend.services.alert_service import get_alert_service
from database.connection import execute_stmt, query_all, query_one


class TransactionService:
    """Service managing database queries and evaluation workflow for transactions."""

    def __init__(self) -> None:
        self.alert_service = get_alert_service()

    def create_and_evaluate(self, tx_dict: dict[str, Any]) -> dict[str, Any]:
        """Evaluates an incoming payment, saves it to SQLite, and returns structured result."""
        result = self.alert_service.process_transaction(tx_dict)

        tx_details = result.get("transaction_details", {})
        explainable = result.get("explainable_alert", {})
        anomaly = result.get("anomaly_prediction", {})

        # Prepare explanations list for Pydantic response
        raw_explanations = explainable.get("contributing_factors", [])
        formatted_explanations = []
        for factor in raw_explanations:
            f_dict = factor.to_dict() if hasattr(factor, "to_dict") else (factor if isinstance(factor, dict) else {})
            formatted_explanations.append({
                "factor_name": f_dict.get("factor_name", "UNKNOWN"),
                "weight": float(f_dict.get("impact_weight", f_dict.get("weight", 0.0))),
                "severity": str(f_dict.get("severity", "NORMAL")),
                "description": str(f_dict.get("explanation", f_dict.get("description", ""))),
            })

        risk_category = result.get("risk_category", "Low risk")
        # Format risk tier cleanly (e.g., 'LOW', 'MEDIUM', 'HIGH')
        risk_tier = risk_category.upper().replace(" RISK", "")

        return {
            "tx_id": result["transaction_id"],
            "sender_upi": tx_details.get("sender_upi", tx_dict.get("sender_upi")),
            "receiver_upi": tx_details.get("receiver_upi", tx_dict.get("receiver_upi")),
            "amount": float(tx_details.get("amount", tx_dict.get("amount", 0.0))),
            "channel": tx_details.get("channel", tx_dict.get("channel", "UPI_APP")),
            "risk_score": float(result["risk_score"]),
            "risk_tier": risk_tier,
            "risk_category": risk_category,
            "status": result["action_recommendation"],
            "action_recommendation": result["action_recommendation"],
            "primary_factor": explainable.get("primary_reason", "NORMAL_TRANSACTION"),
            "is_flagged": True if risk_category == "High risk" else False,
            "explanations": formatted_explanations,
            "relevant_risk_indicators": explainable.get("recommended_actions", []),
            "alert_id": result.get("alert_id"),
            "evaluated_at": result["evaluated_at"],
        }

    def get_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        risk_tier: str | None = None,
        sender_upi: str | None = None,
        is_flagged: int | None = None,
        search: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        channel: str | None = None,
        status: str | None = None,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """Queries transactions with optional search, date filtering, channel, status, sorting, and pagination."""
        where_clauses: list[str] = []
        params: list[Any] = []

        if risk_tier and risk_tier.strip().upper() != "ALL":
            where_clauses.append("UPPER(risk_tier) = ?")
            params.append(risk_tier.strip().upper())

        if channel and channel.strip().upper() != "ALL":
            where_clauses.append("UPPER(channel) = ?")
            params.append(channel.strip().upper())

        if status and status.strip().upper() != "ALL":
            clean_stat = status.strip().upper()
            if clean_stat == "FLAGGED":
                where_clauses.append("(UPPER(status) = 'FLAGGED' OR is_flagged = 1)")
            else:
                where_clauses.append("UPPER(status) = ?")
                params.append(clean_stat)

        if sender_upi:
            where_clauses.append("LOWER(sender_upi) LIKE ?")
            params.append(f"%{sender_upi.strip().lower()}%")

        if is_flagged is not None:
            where_clauses.append("is_flagged = ?")
            params.append(int(is_flagged))

        if search:
            clean_q = f"%{search.strip().lower()}%"
            where_clauses.append(
                "(LOWER(tx_id) LIKE ? OR LOWER(sender_upi) LIKE ? OR LOWER(receiver_upi) LIKE ? OR LOWER(location_city) LIKE ?)"
            )
            params.extend([clean_q, clean_q, clean_q, clean_q])

        if start_date:
            where_clauses.append("timestamp >= ?")
            params.append(start_date.strip())

        if end_date:
            clean_end = end_date.strip()
            if len(clean_end) == 10:
                clean_end += "T23:59:59"
            where_clauses.append("timestamp <= ?")
            params.append(clean_end)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Total count query
        count_sql = f"SELECT COUNT(*) AS total FROM transactions {where_sql};"
        count_row = query_one(count_sql, tuple(params))
        total = count_row["total"] if count_row else 0

        # Whitelist sort column to prevent SQL injection
        allowed_sort_cols = {
            "timestamp": "timestamp",
            "amount": "amount",
            "risk_score": "risk_score",
            "id": "id",
            "tx_id": "tx_id",
            "created_at": "created_at",
        }
        col = allowed_sort_cols.get(sort_by.lower().strip(), "timestamp")
        direction = "ASC" if sort_order.lower().strip() == "asc" else "DESC"

        # Paginated data query
        data_sql = f"""
            SELECT id, tx_id, sender_upi, receiver_upi, amount, channel, device_id,
                   ip_address, location_city, timestamp, risk_score, risk_tier,
                   status, primary_factor, is_flagged, created_at
            FROM transactions
            {where_sql}
            ORDER BY {col} {direction}, id {direction}
            LIMIT ? OFFSET ?;
        """
        rows = query_all(data_sql, tuple(params + [limit, offset]))

        return rows, total

    def get_transaction_by_id(self, tx_id: str) -> dict[str, Any] | None:
        """Retrieves a single transaction by its tx_id or numeric id, with alert and ML prediction details."""
        clean_id = tx_id.strip()

        # Query by tx_id first, then by numeric id
        row = query_one(
            """
            SELECT id, tx_id, sender_upi, receiver_upi, amount, channel, device_id,
                   ip_address, location_city, timestamp, risk_score, risk_tier,
                   status, primary_factor, is_flagged, created_at
            FROM transactions
            WHERE tx_id = ? OR CAST(id AS TEXT) = ?;
            """,
            (clean_id, clean_id),
        )

        if not row:
            return None

        # Fetch linked alert if available
        alert_row = query_one(
            """
            SELECT alert_id, tx_id, severity, primary_reason, explanations_json,
                   status, reviewed_by, analyst_notes, created_at, updated_at
            FROM fraud_alerts
            WHERE tx_id = ?;
            """,
            (row["tx_id"],),
        )

        alert_dict = None
        explanations = []
        if alert_row:
            alert_dict = dict(alert_row)
            import json
            try:
                raw_expl = json.loads(alert_dict.get("explanations_json", "[]"))
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

        # Fetch linked ML prediction record if available
        pred_row = query_one(
            """
            SELECT prediction_id, tx_id, model_name, model_version, is_anomaly,
                   raw_decision_score, model_risk_score, final_risk_score,
                   risk_category, explanation_summary, detailed_explanations_json,
                   created_at
            FROM model_prediction_records
            WHERE tx_id = ?
            ORDER BY id DESC LIMIT 1;
            """,
            (row["tx_id"],),
        )

        pred_dict = None
        if pred_row:
            pred_dict = dict(pred_row)
            if not explanations and pred_dict.get("detailed_explanations_json"):
                import json
                try:
                    raw_expl = json.loads(pred_dict["detailed_explanations_json"])
                    explanations = [
                        {
                            "factor_name": f.get("factor_name", "SIGNAL"),
                            "weight": float(f.get("impact_weight", f.get("weight", 0.0))),
                            "severity": f.get("severity", "NORMAL"),
                            "description": f.get("explanation", f.get("description", "")),
                        }
                        for f in raw_expl
                    ]
                except Exception:
                    pass

        return {
            "transaction": row,
            "alert": alert_dict,
            "explanations": explanations,
            "prediction": pred_dict,
        }

    def update_transaction_status(self, tx_id: str, status: str, notes: str | None = None) -> bool:
        """Updates transaction status and syncs to linked alert if present."""
        clean_status = status.strip().upper()
        clean_id = tx_id.strip()
        is_flagged = 1 if clean_status in ("FLAGGED", "BLOCKED") else 0

        # Update transaction
        rows_affected = execute_stmt(
            """
            UPDATE transactions 
            SET status = ?, is_flagged = ?
            WHERE tx_id = ? OR CAST(id AS TEXT) = ?;
            """,
            (clean_status, is_flagged, clean_id, clean_id),
        )
        if rows_affected > 0:
            # Sync to fraud_alerts if matching alert exists
            alert_status = clean_status
            if clean_status == "ALLOWED":
                alert_status = "APPROVED"
            execute_stmt(
                """
                UPDATE fraud_alerts
                SET status = ?, analyst_notes = COALESCE(?, analyst_notes), updated_at = CURRENT_TIMESTAMP
                WHERE tx_id = ?;
                """,
                (alert_status, notes, clean_id),
            )
            return True
        return False


# Singleton instance helper
_transaction_service: TransactionService | None = None


def get_transaction_service() -> TransactionService:
    """Returns or initialises the singleton TransactionService."""
    global _transaction_service
    if _transaction_service is None:
        _transaction_service = TransactionService()
    return _transaction_service
