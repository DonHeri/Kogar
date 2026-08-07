import pytest

from src.models.budget_category import BudgetCategory
from tests.helpers import make_category

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def shared_category() -> BudgetCategory:
    return BudgetCategory(make_category("fijos"), 0, ["member1", "member2"])


@pytest.fixture
def personal_category() -> BudgetCategory:
    return BudgetCategory(make_category("variables"), 0, ["member1"])


# ====================================================
# TESTS: properties
# ====================================================


def test_budget_category_exposes_category_name(shared_category: BudgetCategory) -> None:
    assert shared_category.name == "fijos"


def test_budget_category_is_shared_derives_from_participants(
    shared_category: BudgetCategory,
) -> None:
    """Compartida es tener a más de uno dentro, no un campo aparte que lo diga."""
    assert shared_category.is_shared is True


def test_budget_category_with_one_participant_is_not_shared(
    personal_category: BudgetCategory,
) -> None:
    assert personal_category.is_shared is False


# ====================================================
# TESTS: participantes
# ====================================================


def test_participants_are_normalized() -> None:
    cat = BudgetCategory(make_category("fijos"), 0, ["Member1", "MEMBER2"])

    assert cat.participants == ["member1", "member2"]


def test_adding_an_existing_participant_does_not_duplicate_it() -> None:
    """Da igual cómo se escriba: 'Member1' y 'member1' son el mismo miembro."""
    cat = BudgetCategory(make_category("fijos"), 0, ["member1"])

    cat.add_participant("Member1")

    assert cat.participants == ["member1"]


def test_add_participant_appends_a_new_one() -> None:
    cat = BudgetCategory(make_category("fijos"), 0, ["member1"])

    cat.add_participant("Member2")

    assert cat.participants == ["member1", "member2"]
    assert cat.is_shared is True


def test_has_participant_ignores_case() -> None:
    cat = BudgetCategory(make_category("fijos"), 0, ["member1"])

    assert cat.has_participant("MEMBER1") is True
    assert cat.has_participant("member2") is False


def test_the_category_does_not_share_the_list_it_receives() -> None:
    """Copiar es lo que permite que una hija herede del padre y luego se
    restrinja sin arrastrarlo consigo."""
    original = ["member1"]

    cat = BudgetCategory(make_category("fijos"), 0, original)
    cat.add_participant("member2")

    assert original == ["member1"]


def test_empty_participants_raises_value_error() -> None:
    """Sin nadie dentro, su facturable no se le puede pedir a ningún miembro."""
    with pytest.raises(ValueError, match="participants no puede estar vacío"):
        BudgetCategory(make_category("fijos"), 0, [])


# ====================================================
# TESTS: planned_amount (llega ya en céntimos)
# ====================================================


def test_planned_amount_is_stored_as_received() -> None:
    """La conversión a céntimos vive en los bordes, no aquí."""
    cat = BudgetCategory(make_category("fijos"), 1000, ["member1"])

    assert cat.planned_amount == 1000


# ====================================================
# TESTS: validación de monto
# ====================================================


def test_negative_amount_raises_value_error() -> None:
    with pytest.raises(ValueError):
        BudgetCategory(make_category("fijos"), -5, ["member1"])


def test_boolean_amount_raises_type_error() -> None:
    with pytest.raises(TypeError):
        BudgetCategory(make_category("fijos"), True, ["member1"])
