import pytest

from src.models.budget_category import BudgetCategory
from tests.helpers import make_category

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def shared_category() -> BudgetCategory:
    return BudgetCategory(make_category("fijos", is_shared=True), 0)


@pytest.fixture
def personal_category() -> BudgetCategory:
    return BudgetCategory(make_category("variables", is_shared=False), 0)


# ====================================================
# TESTS: properties delegadas a Category
# ====================================================


def test_budget_category_exposes_category_name(shared_category: BudgetCategory) -> None:
    assert shared_category.name == "fijos"


def test_budget_category_is_shared_delegates_to_category(
    shared_category: BudgetCategory,
) -> None:
    assert shared_category.is_shared is True


def test_budget_category_personal_is_not_shared(
    personal_category: BudgetCategory,
) -> None:
    assert personal_category.is_shared is False


# ====================================================
# TESTS: planned_amount (se guarda en céntimos)
# ====================================================


def test_planned_amount_stored_in_cents() -> None:
    cat = BudgetCategory(make_category("fijos"), 10.0)
    assert cat.planned_amount == 1000


# ====================================================
# TESTS: validación de monto
# ====================================================


def test_negative_amount_raises_value_error() -> None:
    with pytest.raises(ValueError):
        BudgetCategory(make_category("fijos"), -5.0)


def test_boolean_amount_raises_type_error() -> None:
    with pytest.raises(TypeError):
        BudgetCategory(make_category("fijos"), True)
