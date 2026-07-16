from datetime import datetime

import pytest

from src.models.debt_bucket import DebtBucket

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def car_bucket():
    """Deuda personal con cuota fija declarada por el usuario."""
    return DebtBucket(
        debt_bucket_name="Deuda Coche",
        principal_cents=2000000,
        owner="heri",
        installment_cents=100000,
    )


# ====================================================
# TESTS: Creation — valid
# ====================================================


def test_creation_valid(car_bucket):
    assert car_bucket.name == "Deuda Coche"
    assert car_bucket.principal_cents == 2000000
    assert car_bucket.owner == "heri"
    assert car_bucket.installment_cents == 100000
    assert car_bucket.total_paid == 0
    assert car_bucket.remaining_balance == 2000000
    assert car_bucket.is_closed is False


def test_creation_defaults_start_date_to_today(car_bucket):
    assert car_bucket.start_date.date() == datetime.today().date()


def test_creation_with_explicit_start_date():
    start = datetime(2025, 1, 1)
    bucket = DebtBucket("B", 100000, "heri", 10000, start_date=start)
    assert bucket.start_date == start


def test_id_is_generated(car_bucket):
    assert car_bucket.id is not None


def test_each_bucket_has_unique_id():
    b1 = DebtBucket("B1", 100000, "heri", 10000)
    b2 = DebtBucket("B2", 100000, "heri", 10000)
    assert b1.id != b2.id


# ====================================================
# TESTS: Creation — invalid
# ====================================================


def test_installment_is_mandatory():
    with pytest.raises(TypeError):
        DebtBucket("B", 100000, "heri")  # type: ignore[call-arg]


def test_empty_bucket_name_raises():
    with pytest.raises(ValueError):
        DebtBucket("", 100000, "heri", 10000)


def test_empty_owner_raises():
    with pytest.raises(ValueError, match="owner"):
        DebtBucket("B", 100000, "", 10000)


def test_principal_cents_zero_raises():
    with pytest.raises(ValueError):
        DebtBucket("B", 0, "heri", 10000)


def test_principal_cents_negative_raises():
    with pytest.raises(ValueError):
        DebtBucket("B", -100, "heri", 10000)


def test_principal_cents_float_raises():
    principal: object = 100.0
    with pytest.raises(TypeError):
        DebtBucket("B", principal, "heri", 10000)  # type: ignore[arg-type]


def test_principal_cents_bool_raises():
    with pytest.raises(TypeError):
        DebtBucket("B", True, "heri", 10000)


def test_installment_cents_zero_raises():
    with pytest.raises(ValueError):
        DebtBucket("B", 100000, "heri", 0)


def test_installment_cents_negative_raises():
    with pytest.raises(ValueError):
        DebtBucket("B", 100000, "heri", -100)


# ====================================================
# TESTS: pay
# ====================================================


def test_pay_increases_total_paid(car_bucket):
    car_bucket.pay(50000, "heri")
    assert car_bucket.total_paid == 50000


def test_pay_accumulates(car_bucket):
    car_bucket.pay(30000, "heri")
    car_bucket.pay(20000, "heri")
    assert car_bucket.total_paid == 50000


def test_pay_decreases_remaining_balance(car_bucket):
    car_bucket.pay(50000, "heri")
    assert car_bucket.remaining_balance == 2000000 - 50000


def test_pay_with_date(car_bucket):
    date = datetime(2026, 3, 1)
    car_bucket.pay(50000, "heri", date=date)
    assert car_bucket._entries[0].date == date


def test_pay_raises_if_member_not_owner(car_bucket):
    with pytest.raises(ValueError, match="pertenece"):
        car_bucket.pay(50000, "amanda")


def test_pay_invalid_amount_zero_raises(car_bucket):
    with pytest.raises(ValueError):
        car_bucket.pay(0, "heri")


def test_pay_invalid_amount_negative_raises(car_bucket):
    with pytest.raises(ValueError):
        car_bucket.pay(-100, "heri")


def test_pay_overpayment_is_allowed(car_bucket):
    """Sobrepago confirmado sin restricción (ver refactor_ecosistemas_TODO.md, T1)"""
    car_bucket.pay(2500000, "heri")
    assert car_bucket.total_paid == 2500000
    assert car_bucket.remaining_balance == -500000
    assert car_bucket.is_closed is True


def test_advancing_money_reduces_remaining_installments(car_bucket):
    """Adelantar dinero = un pago mayor que la cuota; reduce las cuotas restantes."""
    car_bucket.pay(300000, "heri")  # 3 cuotas de golpe
    assert car_bucket.remaining_installments == 17  # 20 - 3


# ====================================================
# TESTS: remove_payment
# ====================================================


def test_remove_payment_removes_entry(car_bucket):
    car_bucket.pay(30000, "heri")
    car_bucket.pay(20000, "heri")
    entry_id = car_bucket._entries[0].id

    car_bucket.remove_payment(entry_id)

    assert car_bucket.total_paid == 20000


def test_remove_payment_raises_if_id_not_found(car_bucket):
    with pytest.raises(ValueError, match="No se ha encontrado"):
        car_bucket.remove_payment("id-inexistente")


# ====================================================
# TESTS: is_closed
# ====================================================


def test_is_closed_false_when_balance_remains(car_bucket):
    car_bucket.pay(1999999, "heri")
    assert car_bucket.is_closed is False


def test_is_closed_true_when_balance_reaches_zero(car_bucket):
    car_bucket.pay(2000000, "heri")
    assert car_bucket.is_closed is True


# ====================================================
# TESTS: set_installment
# ====================================================


def test_set_installment_overrides_previous(car_bucket):
    car_bucket.set_installment(120000)
    assert car_bucket.installment_cents == 120000


def test_set_installment_invalid_raises(car_bucket):
    with pytest.raises(ValueError):
        car_bucket.set_installment(0)


# ====================================================
# TESTS: next_installment
# ====================================================


def test_next_installment_equals_user_installment(car_bucket):
    assert car_bucket.next_installment == 100000


def test_next_installment_capped_at_remaining_on_last_payment(car_bucket):
    """Cuando el saldo restante es menor que la cuota, la última cuota se ajusta al saldo."""
    car_bucket.pay(1950000, "heri")  # quedan 50000, menos que la cuota de 100000
    assert car_bucket.next_installment == 50000


# ====================================================
# TESTS: remaining_installments
# ====================================================


def test_remaining_installments_at_start(car_bucket):
    assert car_bucket.remaining_installments == 20  # 2000000 / 100000


def test_remaining_installments_after_partial_payment(car_bucket):
    car_bucket.pay(150000, "heri")  # queda 1850000
    # ceil(1850000 / 100000) = 19 (18 completas + una cola)
    assert car_bucket.remaining_installments == 19


def test_remaining_installments_zero_when_closed(car_bucket):
    car_bucket.pay(2000000, "heri")
    assert car_bucket.remaining_installments == 0
