"""FraudShield AI - Simulation API Route.

Enables interactive testing and live demonstration of fraud detection capabilities:
- One-click trigger presets for known attack scenarios (SIM Swap, Phishing, Velocity Burst).
- Batch stream generation to simulate live transaction traffic on the SOC dashboard.
"""

from datetime import datetime, timezone
from typing import Any, Literal
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.schemas.transaction import TransactionEvaluationResponse, FeatureExplanation
from backend.services.transaction_service import get_transaction_service
from backend.api.deps import require_analyst_or_admin

router = APIRouter(tags=["Simulation & Demo"])

PresetType = Literal[
    "NORMAL_PAYMENT",
    "UNUSUALLY_LARGE",
    "VELOCITY_BURST",
    "NEW_RECIPIENT",
    "UNUSUAL_PATTERN",
    "GROCERY_NORMAL",
    "AFFLUENT_HIGH_VALUE",
    "SIM_SWAP_DRAIN",
    "COLLECT_PHISHING",
]


class PresetRequest(BaseModel):
    """Request to trigger a pre-configured behavioral scenario."""
    preset: PresetType = Field(
        ...,
        examples=["NORMAL_PAYMENT", "UNUSUALLY_LARGE", "VELOCITY_BURST", "NEW_RECIPIENT", "UNUSUAL_PATTERN"],
        description="Scenario preset to simulate (NORMAL_PAYMENT, UNUSUALLY_LARGE, VELOCITY_BURST, NEW_RECIPIENT, UNUSUAL_PATTERN, GROCERY_NORMAL, AFFLUENT_HIGH_VALUE, SIM_SWAP_DRAIN, COLLECT_PHISHING)",
    )


class StreamResponse(BaseModel):
    """Response returned when streaming a batch of transactions."""
    batch_size: int
    evaluated_count: int
    flagged_count: int
    transactions: list[TransactionEvaluationResponse]


@router.post(
    "/simulation/preset",
    response_model=TransactionEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Preset Scenario",
    description="Fires a realistic UPI payment scenario with known risk attributes (e.g., SIM Swap, Velocity burst, Grocery).",
)
def trigger_preset(
    payload: PresetRequest,
    current_user: dict = Depends(require_analyst_or_admin),
) -> TransactionEvaluationResponse:
    """Simulates a specific fraud or legitimate payment scenario."""
    service = get_transaction_service()
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()
    rand_id = np.random.randint(100000, 999999)

    preset_map: dict[str, dict[str, Any]] = {
        "NORMAL_PAYMENT": {
            "tx_id": f"TXN-SIM-NORM-{rand_id}",
            "sender_upi": "arjun.sharma@okaxis",
            "receiver_upi": "grocery.store@icici",
            "amount": float(np.random.randint(180, 850)),
            "channel": "UPI_APP",
            "device_id": "DEV-XIAOMI-12",
            "ip_address": "49.207.180.12",
            "location_city": "Bengaluru",
            "timestamp": now_iso,
            "velocity_15m": 1.0,
            "time_since_last_sec": 7200.0,
            "is_new_recipient": 0,
            "is_new_device": 0,
        },
        "UNUSUALLY_LARGE": {
            "tx_id": f"TXN-SIM-LARGE-{rand_id}",
            "sender_upi": "arjun.sharma@okaxis",
            "receiver_upi": f"luxury.jewels.{rand_id}@hdfcbank",
            "amount": float(np.random.randint(75000, 98000)),
            "channel": "INTENT_FLOW",
            "device_id": "DEV-XIAOMI-12",
            "ip_address": "49.207.180.12",
            "location_city": "Mumbai",
            "timestamp": now_iso,
            "velocity_15m": 1.0,
            "time_since_last_sec": 86400.0,
            "is_new_recipient": 1,
            "is_new_device": 0,
        },
        "VELOCITY_BURST": {
            "tx_id": f"TXN-SIM-BURST-{rand_id}",
            "sender_upi": "priya.patel@oksbi",
            "receiver_upi": f"burner.wallet.{rand_id}@paytm",
            "amount": float(np.random.randint(8500, 14500)),
            "channel": "COLLECT_REQUEST",
            "device_id": "DEV-ONEPLUS-11",
            "ip_address": "103.21.144.10",
            "location_city": "Ahmedabad",
            "timestamp": now_iso,
            "velocity_15m": 8.0,
            "time_since_last_sec": 12.0,
            "is_new_recipient": 1,
            "is_new_device": 0,
        },
        "NEW_RECIPIENT": {
            "tx_id": f"TXN-SIM-NEWRECIP-{rand_id}",
            "sender_upi": "rahul.kumar@paytm",
            "receiver_upi": f"crypto.mule.unverified.{rand_id}@ybl",
            "amount": float(np.random.randint(28000, 48000)),
            "channel": "UPI_APP",
            "device_id": "DEV-SAMSUNG-S23",
            "ip_address": "157.34.120.45",
            "location_city": "Delhi",
            "timestamp": now_iso,
            "velocity_15m": 2.0,
            "time_since_last_sec": 1800.0,
            "is_new_recipient": 1,
            "is_new_device": 0,
        },
        "UNUSUAL_PATTERN": {
            "tx_id": f"TXN-SIM-UNUSUAL-{rand_id}",
            "sender_upi": "sneha.reddy@okicici",
            "receiver_upi": f"fraud.drain.{rand_id}@ybl",
            "amount": 88000.0,
            "channel": "INTENT_FLOW",
            "device_id": "DEV-UNKNOWN-ROOTED-IMEI",
            "ip_address": "185.220.101.5",
            "location_city": "Kolkata",
            "timestamp": now_utc.replace(hour=3, minute=15).isoformat(),
            "velocity_15m": 5.0,
            "time_since_last_sec": 25.0,
            "is_new_recipient": 1,
            "is_new_device": 1,
        },
        # Backward-compatible presets
        "GROCERY_NORMAL": {
            "tx_id": f"UPI-SIM-GROCERY-{rand_id}",
            "sender_upi": "arjun.sharma@okaxis",
            "receiver_upi": "grocery.store@icici",
            "amount": 450.0,
            "channel": "QR_CODE",
            "device_id": "DEV-XIAOMI-12",
            "ip_address": "49.207.180.12",
            "location_city": "Mumbai",
            "timestamp": now_iso,
            "velocity_15m": 1.0,
            "time_since_last_sec": 7200.0,
            "is_new_recipient": 0,
            "is_new_device": 0,
        },
        "AFFLUENT_HIGH_VALUE": {
            "tx_id": f"UPI-SIM-AFFLUENT-{rand_id}",
            "sender_upi": "vikram.malhotra@okhdfcbank",
            "receiver_upi": "luxury.jewels@hdfcbank",
            "amount": 35000.0,
            "channel": "UPI_APP",
            "device_id": "DEV-IPHONE-15PRO",
            "ip_address": "157.34.120.45",
            "location_city": "Mumbai",
            "timestamp": now_iso,
            "velocity_15m": 1.0,
            "time_since_last_sec": 86400.0,
            "is_new_recipient": 0,
            "is_new_device": 0,
        },
        "SIM_SWAP_DRAIN": {
            "tx_id": f"UPI-SIM-SWAP-{rand_id}",
            "sender_upi": "sneha.reddy@okicici",
            "receiver_upi": f"fraud.cashout.{rand_id}@ybl",
            "amount": 88000.0,
            "channel": "UPI_APP",
            "device_id": "DEV-UNKNOWN-ROOTED-ANDROID",
            "ip_address": "185.220.101.5",
            "location_city": "Kolkata",
            "timestamp": now_utc.replace(hour=3, minute=15).isoformat(),
            "velocity_15m": 4.0,
            "time_since_last_sec": 30.0,
            "is_new_recipient": 1,
            "is_new_device": 1,
        },
        "COLLECT_PHISHING": {
            "tx_id": f"UPI-SIM-PHISH-{rand_id}",
            "sender_upi": "rahul.verma@okaxis",
            "receiver_upi": f"lottery.claim.dept.{rand_id}@paytm",
            "amount": 49000.0,
            "channel": "COLLECT_REQUEST",
            "device_id": "DEV-SAMSUNG-A54",
            "ip_address": "45.154.255.80",
            "location_city": "Bengaluru",
            "timestamp": now_iso,
            "velocity_15m": 2.0,
            "time_since_last_sec": 60.0,
            "is_new_recipient": 1,
            "is_new_device": 0,
        },
    }

    tx_data = preset_map.get(payload.preset)
    if not tx_data:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {payload.preset}")

    result = service.create_and_evaluate(tx_data)

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


@router.post(
    "/simulation/stream",
    response_model=StreamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Stream Simulated Transactions",
    description="Generates a batch of randomized legitimate and suspicious transactions to populate live SOC telemetry.",
)
def stream_transactions(
    count: int = Query(default=10, ge=1, le=50, description="Number of transactions to generate and score"),
    current_user: dict = Depends(require_analyst_or_admin),
) -> StreamResponse:
    """Generates and evaluates a mixed batch of live transactions."""
    service = get_transaction_service()
    presets: list[PresetType] = [
        "NORMAL_PAYMENT",
        "NORMAL_PAYMENT",
        "NORMAL_PAYMENT",
        "UNUSUALLY_LARGE",
        "VELOCITY_BURST",
        "NEW_RECIPIENT",
        "UNUSUAL_PATTERN",
        "GROCERY_NORMAL",
        "AFFLUENT_HIGH_VALUE",
        "SIM_SWAP_DRAIN",
        "COLLECT_PHISHING",
    ]

    evaluated_items = []
    flagged_count = 0

    for _ in range(count):
        chosen_preset = np.random.choice(presets)
        req = PresetRequest(preset=chosen_preset)
        item = trigger_preset(req, current_user=current_user)
        evaluated_items.append(item)
        if item.is_flagged:
            flagged_count += 1

    return StreamResponse(
        batch_size=count,
        evaluated_count=len(evaluated_items),
        flagged_count=flagged_count,
        transactions=evaluated_items,
    )
