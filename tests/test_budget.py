# tests/test_budget_category.py
from src.models.budget import Budget
from src.models.budget_category import BudgetCategory
import pytest

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def budget_rent():
    """Categoría con 1000€ presupuestados"""
    return BudgetCategory("fijos", 1000)


@pytest.fixture
def budget():
    """Presupuestos"""
    return Budget()


# ====================================================
# TESTS: Creación de Presupuesto específico
# ====================================================
def test_create_valid_budget_category():
    # Act
    budget1 = BudgetCategory("Test", 500)

    # Arrange
    assert budget1.name == "Test"
    assert budget1.spent == 0
    assert budget1.planned_amount == 50000
    assert isinstance(budget1.member_contributions, dict)


def test_negative_budget_must_raise_error():
    with pytest.raises(
        ValueError, match="El monto presupuestado no puede ser negativo"
    ):
        budget1 = BudgetCategory(name="Test", planned_amount=-500)


# ====================================================
# TESTS: Budget: `set_budget`(self, category: str, amount: float)
# ====================================================
def test_set_budget_updates_category_amount(budget):
    budget.set_budget("fijos", 1000)
    assert budget.categories["fijos"].planned_amount == 100000


def test_set_budget_updates_multiple_categories(budget):
    budget.set_budget("fijos", 1000)
    budget.set_budget("variables", 500)

    assert budget.categories["fijos"].planned_amount == 100000
    assert budget.categories["variables"].planned_amount == 50000


def test_set_budget_invalid_category_raises_error(budget):
    with pytest.raises(ValueError, match="La categoría debe estar creada"):
        budget.set_budget("invalida", 100)


def test_set_budget_negative_amount_raises_error(budget):
    with pytest.raises(ValueError, match="Monto del presupuesto debe ser superior a 0"):
        budget.set_budget("fijos", -100)


# ====================================================
# TESTS: register_payment(name: str, amount:float)
# ====================================================
def test_register_payment_adds_amount_to_member(budget_rent):
    budget_rent.register_payment("Amanda", 100)

    assert budget_rent.member_contributions["Amanda"] == 10000
    assert budget_rent.spent == 10000


def test_register_payment_accumulates_multiple_payments(budget_rent):
    budget_rent.register_payment("Amanda", 100)
    budget_rent.register_payment("Amanda", 50)

    assert budget_rent.member_contributions["Amanda"] == 15000
    assert budget_rent.spent == 15000


def test_register_payment_tracks_multiple_members(budget_rent):
    budget_rent.register_payment("Amanda", 100)
    budget_rent.register_payment("Heri", 200)

    assert budget_rent.member_contributions["Amanda"] == 10000
    assert budget_rent.member_contributions["Heri"] == 20000
    assert budget_rent.spent == 30000


def test_register_payment_zero_raises_error(budget_rent):
    with pytest.raises(ValueError, match="El pago debe ser superior a 0"):
        budget_rent.register_payment("Amanda", 0)


def test_register_payment_negative_raises_error(budget_rent):
    with pytest.raises(ValueError, match="El pago debe ser superior a 0"):
        budget_rent.register_payment("Amanda", -50)


def test_create_budget_negative_planned_raises_error():
    with pytest.raises(
        ValueError, match="El monto presupuestado no puede ser negativo"
    ):
        BudgetCategory("fijos", -100)


# ====================================================
# REMAINING
# ====================================================


def test_remaining_returns_difference_between_planned_and_spent(budget_rent):
    budget_rent.register_payment("Amanda", 300)
    assert budget_rent.remaining() == 70000


def test_remaining_returns_zero_when_fully_paid(budget_rent):
    budget_rent.register_payment("Amanda", 1000)
    assert budget_rent.remaining() == 0


def test_remaining_returns_negative_when_overpaid(budget_rent):
    budget_rent.register_payment("Amanda", 1200)
    assert budget_rent.remaining() == -20000


# ====================================================
# MEMBER_PENDING
# ====================================================
def test_member_pending_returns_amount_owed_minus_paid(budget_rent):
    budget_rent.register_payment("Amanda", 100)
    assert budget_rent.member_pending("Amanda", 50000) == 40000


def test_member_pending_when_member_hasnt_paid(budget_rent):
    assert budget_rent.member_pending("Heri", 30000) == 30000


def test_member_pending_when_overpaid(budget_rent):
    budget_rent.register_payment("Amanda", 600)
    assert budget_rent.member_pending("Amanda", 50000) == -10000
