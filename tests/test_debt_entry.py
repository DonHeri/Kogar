from datetime import datetime, timedelta

import pytest

from src.models.debt_entry import DebtEntry


def test_debt_entry_valid_creation() -> None:
    entry = DebtEntry(member_name="ana", amount_cents=5000, description="Pago préstamo")
    assert entry.amount_cents == 5000
    assert entry.description == "Pago préstamo"


def test_debt_entry_default_date_is_now() -> None:
    before = datetime.now()
    entry = DebtEntry(member_name="ana", amount_cents=100)
    after = datetime.now()
    assert before <= entry.date <= after


def test_debt_entry_zero_amount_raises() -> None:
    with pytest.raises(ValueError, match="0"):
        DebtEntry(member_name="ana", amount_cents=0)


def test_debt_entry_negative_amount_raises() -> None:
    # Deuda no tiene retiro: todo pago es positivo, sin excepción
    with pytest.raises(ValueError, match="0"):
        DebtEntry(member_name="ana", amount_cents=-100)


def test_debt_entry_future_date_raises() -> None:
    future = datetime.now() + timedelta(days=1)
    with pytest.raises(ValueError, match="futura"):
        DebtEntry(member_name="ana", amount_cents=100, date=future)


def test_debt_entry_past_date_is_valid() -> None:
    past = datetime.now() - timedelta(days=30)
    entry = DebtEntry(member_name="ana", amount_cents=100, date=past)
    assert entry.date == past


def test_debt_entry_generates_id_when_none() -> None:
    entry = DebtEntry(member_name="ana", amount_cents=100)
    assert entry.id is not None


def test_debt_entry_keeps_given_id() -> None:
    from uuid import uuid4

    given_id = uuid4()
    entry = DebtEntry(member_name="ana", amount_cents=100, id=given_id)
    assert entry.id == given_id
