# tests/test_budget_category.py
from src.models.budget import BudgetCategory
import pytest

# ====================================================
# FIXTURES
# ====================================================

@pytest.fixture
def budget():
    """Categoría con 1000€ presupuestados"""
    return BudgetCategory("Alquiler", 1000)

# ====================================================
# TESTS: Creación de Presupuesto específico
# ====================================================
def test_create_valid_budget_category():
    # Act
    budget1 = BudgetCategory("Test", 500)

    # Arrange
    assert budget1.name == "Test"
    assert budget1.spent == 0.0
    assert budget1.planned_amount == 500
    assert isinstance(budget1.member_contributions, dict)
    


def test_negative_budget_must_raise_error():
    with pytest.raises(
        ValueError, match="El monto presupuestado no puede ser negativo"
    ):
        budget1 = BudgetCategory("Test", -500)

# ====================================================
# TESTS: register_payment(name: str, amount:float)
# ====================================================
def test_register_payment_adds_amount_to_member(budget):
    budget.register_payment("Amanda", 100)
    
    assert budget.member_contributions["Amanda"] == 100
    assert budget.spent == 100


def test_register_payment_accumulates_multiple_payments(budget):
    budget.register_payment("Amanda", 100)
    budget.register_payment("Amanda", 50)
    
    assert budget.member_contributions["Amanda"] == 150
    assert budget.spent == 150


def test_register_payment_tracks_multiple_members(budget):
    budget.register_payment("Amanda", 100)
    budget.register_payment("Heri", 200)
    
    assert budget.member_contributions["Amanda"] == 100
    assert budget.member_contributions["Heri"] == 200
    assert budget.spent == 300


def test_register_payment_zero_raises_error(budget):
    with pytest.raises(ValueError, match="El pago debe ser superior a 0"):
        budget.register_payment("Amanda", 0)


def test_register_payment_negative_raises_error(budget):
    with pytest.raises(ValueError, match="El pago debe ser superior a 0"):
        budget.register_payment("Amanda", -50)


def test_create_budget_negative_planned_raises_error():
    with pytest.raises(ValueError, match="El monto presupuestado no puede ser negativo"):
        BudgetCategory("Alquiler", -100)


def test_create_budget_zero_planned_raises_error():
    with pytest.raises(ValueError, match="El monto presupuestado no puede ser negativo"):
        BudgetCategory("Alquiler", 0)
        

# ====================================================
# REMAINING 
# ====================================================

def test_remaining_returns_difference_between_planned_and_spent(budget):
    budget.register_payment("Amanda", 300)
    assert budget.remaining() == 700


def test_remaining_returns_zero_when_fully_paid(budget):
    budget.register_payment("Amanda", 1000)
    assert budget.remaining() == 0


def test_remaining_returns_negative_when_overpaid(budget):
    budget.register_payment("Amanda", 1200)
    assert budget.remaining() == -200


# ====================================================
# MEMBER_PENDING
# ====================================================
def test_member_pending_returns_amount_owed_minus_paid(budget):
    budget.register_payment("Amanda", 100)
    assert budget.member_pending("Amanda", 500) == 400


def test_member_pending_when_member_hasnt_paid(budget):
    assert budget.member_pending("Heri", 300) == 300


def test_member_pending_when_overpaid(budget):
    budget.register_payment("Amanda", 600)
    assert budget.member_pending("Amanda", 500) == -100
