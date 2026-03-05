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
    b = Budget()
    b.set_standard_categories()
    return b

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
    budget_rent.register_payment("Amanda", 10000)  # 100€ en céntimos

    assert budget_rent.member_contributions["Amanda"] == 10000
    assert budget_rent.spent == 10000


def test_register_payment_accumulates_multiple_payments(budget_rent):
    budget_rent.register_payment("Amanda", 10000)  # 100€ en céntimos
    budget_rent.register_payment("Amanda", 5000)   # 50€ en céntimos

    assert budget_rent.member_contributions["Amanda"] == 15000
    assert budget_rent.spent == 15000


def test_register_payment_tracks_multiple_members(budget_rent):
    budget_rent.register_payment("Amanda", 10000)  # 100€ en céntimos
    budget_rent.register_payment("Heri", 20000)    # 200€ en céntimos

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
    budget_rent.register_payment("Amanda", 30000)  # 300€ en céntimos
    assert budget_rent.remaining() == 70000


def test_remaining_returns_zero_when_fully_paid(budget_rent):
    budget_rent.register_payment("Amanda", 100000)  # 1000€ en céntimos
    assert budget_rent.remaining() == 0


def test_remaining_returns_negative_when_overpaid(budget_rent):
    budget_rent.register_payment("Amanda", 120000)  # 1200€ en céntimos
    assert budget_rent.remaining() == -20000


# ====================================================
# MEMBER_PENDING
# ====================================================
def test_member_pending_returns_amount_owed_minus_paid(budget_rent):
    budget_rent.register_payment("Amanda", 10000)  # 100€ en céntimos
    assert budget_rent.member_pending("Amanda", 50000) == 40000


def test_member_pending_when_member_hasnt_paid(budget_rent):
    assert budget_rent.member_pending("Heri", 30000) == 30000


def test_member_pending_when_overpaid(budget_rent):
    budget_rent.register_payment("Amanda", 60000)  # 600€ en céntimos
    assert budget_rent.member_pending("Amanda", 50000) == -10000


# ====================================================
# ADD_CATEGORY
# ====================================================


def test_add_category_creates_new_category(budget):
    budget.add_category("educacion")
    
    assert "educacion" in budget.get_categories_list()
    assert budget.categories["educacion"].planned_amount == 0


def test_add_category_normalizes_name(budget):
    budget.add_category("  EDUCACIÓN  ")
    
    assert "educación" in budget.get_categories_list()


def test_add_category_already_exists_raises_error(budget):
    with pytest.raises(ValueError, match="La categoría ya existe"):
        budget.add_category("fijos")


def test_add_category_adds_to_library_if_unknown(budget):
    from src.models.category_library import CategoryLibrary
    
    # Asegurarse que "nueva_categoria" no existe en library
    budget.add_category("nueva_categoria")
    
    # Verificar que se agregó a CategoryLibrary
    assert CategoryLibrary.is_known("nueva_categoria")


# ====================================================
# DELETE_BUDGET_CATEGORY
# ====================================================


def test_delete_budget_category_removes_category(budget):
    budget.delete_budget_category("fijos")
    
    assert "fijos" not in budget.get_categories_list()


def test_delete_budget_category_not_exists_raises_error(budget):
    with pytest.raises(ValueError, match="La categoría debe estar creada"):
        budget.delete_budget_category("inexistente")


def test_delete_budget_category_with_spent_raises_error(budget_rent):
    budget_rent.register_payment("Amanda", 100)
    budget = Budget()
    budget.categories["fijos"] = budget_rent
    
    with pytest.raises(ValueError, match="ya tiene pagos registrados"):
        budget.delete_budget_category("fijos")


def test_delete_budget_category_without_spent_succeeds(budget):
    # Categoría sin gastos se puede eliminar
    budget.set_budget("fijos", 1000)
    budget.delete_budget_category("fijos")
    
    assert "fijos" not in budget.get_categories_list()
