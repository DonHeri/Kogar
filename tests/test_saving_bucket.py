from datetime import datetime
from uuid import UUID

import pytest

from src.models.constants import SavingScope
from src.models.saving_bucket import SavingBucket

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def bucket_personal():
    return SavingBucket(
        bucket_name="MacBook Pro",
        goal_cents=220000,
        scope=SavingScope.PERSONAL,
        owners=["heri"],
    )


@pytest.fixture
def bucket_shared():
    return SavingBucket(
        bucket_name="Fondo de emergencia",
        goal_cents=600000,
        scope=SavingScope.SHARED,
        owners=["amanda", "heri"],
        description="3 meses de gastos fijos cubiertos",
    )


@pytest.fixture
def bucket_shared_with_deadline():
    return SavingBucket(
        bucket_name="Viaje a Japón",
        goal_cents=280000,
        scope=SavingScope.SHARED,
        owners=["amanda", "heri"],
        deadline=datetime(2027, 4, 23),
    )


# ====================================================
# TESTS: Creation — valid
# ====================================================


def test_creation_personal_valid(bucket_personal):
    assert bucket_personal.bucket_name == "MacBook Pro"
    assert bucket_personal.goal == 220000
    assert bucket_personal.scope == SavingScope.PERSONAL
    assert bucket_personal.owners == ["heri"]
    assert bucket_personal.balance == 0
    assert bucket_personal.deadline is None
    assert bucket_personal.description == ""


def test_creation_shared_valid(bucket_shared):
    assert bucket_shared.bucket_name == "Fondo de emergencia"
    assert bucket_shared.scope == SavingScope.SHARED
    assert len(bucket_shared.owners) == 2
    assert bucket_shared.description == "3 meses de gastos fijos cubiertos"


def test_creation_with_deadline(bucket_shared_with_deadline):
    assert bucket_shared_with_deadline.deadline == datetime(2027, 4, 23)


def test_id_is_uuid(bucket_personal):
    assert isinstance(bucket_personal.id, UUID)


def test_each_bucket_has_unique_id():
    b1 = SavingBucket("B1", 10000, SavingScope.PERSONAL, ["heri"])
    b2 = SavingBucket("B2", 10000, SavingScope.PERSONAL, ["heri"])
    assert b1.id != b2.id


# ====================================================
# TESTS: Creation — invalid scope/owners
# ====================================================


def test_personal_bucket_with_two_owners_raises():
    with pytest.raises(ValueError, match="Personal"):
        SavingBucket("B", 10000, SavingScope.PERSONAL, ["amanda", "heri"])


def test_shared_bucket_with_one_owner_raises():
    with pytest.raises(ValueError, match="compartido"):
        SavingBucket("B", 10000, SavingScope.SHARED, ["amanda"])


def test_shared_bucket_with_empty_owners_raises():
    with pytest.raises(ValueError, match="compartido"):
        SavingBucket("B", 10000, SavingScope.SHARED, [])


# ====================================================
# TESTS: Creation — invalid goal_cents
# ====================================================


def test_goal_cents_zero_raises():
    with pytest.raises(ValueError):
        SavingBucket("B", 0, SavingScope.PERSONAL, ["heri"])


def test_goal_cents_negative_raises():
    with pytest.raises(ValueError):
        SavingBucket("B", -100, SavingScope.PERSONAL, ["heri"])


def test_goal_cents_float_raises():
    goal: object = 100.0
    with pytest.raises(TypeError):
        SavingBucket("B", goal, SavingScope.PERSONAL, ["heri"])  # type: ignore[arg-type]


def test_goal_cents_bool_raises():
    with pytest.raises(TypeError):
        SavingBucket("B", True, SavingScope.PERSONAL, ["heri"])


# ====================================================
# TESTS: deposit
# ====================================================


def test_deposit_increases_balance(bucket_personal):
    bucket_personal.deposit(5000, "heri")
    assert bucket_personal.balance == 5000


def test_deposit_accumulates(bucket_personal):
    bucket_personal.deposit(3000, "heri")
    bucket_personal.deposit(2000, "heri")
    assert bucket_personal.balance == 5000


def test_deposit_shared_by_different_members(bucket_shared):
    bucket_shared.deposit(10000, "amanda")
    bucket_shared.deposit(8000, "heri")
    assert bucket_shared.balance == 18000


def test_deposit_with_date(bucket_personal):
    date = datetime(2026, 3, 1)
    bucket_personal.deposit(5000, "heri", date=date)
    assert bucket_personal._entries[0].date == date


def test_deposit_raises_if_member_not_in_bucket(bucket_personal):
    with pytest.raises(ValueError, match="no pertenece"):
        bucket_personal.deposit(5000, "amanda")


def test_deposit_invalid_amount_zero_raises(bucket_personal):
    with pytest.raises(ValueError):
        bucket_personal.deposit(0, "heri")


def test_deposit_invalid_amount_negative_raises(bucket_personal):
    with pytest.raises(ValueError):
        bucket_personal.deposit(-100, "heri")


# ====================================================
# TESTS: withdraw
# ====================================================


def test_withdraw_decreases_balance(bucket_personal):
    bucket_personal.deposit(10000, "heri")
    bucket_personal.withdraw(4000, "heri")
    assert bucket_personal.balance == 6000


def test_withdraw_raises_if_insufficient_balance_personal(bucket_personal):
    bucket_personal.deposit(3000, "heri")
    with pytest.raises(ValueError, match="Saldo insuficiente"):
        bucket_personal.withdraw(5000, "heri")


def test_withdraw_shared_raises_if_member_balance_insufficient(bucket_shared):
    """En bucket compartido, el retiro se valida contra el saldo individual del miembro"""
    bucket_shared.deposit(10000, "amanda")
    bucket_shared.deposit(2000, "heri")
    with pytest.raises(ValueError, match="Saldo insuficiente"):
        bucket_shared.withdraw(5000, "heri")


def test_withdraw_shared_succeeds_if_member_has_enough(bucket_shared):
    bucket_shared.deposit(10000, "amanda")
    bucket_shared.deposit(8000, "heri")
    bucket_shared.withdraw(5000, "heri")
    assert bucket_shared.balance == 13000


def test_withdraw_raises_if_member_not_in_bucket(bucket_personal):
    bucket_personal.deposit(5000, "heri")
    with pytest.raises(ValueError, match="no pertenece"):
        bucket_personal.withdraw(1000, "amanda")


def test_withdraw_with_date(bucket_personal):
    date_dep = datetime(2026, 1, 10)
    date_wit = datetime(2026, 2, 5)
    bucket_personal.deposit(10000, "heri", date=date_dep)
    bucket_personal.withdraw(3000, "heri", date=date_wit)
    assert bucket_personal._entries[1].date == date_wit


# ====================================================
# TESTS: balance_by_member
# ====================================================


def test_balance_by_member_empty(bucket_shared):
    result = bucket_shared.balance_by_member
    assert result == {"amanda": 0, "heri": 0}


def test_balance_by_member_after_deposits(bucket_shared):
    bucket_shared.deposit(10000, "amanda")
    bucket_shared.deposit(5000, "heri")
    result = bucket_shared.balance_by_member
    assert result["amanda"] == 10000
    assert result["heri"] == 5000


def test_balance_by_member_after_withdraw(bucket_shared):
    bucket_shared.deposit(10000, "amanda")
    bucket_shared.withdraw(3000, "amanda")
    result = bucket_shared.balance_by_member
    assert result["amanda"] == 7000
    assert result["heri"] == 0


# ====================================================
# TESTS: __str__
# ====================================================


def test_str_contains_bucket_name(bucket_personal):
    assert "MacBook Pro" in str(bucket_personal)


def test_str_contains_scope_personal(bucket_personal):
    assert "Personal" in str(bucket_personal)


def test_str_contains_scope_shared(bucket_shared):
    assert "Compartido" in str(bucket_shared)


def test_str_contains_description_when_present(bucket_shared):
    assert "meses de gastos fijos" in str(bucket_shared)


def test_str_no_description_when_absent(bucket_personal):
    output = str(bucket_personal)
    assert "Desc." not in output


def test_str_contains_deadline_when_present(bucket_shared_with_deadline):
    assert "23/04/2027" in str(bucket_shared_with_deadline)


def test_str_no_deadline_when_absent(bucket_personal):
    output = str(bucket_personal)
    assert "Deadline" not in output


def test_str_shows_progress(bucket_personal):
    bucket_personal.deposit(110000, "heri")
    output = str(bucket_personal)
    assert "1100.00" in output
    assert "2200.00" in output
    assert "50%" in output
