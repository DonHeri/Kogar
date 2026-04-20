from datetime import datetime

import pytest

from src.models.debt_account import DebtAccount


@pytest.fixture
def account():
    return DebtAccount("amanda")


def test_debt_account_valid_creation(account):
    assert account.member_name == "amanda"
    assert account.total_paid == 0


def test_debt_account_empty_name_raises():
    with pytest.raises(ValueError):
        DebtAccount("")


def test_debt_account_whitespace_name_raises():
    with pytest.raises(ValueError):
        DebtAccount("   ")


def test_pay_registers_entry(account):
    account.pay(10000)
    assert account.total_paid == 10000


def test_pay_accumulates(account):
    account.pay(10000)
    account.pay(5000)
    assert account.total_paid == 15000


def test_pay_with_float_raises_type_error(account):
    with pytest.raises(TypeError):
        account.pay(100.0)


def test_pay_with_bool_raises_type_error(account):
    with pytest.raises(TypeError):
        account.pay(True)


def test_pay_with_negative_raises(account):
    with pytest.raises(ValueError):
        account.pay(-100)


def test_pay_zero_raises(account):
    with pytest.raises(ValueError):
        account.pay(0)


def test_get_history_returns_copy(account):
    account.pay(1000)
    history = account.get_history()
    assert len(history) == 1
    history.clear()
    assert len(account.get_history()) == 1


def test_get_monthly_summary_filters_by_month(account):
    target = datetime(2024, 3, 15)
    other = datetime(2024, 4, 10)
    account.pay(5000, date=target)
    account.pay(3000, date=other)

    summary = account.get_monthly_summary(month=3, year=2024)
    assert summary["paid"] == 5000
    assert summary["payments_count"] == 1


def test_get_monthly_summary_empty_month(account):
    summary = account.get_monthly_summary(month=1, year=2000)
    assert summary["paid"] == 0
    assert summary["payments_count"] == 0
