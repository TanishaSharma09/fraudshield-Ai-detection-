"""FraudShield AI - Transactions API Route.

Handles transaction submission, real-time risk evaluation, database persistence,
paginated querying, and single-transaction inspection.
Requires authenticated ANALYST or ADMIN role.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.schemas.transaction import (
    TransactionCreate,
    TransactionEvaluationResponse,
    TransactionListResponse,
    TransactionDetailResponse,
    FeatureExplanation,
    TransactionRecord,
)
from backend.services.transaction_service import get_transaction_service
from backend.api.deps import require_analyst_or_admin

router = APIRouter(tags=["Transactions"])


@router.post(
    "/transactions",
    response_model=TransactionEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit & Evaluate Transaction",
    description="Processes incoming UPI transaction in real-time, persists record, triggers alerts for medium/high risk, and returns explainable scoring. Requires ANALYST or ADMIN role.",
)
def submit_transaction(
    payload: TransactionCreate,
    current_user: dict = Depends(require_analyst_or_admin),
) -> TransactionEvaluationResponse:
    """Evaluates payment, persists to SQLite ledger, and generates alerts if suspicious."""
    try:
        service = get_transaction_service()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Transaction processing service unavailable: {str(e)}",
        )

    try:
        tx_dict = payload.model_dump()
        result = service.create_and_evaluate(tx_dict)

        explanations = [
            FeatureExplanation(
                factor_name=f["factor_name"],
                weight=f["weight"],
                severity=f["severity"],
                description=f["description"],
            )
            for f in result.get("explanations", [])
        ]

        return TransactionEvaluationResponse(
            tx_id=result["tx_id"],
            sender_upi=result["sender_upi"],
            receiver_upi=result["receiver_upi"],
            amount=result["amount"],
            channel=result.get("channel", "UPI_APP"),
            risk_score=result["risk_score"],
            risk_tier=result["risk_tier"],
            risk_category=result["risk_category"],
            status=result["status"],
            action_recommendation=result["action_recommendation"],
            primary_factor=result["primary_factor"],
            is_flagged=result["is_flagged"],
            explanations=explanations,
            relevant_risk_indicators=result.get("relevant_risk_indicators", []),
            alert_id=result.get("alert_id"),
            evaluated_at=result["evaluated_at"],
        )
    except FileNotFoundError as fnf:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Machine learning model is not available: {str(fnf)}",
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation or format error: {str(ve)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction evaluation failed: {str(exc)}",
        )


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Transactions",
    description="Returns a paginated list of evaluated transactions with optional filtering by risk tier, search query, date range, or sorting. Requires ANALYST or ADMIN role.",
)
def list_transactions(
    limit: int = Query(default=50, ge=1, le=500, description="Max transactions to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    risk_tier: str | None = Query(default=None, description="Filter by risk tier (LOW, MEDIUM, HIGH, CRITICAL)"),
    channel: str | None = Query(default=None, description="Filter by payment channel (UPI_APP, QR_CODE, COLLECT_REQUEST, INTENT_FLOW)"),
    status: str | None = Query(default=None, description="Filter by status (ALLOWED, FLAGGED, BLOCKED, UNDER_REVIEW)"),
    sender_upi: str | None = Query(default=None, description="Search by sender UPI VPA substring"),
    is_flagged: int | None = Query(default=None, ge=0, le=1, description="Filter by flagged status (0 or 1)"),
    search: str | None = Query(default=None, description="Search across tx_id, sender_upi, receiver_upi, city"),
    start_date: str | None = Query(default=None, description="Filter transactions after this ISO timestamp"),
    end_date: str | None = Query(default=None, description="Filter transactions before this ISO timestamp"),
    sort_by: str = Query(default="timestamp", description="Sort by: timestamp, amount, risk_score, tx_id"),
    sort_order: str = Query(default="desc", description="Sort order: asc or desc"),
    current_user: dict = Depends(require_analyst_or_admin),
) -> TransactionListResponse:
    """Fetches paginated transactions from SQLite with search, date filter, channel, status, and sort options."""
    service = get_transaction_service()
    rows, total = service.get_transactions(
        limit=limit,
        offset=offset,
        risk_tier=risk_tier,
        sender_upi=sender_upi,
        is_flagged=is_flagged,
        search=search,
        start_date=start_date,
        end_date=end_date,
        channel=channel,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    records = [
        TransactionRecord(
            id=r["id"],
            tx_id=r["tx_id"],
            sender_upi=r["sender_upi"],
            receiver_upi=r["receiver_upi"],
            amount=r["amount"],
            channel=r["channel"],
            device_id=r["device_id"],
            ip_address=r["ip_address"],
            location_city=r["location_city"],
            timestamp=r["timestamp"],
            risk_score=r["risk_score"],
            risk_tier=r["risk_tier"],
            status=r["status"],
            primary_factor=r["primary_factor"],
            is_flagged=r["is_flagged"],
            created_at=r["created_at"],
        )
        for r in rows
    ]

    return TransactionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        transactions=records,
    )


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Transaction by ID",
    description="Retrieves complete transaction details, attached fraud alert, and explainable feature attributions. Requires ANALYST or ADMIN role.",
)
def get_transaction(
    transaction_id: str,
    current_user: dict = Depends(require_analyst_or_admin),
) -> TransactionDetailResponse:
    """Finds a transaction by tx_id or numeric ID, including attached alerts and ML explanations."""
    service = get_transaction_service()
    record = service.get_transaction_by_id(transaction_id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{transaction_id}' was not found in the database.",
        )

    r = record["transaction"]
    tx_model = TransactionRecord(
        id=r["id"],
        tx_id=r["tx_id"],
        sender_upi=r["sender_upi"],
        receiver_upi=r["receiver_upi"],
        amount=r["amount"],
        channel=r["channel"],
        device_id=r["device_id"],
        ip_address=r["ip_address"],
        location_city=r["location_city"],
        timestamp=r["timestamp"],
        risk_score=r["risk_score"],
        risk_tier=r["risk_tier"],
        status=r["status"],
        primary_factor=r["primary_factor"],
        is_flagged=r["is_flagged"],
        created_at=r["created_at"],
    )

    explanations = [
        FeatureExplanation(
            factor_name=f["factor_name"],
            weight=f["weight"],
            severity=f["severity"],
            description=f["description"],
        )
        for f in record.get("explanations", [])
    ]

    return TransactionDetailResponse(
        transaction=tx_model,
        alert=record.get("alert"),
        explanations=explanations,
        prediction=record.get("prediction"),
    )


@router.patch(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_200_OK,
    summary="Update Transaction Status",
    description="Updates transaction status (ALLOWED, APPROVED, BLOCKED, FLAGGED, UNDER_REVIEW) and syncs to linked alert. Requires ANALYST or ADMIN role.",
)
def update_transaction(
    transaction_id: str,
    payload: dict,
    current_user: dict = Depends(require_analyst_or_admin),
):
    """Updates status for a transaction and syncs to linked alert if present."""
    service = get_transaction_service()
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'status' is required.",
        )
    notes = payload.get("notes")
    ok = service.update_transaction_status(transaction_id, new_status, notes)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{transaction_id}' was not found in the database.",
        )
    return {
        "success": True,
        "transaction_id": transaction_id,
        "status": new_status.upper(),
        "notes": notes,
    }
