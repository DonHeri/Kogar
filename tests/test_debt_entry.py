from datetime import datetime, timedelta

import pytest

from src.models.debt_entry import DebtEntry


def test_debt_entry_valid_creation():
    entry = DebtEntry(amount_cents=5000, description="Pago préstamo")
    assert entry.amount_cents == 5000
    assert entry.description == "Pago préstamo"


def test_debt_entry_default_date_is_now():
    before = datetime.now()
    entry = DebtEntry(amount_cents=100)
    after = datetime.now()
    assert before <= entry.date <= after


def test_debt_entry_zero_amount_raises():
    with pytest.raises(ValueError, match="0"):
        DebtEntry(amount_cents=0)


def test_debt_entry_negative_amount_is_valid():
    # El signo lo gestiona DebtAccount, igual que SavingEntry
    entry = DebtEntry(amount_cents=-100)
    assert entry.amount_cents == -100


def test_debt_entry_future_date_raises():
    future = datetime.now() + timedelta(days=1)
    with pytest.raises(ValueError, match="futura"):
        DebtEntry(amount_cents=100, date=future)


def test_debt_entry_past_date_is_valid():
    past = datetime.now() - timedelta(days=30)
    entry = DebtEntry(amount_cents=100, date=past)
    assert entry.date == past
