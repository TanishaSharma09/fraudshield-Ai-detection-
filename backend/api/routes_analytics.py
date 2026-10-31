"""FraudShield AI - Analytics API Route.

Provides aggregated operational KPIs, risk distribution tiers,
hourly fraud velocity, amount distributions, velocity bursts,
ground-truth vs anomaly metrics, model evaluation metrics,
and RFC-4180 compliant CSV exports for transactions and alerts.
Accessible exclusively to users with the ADMIN role.
"""

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, Query, Response, status

from backend.schemas.analytics import AnalyticsOverview
from backend.services.analytics_service import get_analytics_service
from backend.api.deps import require_admin, require_analyst_or_admin
from ml_model.behavioural.graph_analyzer import get_graph_analyzer
from ml_model.behavioural.baseline_tracker import get_baseline_tracker
from database.connection import query_all, query_one

router = APIRouter(tags=["Analytics & Forensics KPIs"])


@router.get(
    "/analytics",
    response_model=AnalyticsOverview,
    status_code=status.HTTP_200_OK,
    summary="Get Analytics & Metrics Overview (ADMIN Only)",
    description=(
        "Returns aggregate statistics, risk tier distribution, hourly trends, "
        "amount distributions, transaction velocity bursts, fraud vs legitimate breakdown, "
        "and true model evaluation metrics. Supports filtering by date range and risk tier."
    ),
)
@router.get(
    "/analytics/metrics",
    response_model=AnalyticsOverview,
    include_in_schema=False,
)
def get_analytics(
    start_date: str | None = Query(
        None,
        description="ISO-8601 start date (e.g. 2026-10-01 or 2026-10-01T00:00:00Z)",
    ),
    end_date: str | None = Query(
        None,
        description="ISO-8601 end date (e.g. 2026-10-31 or 2026-10-31T23:59:59Z)",
    ),
    risk_tier: str | None = Query(
        None,
        description="Filter by risk tier: ALL, LOW, MEDIUM, HIGH, CRITICAL",
    ),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> AnalyticsOverview:
    """Calculates operational KPIs and visualization payloads strictly from stored database records."""
    service = get_analytics_service()
    overview = service.get_overview(
        start_date=start_date,
        end_date=end_date,
        risk_tier=risk_tier,
    )
    return AnalyticsOverview(**overview)


@router.get(
    "/analytics/export/transactions",
    status_code=status.HTTP_200_OK,
    summary="Export Filtered Transactions to CSV (ADMIN Only)",
    description="Streams RFC-4180 formatted CSV containing stored transaction records, risk scores, and primary factors.",
)
def export_transactions_csv(
    start_date: str | None = Query(None, description="Filter transactions starting from this date"),
    end_date: str | None = Query(None, description="Filter transactions up to this date"),
    risk_tier: str | None = Query(None, description="Filter by risk tier: ALL, LOW, MEDIUM, HIGH, CRITICAL"),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> Response:
    """Generates and streams an RFC-4180 CSV export of transaction ledger."""
    service = get_analytics_service()
    csv_content = service.export_transactions_csv(
        start_date=start_date,
        end_date=end_date,
        risk_tier=risk_tier,
    )
    filename = f"fraudshield_transactions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get(
    "/analytics/export/alerts",
    status_code=status.HTTP_200_OK,
    summary="Export Filtered Fraud Alerts to CSV (ADMIN Only)",
    description="Streams RFC-4180 formatted CSV containing fraud alerts queue, analyst triage states, and notes.",
)
def export_alerts_csv(
    status_filter: str | None = Query(None, alias="status", description="Filter by status: PENDING, UNDER_REVIEW, RESOLVED, DISMISSED"),
    severity: str | None = Query(None, description="Filter by severity: MEDIUM, HIGH, CRITICAL"),
    start_date: str | None = Query(None, description="Filter alerts created after this date"),
    end_date: str | None = Query(None, description="Filter alerts created before this date"),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> Response:
    """Generates and streams an RFC-4180 CSV export of fraud alerts."""
    service = get_analytics_service()
    csv_content = service.export_alerts_csv(
        status=status_filter,
        severity=severity,
        start_date=start_date,
        end_date=end_date,
    )
    filename = f"fraudshield_alerts_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get(
    "/analytics/network-graph",
    status_code=status.HTTP_200_OK,
    summary="Get Account Relationship Network Graph",
    description="Constructs directed graph topology of transactions between accounts, detecting mule hubs and repeated interactions.",
)
def get_network_graph(
    min_risk_score: float = Query(0.0, description="Filter edges by minimum risk score"),
    only_suspicious: bool = Query(False, description="Filter for suspicious interaction links only"),
    limit: int = Query(500, description="Maximum recent transactions to analyze"),
    current_user: dict[str, Any] = Depends(require_analyst_or_admin),
) -> dict[str, Any]:
    """Generates account relationship network graph with nodes, edges, and cluster metrics."""
    analyzer = get_graph_analyzer()
    return analyzer.build_graph_from_db(
        min_risk_score=min_risk_score,
        only_suspicious=only_suspicious,
        limit=limit,
    )


@router.get(
    "/analytics/behavioural/users",
    status_code=status.HTTP_200_OK,
    summary="List Profiled Senders for Behavioural Inspection",
    description="Returns distinct sender VPAs with their transaction counts stored in the database.",
)
def get_behavioural_users(
    current_user: dict[str, Any] = Depends(require_analyst_or_admin),
) -> list[dict[str, Any]]:
    """Returns top active senders for interactive baseline inspection."""
    rows = query_all(
        """
        SELECT sender_upi, COUNT(*) AS tx_count, MAX(timestamp) AS last_active
        FROM transactions
        WHERE sender_upi IS NOT NULL AND TRIM(sender_upi) != ''
        GROUP BY sender_upi
        ORDER BY tx_count DESC
        LIMIT 50;
        """
    )
    return [dict(r) for r in rows]


@router.get(
    "/analytics/behavioural/profile",
    status_code=status.HTTP_200_OK,
    summary="Get User Baseline Profile and Feature Deviations",
    description="Computes leak-free empirical historical baseline for a specific sender VPA.",
)
def get_behavioural_profile(
    sender_upi: str = Query(..., description="Sender UPI VPA identifier"),
    current_user: dict[str, Any] = Depends(require_analyst_or_admin),
) -> dict[str, Any]:
    """Returns empirical user baseline profile with known devices, recipients, and recent history."""
    clean_sender = sender_upi.strip().lower()
    now_utc = datetime.now(timezone.utc).isoformat()
    tracker = get_baseline_tracker()
    baseline = tracker.get_user_baseline_from_db(clean_sender, as_of_timestamp=now_utc)

    # Query recent 5 transactions for this user
    recent_rows = query_all(
        """
        SELECT tx_id, receiver_upi, amount, channel, device_id, timestamp, risk_score, risk_tier, status
        FROM transactions
        WHERE LOWER(sender_upi) = ?
        ORDER BY timestamp DESC
        LIMIT 5;
        """,
        (clean_sender,),
    )

    return {
        "sender_upi": baseline.sender_upi,
        "as_of_timestamp": baseline.as_of_timestamp,
        "total_prior_transactions": baseline.total_prior_transactions,
        "avg_amount": round(baseline.avg_amount, 2),
        "std_amount": round(baseline.std_amount, 2),
        "min_amount": round(baseline.min_amount, 2),
        "max_amount": round(baseline.max_amount, 2),
        "daily_frequency_mean": round(baseline.daily_frequency_mean, 2),
        "known_devices": sorted(list(baseline.known_devices)),
        "known_recipients": sorted(list(baseline.known_recipients)),
        "recent_transactions": [dict(r) for r in recent_rows],
    }


@router.get(
    "/analytics/behavioural/metrics",
    status_code=status.HTTP_200_OK,
    summary="Get Behavioural Anomaly Counters and Graph Summary",
    description="Returns aggregate counts of velocity bursts, amount outliers, novel devices, and suspicious clusters.",
)
def get_behavioural_metrics(
    current_user: dict[str, Any] = Depends(require_analyst_or_admin),
) -> dict[str, Any]:
    """Returns database-derived behavioural forensic metrics."""
    users_cnt = query_one("SELECT COUNT(DISTINCT sender_upi) AS c FROM transactions WHERE sender_upi IS NOT NULL AND TRIM(sender_upi) != '';")
    bursts_cnt = query_one(
        """
        SELECT COUNT(*) AS c FROM fraud_alerts 
        WHERE LOWER(primary_reason) LIKE '%velocity%' 
           OR LOWER(primary_reason) LIKE '%burst%' 
           OR LOWER(primary_reason) LIKE '%rapid%' 
           OR LOWER(primary_reason) LIKE '%spike%';
        """
    )
    outliers_cnt = query_one(
        """
        SELECT COUNT(*) AS c FROM fraud_alerts 
        WHERE LOWER(primary_reason) LIKE '%amount%' 
           OR LOWER(primary_reason) LIKE '%large%' 
           OR LOWER(primary_reason) LIKE '%surge%' 
           OR LOWER(primary_reason) LIKE '%deviation%';
        """
    )
    novel_cnt = query_one(
        """
        SELECT COUNT(*) AS c FROM fraud_alerts 
        WHERE LOWER(primary_reason) LIKE '%device%' 
           OR LOWER(primary_reason) LIKE '%hardware%' 
           OR LOWER(primary_reason) LIKE '%sim%' 
           OR LOWER(primary_reason) LIKE '%fingerprint%'
           OR LOWER(primary_reason) LIKE '%recipient%';
        """
    )

    analyzer = get_graph_analyzer()
    graph_res = analyzer.build_graph_from_db(only_suspicious=True, limit=200)
    summary = graph_res.get("summary", {})

    return {
        "total_profiled_users": users_cnt["c"] if users_cnt else 0,
        "velocity_bursts_detected": bursts_cnt["c"] if bursts_cnt else 0,
        "amount_outliers_detected": outliers_cnt["c"] if outliers_cnt else 0,
        "novel_device_attempts": novel_cnt["c"] if novel_cnt else 0,
        "suspicious_account_clusters": summary.get("mule_hubs_detected", 0),
        "repeated_pairs_count": summary.get("repeated_pairs", 0),
        "circular_routing_count": summary.get("circular_flows_count", 0),
    }

