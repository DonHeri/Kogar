# tests/test_budget.py
import pytest

from src.models.budget import Budget
from src.models.budget_category import BudgetCategory
from tests.helpers import make_category

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def budget() -> Budget:
    b = Budget()
    b.set_standard_categories(["member1", "member2"])
    return b


# ====================================================
# TESTS: Creación de Presupuesto específico
# ====================================================
def test_create_valid_budget_category() -> None:
    # Arrange & Act
    budget1 = BudgetCategory(make_category("Test"), 50000, ["member1", "member2"])

    # Assert
    assert budget1.name == "Test"
    assert budget1.planned_amount == 50000


def test_negative_budget_must_raise_error() -> None:
    with pytest.raises(
        ValueError, match="El monto presupuestado no puede ser negativo"
    ):
        budget1 = BudgetCategory(
            category=make_category("Test"),
            planned_amount=-500,
            participants=["member1"],
        )


# ====================================================
# TESTS: Budget: `set_budget`(self, category: str, amount: float)
# ====================================================
def test_set_budget_updates_category_amount(budget: Budget) -> None:
    budget.set_planned_amount("fijos", 100000)
    assert budget.categories["fijos"].planned_amount == 100000


def test_set_budget_updates_multiple_categories(budget: Budget) -> None:
    budget.set_planned_amount("fijos", 100000)
    budget.set_planned_amount("variables", 50000)

    assert budget.categories["fijos"].planned_amount == 100000
    assert budget.categories["variables"].planned_amount == 50000


def test_set_budget_invalid_category_raises_error(budget: Budget) -> None:
    with pytest.raises(ValueError, match="La categoría debe estar creada"):
        budget.set_planned_amount("invalida", 100)


def test_set_budget_negative_amount_raises_error(budget: Budget) -> None:
    with pytest.raises(ValueError, match="Monto del presupuesto debe ser superior a 0"):
        budget.set_planned_amount("fijos", -100)


# ====================================================
# TESTS: participantes de una categoría
# ====================================================


def test_a_child_inherits_the_participants_of_its_parent(budget: Budget) -> None:
    budget.add_category("vivienda", parent="fijos")

    assert budget.categories["vivienda"].participants == ["member1", "member2"]


def test_restricting_a_child_leaves_its_parent_untouched(budget: Budget) -> None:
    """El límite está en que heredar no puede ser compartir la misma lista: si
    lo fuera, restringir la hija restringiría al padre por detrás."""
    budget.add_category("gimnasio", parent="fijos")

    budget.categories["gimnasio"].participants.remove("member2")

    assert budget.categories["gimnasio"].participants == ["member1"]
    assert budget.categories["fijos"].participants == ["member1", "member2"]


def test_a_child_cannot_add_participants_its_parent_does_not_have(
    budget: Budget,
) -> None:
    """Un tercero dentro de la hija haría que el techo del padre repartiera
    entre gente que él no reparte."""
    with pytest.raises(ValueError, match="no tiene: member3"):
        budget.add_category("pesas", ["member1", "member3"], parent="fijos")


def test_a_child_cannot_be_widened_after_it_is_created(budget: Budget) -> None:
    """La otra puerta a la misma regla: crear estrecho y ampliar después."""
    budget.add_category("gimnasio", ["member1"], parent="fijos")

    with pytest.raises(ValueError, match="no tiene: member3"):
        budget.add_participant_to_budget_category("member3", "gimnasio")

    assert budget.categories["gimnasio"].participants == ["member1"]


def test_a_child_may_recover_a_participant_its_parent_still_has(
    budget: Budget,
) -> None:
    """Restringir no es irreversible: member2 sigue estando en el padre."""
    budget.add_category("gimnasio", ["member1"], parent="fijos")

    budget.add_participant_to_budget_category("member2", "gimnasio")

    assert budget.categories["gimnasio"].participants == ["member1", "member2"]


def test_a_root_may_take_in_anyone(budget: Budget) -> None:
    """Una raíz no tiene padre que la limite."""
    budget.add_participant_to_budget_category("member3", "fijos")

    assert "member3" in budget.categories["fijos"].participants


def test_the_subset_rule_does_not_depend_on_how_the_name_is_written(
    budget: Budget,
) -> None:
    """member2 está en el padre como 'member2'; declararlo 'MEMBER2' es el mismo."""
    budget.add_category("gimnasio", ["MEMBER2"], parent="fijos")

    assert budget.categories["gimnasio"].participants == ["member2"]


def test_a_root_without_participants_raises(budget: Budget) -> None:
    with pytest.raises(ValueError, match="al menos un participante"):
        budget.add_category("ocio")


def test_a_root_with_an_empty_list_raises(budget: Budget) -> None:
    """Lista vacía y lista ausente son el mismo error, no dos caminos."""
    with pytest.raises(ValueError, match="al menos un participante"):
        budget.add_category("ocio", [])


# ====================================================
# ADD_CATEGORY
# ====================================================


def test_add_category_creates_new_category(budget: Budget) -> None:
    budget.add_category("educacion", ["member1", "member2"])

    assert "educacion" in budget.get_category_names()
    assert budget.categories["educacion"].planned_amount == 0


def test_add_category_normalizes_name(budget: Budget) -> None:
    budget.add_category("  EDUCACIÓN  ", ["member1", "member2"])

    assert "educación" in budget.get_category_names()


def test_add_category_already_exists_raises_error(budget: Budget) -> None:
    with pytest.raises(ValueError, match="La categoría ya existe"):
        budget.add_category("fijos", ["member1", "member2"])


def test_add_category_adds_to_library_if_unknown(budget: Budget) -> None:
    budget.add_category("nueva_categoria", ["member1", "member2"])

    assert budget.library.is_known("nueva_categoria")


# ====================================================
# TESTS: Jerarquía padre/hija
# ====================================================


def test_add_category_with_parent_sets_parent(budget: Budget) -> None:
    budget.add_category("vivienda", parent="fijos")

    assert budget.categories["vivienda"].parent == "fijos"


def test_add_category_with_nonexistent_parent_raises_error(budget: Budget) -> None:
    with pytest.raises(ValueError, match="La categoría debe estar creada"):
        budget.add_category("vivienda", parent="inexistente")


def test_get_child_total_planned_sums_children(budget: Budget) -> None:
    budget.add_category("vivienda", parent="fijos")
    budget.add_category("suministros", parent="fijos")
    budget.set_planned_amount("vivienda", 30000)
    budget.set_planned_amount("suministros", 20000)

    assert budget.get_child_total_planned("fijos") == 50000


# ====================================================
# DELETE_BUDGET_CATEGORY
# ====================================================


def test_delete_budget_category_removes_category(budget: Budget) -> None:
    budget.delete_budget_category("fijos")

    assert "fijos" not in budget.get_category_names()


def test_delete_budget_category_not_exists_raises_error(budget: Budget) -> None:
    with pytest.raises(ValueError, match="La categoría debe estar creada"):
        budget.delete_budget_category("inexistente")


def test_delete_budget_category_succeeds(budget: Budget) -> None:
    # Cualquier categoría se puede eliminar (Budget no conoce gastos)
    budget.set_planned_amount("fijos", 100000)
    budget.delete_budget_category("fijos")

    assert "fijos" not in budget.get_category_names()


# ====================================================
# GET_CATEGORY_BUDGET
# ====================================================


def test_get_category_budget_is_correct(budget: Budget) -> None:
    budget.set_planned_amount("fijos", 10000)

    result = budget.get_planned_amount("fijos")

    assert result == 10000


def test_get_category_budget_normalizes_name(budget: Budget) -> None:
    budget.set_planned_amount("fijos", 50000)

    result = budget.get_planned_amount("  FIJOS  ")

    assert result == 50000


def test_get_category_budget_invalid_category_raises_error(budget: Budget) -> None:
    with pytest.raises(ValueError, match="La categoría debe estar creada"):
        budget.get_planned_amount("inexistente")
