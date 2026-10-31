"""FraudShield AI - Alerts API Route.

Manages actionable fraud alerts for security operations (SOC):
- Lists active and historical alert queues with severity, status, and search filters.
- Retrieves detailed alert records with transparent factor explanations.
- Handles SOC analyst triage reviews (APPROVE, BLOCK, DISMISS, REVIEWED) with audit logging.
- Provides real-time Server-Sent Events (SSE) stream for live alerts dispatch.
- Requires ANALYST or ADMIN role.
"""

import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from backend.schemas.alert import (
    FraudAlertResponse,
    AlertListResponse,
    AlertActionRequest,
)
from backend.schemas.transaction import FeatureExplanation
from backend.services.alert_service import get_alert_service
from backend.api.deps import require_analyst_or_admin

router = APIRouter(tags=["Alerts & SOC Triage"])


def _format_alert_response(r: dict) -> FraudAlertResponse:
    """Helper to cleanly instantiate FraudAlertResponse from alert dict."""
    explanations = [
        FeatureExplanation(
            factor_name=f["factor_name"],
            weight=f["weight"],
            severity=f["severity"],
            description=f["description"],
        )
        for f in r.get("explanations", [])
    ]
    return FraudAlertResponse(
        id=r["id"],
        alert_id=r["alert_id"],
        tx_id=r["tx_id"],
        amount=r.get("amount"),
        sender_upi=r.get("sender_upi"),
        receiver_upi=r.get("receiver_upi"),
        channel=r.get("channel"),
        location_city=r.get("location_city"),
        risk_score=r.get("risk_score"),
        risk_category=r.get("risk_category"),
        tx_timestamp=r.get("tx_timestamp"),
        device_id=r.get("device_id"),
        tx_status=r.get("tx_status"),
        severity=r["severity"],
        primary_reason=r["primary_reason"],
        explanations=explanations,
        status=r["status"],
        reviewed_by=r.get("reviewed_by"),
        analyst_notes=r.get("analyst_notes"),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


@router.get(
    "/alerts",
    response_model=AlertListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Fraud Alerts",
    description="Fetches paginated fraud alerts enriched with payment details, filterable by status (PENDING, REVIEWED, APPROVED, BLOCKED, DISMISSED), severity, and search keywords. Requires ANALYST or ADMIN role.",
)
def list_alerts(
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status (PENDING, REVIEWED, APPROVED, BLOCKED, DISMISSED)"),
    severity: str | None = Query(default=None, description="Filter by severity (MEDIUM, HIGH, CRITICAL)"),
    search: str | None = Query(default=None, description="Search by Alert ID, Tx ID, VPA or primary reason"),
    limit: int = Query(default=50, ge=1, le=500, description="Max alerts to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    current_user: dict = Depends(require_analyst_or_admin),
) -> AlertListResponse:
    """Lists alerts from SQLite joined with transaction details."""
    service = get_alert_service()
    rows, total = service.get_alerts(
        status=status_filter,
        severity=severity,
        search=search,
        limit=limit,
        offset=offset,
    )

    alert_models = [_format_alert_response(r) for r in rows]

    return AlertListResponse(
        total=total,
        limit=limit,
        offset=offset,
        alerts=alert_models,
    )


@router.get(
    "/alerts/summary",
    status_code=status.HTTP_200_OK,
    summary="Get Alert Summary Statistics",
    description="Returns aggregate counts of total, pending, reviewed, approved, and blocked alerts across the entire database.",
)
def get_alert_summary(
    current_user: dict = Depends(require_analyst_or_admin),
) -> dict:
    """Returns database-level alert count metrics for the SOC dashboard ribbon."""
    service = get_alert_service()
    return service.get_alert_summary()


@router.get(
    "/alerts/stream",
    summary="Real-time Alerts Server-Sent Events (SSE)",
    description="Streams real-time alert updates and snapshot queues via SSE for instant dashboard reactivity.",
)
async def stream_alerts(request: Request):
    """Streams live alerts snapshot and updates to connected frontend clients."""
    async def event_generator():
        service = get_alert_service()
        while True:
            if await request.is_disconnected():
                break
            try:
                alerts, total = service.get_alerts(limit=15, offset=0)
                event_payload = {
                    "type": "ALERTS_SYNC",
                    "total": total,
                    "pending_count": sum(1 for a in alerts if a.get("status") == "PENDING"),
                    "alerts": [
                        {
                            "alert_id": a["alert_id"],
                            "tx_id": a["tx_id"],
                            "amount": a.get("amount"),
                            "sender_upi": a.get("sender_upi"),
                            "receiver_upi": a.get("receiver_upi"),
                            "risk_score": a.get("risk_score"),
                            "risk_category": a.get("risk_category"),
                            "severity": a["severity"],
                            "primary_reason": a["primary_reason"],
                            "status": a["status"],
                            "created_at": a["created_at"],
                            "updated_at": a["updated_at"],
                        }
                        for a in alerts
                    ],
                }
                yield f"data: {json.dumps(event_payload)}\n\n"
            except Exception:
                pass
            await asyncio.sleep(3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/alerts/{alert_id}",
    response_model=FraudAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Alert Details",
    description="Retrieves a specific fraud alert with full transparent factor explanations and payment details. Requires ANALYST or ADMIN role.",
)
def get_alert(
    alert_id: str,
    current_user: dict = Depends(require_analyst_or_admin),
) -> FraudAlertResponse:
    """Finds an alert by its alert_id or database id."""
    service = get_alert_service()
    r = service.get_alert_by_id(alert_id)

    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' was not found.",
        )

    return _format_alert_response(r)


@router.post(
    "/alerts/{alert_id}/review",
    response_model=FraudAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Alert as Reviewed",
    description="Transitions an alert status to REVIEWED, recording the analyst identity and optional review notes. Requires ANALYST or ADMIN role.",
)
def mark_alert_reviewed(
    alert_id: str,
    payload: AlertActionRequest | None = None,
    current_user: dict = Depends(require_analyst_or_admin),
) -> FraudAlertResponse:
    """Convenience action to mark an alert as reviewed."""
    service = get_alert_service()
    reviewer = current_user.get("username", "SOC-Analyst")
    notes = payload.notes if payload else "Alert reviewed by SOC analyst"

    updated = service.update_alert_action(
        alert_id=alert_id,
        action="REVIEWED",
        notes=notes,
        reviewed_by=reviewer,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' was not found.",
        )

    return _format_alert_response(updated)


@router.patch(
    "/alerts/{alert_id}",
    response_model=FraudAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Triage Alert (SOC Action)",
    description="Updates alert status (APPROVE, BLOCK, DISMISS, REVIEWED) with investigator notes and updates transaction status. Requires ANALYST or ADMIN role.",
)
def update_alert(
    alert_id: str,
    payload: AlertActionRequest,
    current_user: dict = Depends(require_analyst_or_admin),
) -> FraudAlertResponse:
    """Transitions alert status and records analyst action audit trail."""
    service = get_alert_service()

    # Use reviewer from payload or default to authenticated username
    reviewer = payload.reviewed_by if payload.reviewed_by != "SOC-Analyst-1" else current_user.get("username", "SOC-Analyst")

    updated = service.update_alert_action(
        alert_id=alert_id,
        action=payload.action,
        notes=payload.notes,
        reviewed_by=reviewer,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' was not found.",
        )

    return _format_alert_response(updated)
