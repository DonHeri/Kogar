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
    assert budget1.planned_amount == 50000


def test_negative_budget_must_raise_error():
    with pytest.raises(
        ValueError, match="El monto presupuestado no puede ser negativo"
    ):
        budget1 = BudgetCategory(name="Test", planned_amount=-500)


# ====================================================
# TESTS: Budget: `set_budget`(self, category: str, amount: float)
# ====================================================
def test_set_budget_updates_category_amount(budget):
    budget.set_budget("fijos", 100000)
    assert budget.categories["fijos"].planned_amount == 100000


def test_set_budget_updates_multiple_categories(budget):
    budget.set_budget("fijos", 100000)
    budget.set_budget("variables", 50000)

    assert budget.categories["fijos"].planned_amount == 100000
    assert budget.categories["variables"].planned_amount == 50000


def test_set_budget_invalid_category_raises_error(budget):
    with pytest.raises(ValueError, match="La categoría debe estar creada"):
        budget.set_budget("invalida", 100)


def test_set_budget_negative_amount_raises_error(budget):
    with pytest.raises(ValueError, match="Monto del presupuesto debe ser superior a 0"):
        budget.set_budget("fijos", -100)


# ====================================================
# TESTS: CategoryBehavior heredado desde librería
# ====================================================


def test_standard_categories_inherit_behavior_from_library(budget):
    from src.models.constants import CategoryBehavior

    assert budget.categories["fijos"].behavior == CategoryBehavior.SHARED
    assert budget.categories["variables"].behavior == CategoryBehavior.PERSONAL
    assert budget.categories["reserva"].behavior == CategoryBehavior.PERSONAL


def test_add_known_category_inherits_behavior(budget):
    from src.models.constants import CategoryBehavior

    budget.add_category("ocio")
    assert budget.categories["ocio"].behavior == CategoryBehavior.PERSONAL


def test_add_unknown_category_defaults_to_shared(budget):
    from src.models.constants import CategoryBehavior

    budget.add_category("nueva_custom")
    assert budget.categories["nueva_custom"].behavior == CategoryBehavior.SHARED


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
    budget.add_category("nueva_categoria")

    assert budget.library.is_known("nueva_categoria")


# ====================================================
# DELETE_BUDGET_CATEGORY
# ====================================================


def test_delete_budget_category_removes_category(budget):
    budget.delete_budget_category("fijos")

    assert "fijos" not in budget.get_categories_list()


def test_delete_budget_category_not_exists_raises_error(budget):
    with pytest.raises(ValueError, match="La categoría debe estar creada"):
        budget.delete_budget_category("inexistente")


def test_delete_budget_category_succeeds(budget):
    # Cualquier categoría se puede eliminar (Budget no conoce gastos)
    budget.set_budget("fijos", 100000)
    budget.delete_budget_category("fijos")

    assert "fijos" not in budget.get_categories_list()


# ====================================================
# GET_CATEGORY_LIST
# ====================================================


def test_get_category_budget_is_correct(budget):
    budget.set_budget("fijos", 10000)

    result = budget.get_category_budget("fijos")

    assert result == 10000


def test_get_category_budget_normalizes_name(budget):
    budget.set_budget("fijos", 50000)

    result = budget.get_category_budget("  FIJOS  ")

    assert result == 50000

def test_get_category_budget_invalid_category_raises_error(budget):
    with pytest.raises(ValueError, match="La categoría debe estar creada"):
        budget.get_category_budget("inexistente")

