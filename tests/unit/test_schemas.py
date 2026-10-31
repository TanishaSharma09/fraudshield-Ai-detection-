"""Unit tests for Pydantic transaction, alert, and analytics schemas."""

import pytest
from backend.schemas.transaction import TransactionCreate


def test_valid_upi_transaction():
    tx = TransactionCreate(
        sender_upi="arjun.sharma@okaxis",
        receiver_upi="merchant.groceries@icici",
        amount=1450.50,
        channel="UPI_APP",
        device_id="DEV-XIAOMI-12",
        location_city="Mumbai",
    )
    assert tx.sender_upi == "arjun.sharma@okaxis"
    assert tx.amount == 1450.50


def test_invalid_upi_format():
    with pytest.raises(ValueError, match="Invalid UPI format"):
        TransactionCreate(
            sender_upi="not_a_valid_vpa",
            receiver_upi="receiver@bank",
            amount=500.0,
            device_id="DEV-1",
        )


def test_invalid_amount_negative_or_zero():
    with pytest.raises(ValueError):
        TransactionCreate(
            sender_upi="sender@okaxis",
            receiver_upi="receiver@icici",
            amount=0.0,
            device_id="DEV-1",
        )
