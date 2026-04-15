import pytest

from src.models.budget_category import BudgetCategory
from src.models.constants import CategoryBehavior

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def shared_category():
    return BudgetCategory("fijos", 0, CategoryBehavior.SHARED)


@pytest.fixture
def personal_category():
    return BudgetCategory("variables", 0, CategoryBehavior.PERSONAL)


# ====================================================
# TESTS: behavior default
# ====================================================


def test_budget_category_default_behavior_is_shared():
    """Sin pasar behavior, el default es SHARED"""
    cat = BudgetCategory("cualquiera", 0)
    assert cat.behavior == CategoryBehavior.SHARED


def test_budget_category_shared_behavior(shared_category):
    assert shared_category.behavior == CategoryBehavior.SHARED


def test_budget_category_personal_behavior(personal_category):
    assert personal_category.behavior == CategoryBehavior.PERSONAL


# ====================================================
# TESTS: set_behavior
# ====================================================


def test_set_behavior_changes_behavior(shared_category):
    shared_category.set_behavior(CategoryBehavior.PERSONAL)
    assert shared_category.behavior == CategoryBehavior.PERSONAL


def test_set_behavior_to_shared(personal_category):
    personal_category.set_behavior(CategoryBehavior.SHARED)
    assert personal_category.behavior == CategoryBehavior.SHARED
