import pytest
from src.models.member import Member
from src.models.household import Household
from src.models.budget import Budget
from src.models.constants import Phase
from src.workflow.workflow_manager import WorkflowManager


# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def household():
    return Household(Budget())


@pytest.fixture
def wm(household):
    return WorkflowManager(household)


@pytest.fixture
def member_amanda():
    return Member("Amanda")


@pytest.fixture
def member_heri():
    return Member("Heri")


# ====================================================
# TESTS: Initialization
# ====================================================


def test_workflow_manager_starts_in_registration_phase(wm):
    """WorkflowManager debe iniciar en fase REGISTRATION"""
    assert wm.current_phase == Phase.REGISTRATION


# ====================================================
# TESTS: REGISTRATION PHASE - register_member
# ====================================================


def test_register_member_in_registration_phase(wm, member_amanda):
    """Un miembro registrado en fase REGISTRATION aparece en get_registered_members"""
    wm.register_member(member_amanda)
    assert "Amanda" in wm.get_registered_members()


def test_register_member_wrong_phase(wm, member_amanda):
    """Intentar registrar un miembro fuera de REGISTRATION lanza ValueError"""
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()
    with pytest.raises(ValueError, match="registro"):
        wm.register_member(Member("Nuevo"))


def test_register_duplicate_member(wm, member_amanda):
    """Registrar un miembro con nombre ya existente lanza ValueError"""
    wm.register_member(member_amanda)
    with pytest.raises(ValueError, match="ya está registrado"):
        wm.register_member(Member("Amanda"))


# ====================================================
# TESTS: REGISTRATION PHASE - set_incomes
# ====================================================


def test_set_income_valid(wm, member_amanda):
    """set_incomes actualiza el ingreso del miembro en centavos correctamente"""
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 3000)
    assert wm.get_member_income("Amanda") == 300000


def test_set_income_wrong_phase(wm, member_amanda):
    """Intentar asignar ingresos fuera de REGISTRATION lanza ValueError"""
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()
    with pytest.raises(ValueError, match="registro"):
        wm.set_incomes("Amanda", 5000)


def test_set_income_nonexistent_member(wm):
    """Asignar ingresos a un miembro no registrado lanza ValueError"""
    with pytest.raises(ValueError):
        wm.set_incomes("Fantasma", 3000)


# ====================================================
# TESTS: REGISTRATION PHASE - finish_registration
# ====================================================


def test_finish_registration_advances_to_planning(wm, member_amanda):
    """finish_registration con datos válidos avanza la fase a PLANNING"""
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()
    assert wm.current_phase == Phase.PLANNING


def test_finish_registration_no_members(wm):
    """finish_registration sin miembros registrados lanza ValueError"""
    with pytest.raises(ValueError, match="Registra al menos un miembro"):
        wm.finish_registration()


def test_finish_registration_zero_incomes(wm, member_amanda):
    """finish_registration con todos los ingresos en 0 lanza ValueError"""
    wm.register_member(member_amanda)
    with pytest.raises(ValueError, match="Al menos un miembro debe tener ingresos"):
        wm.finish_registration()


def test_finish_registration_partial_incomes_ok(wm, member_amanda, member_heri):
    """finish_registration es válido si al menos un miembro tiene ingresos > 0"""
    wm.register_member(member_amanda)
    wm.register_member(member_heri)
    wm.set_incomes("Amanda", 3000)
    # Heri sin ingresos — debe pasar igual
    wm.finish_registration()
    assert wm.current_phase == Phase.PLANNING


# ====================================================
# TESTS: QUERIES (phase-independent)
# ====================================================


def test_get_registered_members_empty(wm):
    """get_registered_members retorna lista vacía si no hay miembros"""
    assert wm.get_registered_members() == []


def test_get_registered_members_multiple(wm, member_amanda, member_heri):
    """get_registered_members retorna todos los nombres registrados"""
    wm.register_member(member_amanda)
    wm.register_member(member_heri)
    members = wm.get_registered_members()
    assert set(members) == {"Amanda", "Heri"}


def test_get_member_income_nonexistent(wm):
    """get_member_income con nombre inexistente lanza ValueError"""
    with pytest.raises(ValueError, match="does not exist"):
        wm.get_member_income("Nadie")


def test_get_member_income_after_planning(wm, member_amanda):
    """get_member_income está disponible en cualquier fase y retorna centavos"""
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()
    assert wm.get_member_income("Amanda") == 500000


def test_get_total_incomes_empty(wm):
    """get_total_incomes sin miembros registrados lanza ValueError"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        wm.get_total_incomes()


def test_get_total_incomes_multiple_members(wm, member_amanda, member_heri):
    """get_total_incomes suma correctamente los ingresos de todos los miembros en centavos"""
    wm.register_member(member_amanda)
    wm.register_member(member_heri)
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    assert wm.get_total_incomes() == 500000


# ====================================================
# TESTS: validate_phase helper
# ====================================================


def test_validate_phase_correct(wm):
    """validate_phase no lanza excepción cuando la fase actual es la requerida"""
    wm.validate_phase(Phase.REGISTRATION)  # no debe lanzar


def test_validate_phase_wrong(wm):
    """validate_phase lanza ValueError cuando la fase actual no coincide con la requerida"""
    with pytest.raises(ValueError, match="planificación"):
        wm.validate_phase(Phase.PLANNING)


# ====================================================
# TESTS: PLANNING PHASE - Budget assignment
# ====================================================


def test_set_budget_for_category_in_planning_phase(wm, member_amanda):
    """Puedo asignar presupuesto a una categoría en fase PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    # En PLANNING, asignar presupuesto
    wm.set_budget_for_category("fijos", 2000)
    assert wm.household.get_category_budget("fijos") == 200000


def test_set_budget_for_category_raises_if_not_in_planning(wm, member_amanda):
    """set_budget_for_category lanza ValueError si no estamos en PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member(member_amanda)

    # Aún en REGISTRATION
    with pytest.raises(ValueError, match="planificación"):
        wm.set_budget_for_category("fijos", 2000)


def test_set_budget_for_category_multiple_categories(wm, member_amanda):
    """Puedo asignar presupuestos a múltiples categorías"""
    wm.household.budget.set_standard_categories()
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 10000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 5000)
    wm.set_budget_for_category("variables", 3000)

    assert wm.household.get_category_budget("fijos") == 500000
    assert wm.household.get_category_budget("variables") == 300000


# ====================================================
# TESTS: PLANNING PHASE - Planning summary
# ====================================================


def test_get_planning_summary_in_planning_phase(wm, member_amanda):
    """get_planning_summary retorna resumen completo en PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 10000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 5000)
    wm.set_budget_for_category("variables", 3000)

    summary = wm.get_planning_summary()

    assert summary["members"] == ["Amanda"]
    assert summary["total_household_income"] == 1000000
    assert summary["total_budgeted"] == 800000
    assert summary["loose_money"] == 200000
    assert "distribution_percentages" in summary
    assert "contributions_preview" in summary


def test_get_planning_summary_raises_if_not_in_planning(wm, member_amanda):
    """get_planning_summary lanza ValueError si no estamos en PLANNING"""
    with pytest.raises(ValueError, match="planificación"):
        wm.get_planning_summary()


def test_get_planning_summary_includes_all_key_data(wm, member_amanda):
    """get_planning_summary incluye todas las claves necesarias"""
    wm.household.budget.set_standard_categories()
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 10000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 5000)

    summary = wm.get_planning_summary()

    required_keys = {
        "members",
        "member_incomes",
        "total_household_income",
        "distribution_method",
        "distribution_percentages",
        "categories",
        "budget_by_category",
        "total_budgeted",
        "loose_money",
        "contributions_preview",
    }

    assert required_keys.issubset(set(summary.keys()))


# ====================================================
# TESTS: PLANNING PHASE - Transitions to MONTH
# ====================================================


def test_finish_planning_transitions_to_month_phase(wm, member_amanda):
    """finish_planning transita de PLANNING a MONTH correctamente"""
    wm.household.budget.set_standard_categories()
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    assert wm.current_phase == Phase.PLANNING

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    assert wm.current_phase == Phase.MONTH


def test_finish_planning_raises_if_not_in_planning(wm):
    """finish_planning lanza ValueError si no estamos en PLANNING"""
    with pytest.raises(ValueError, match="planificación"):
        wm.finish_planning()


def test_finish_planning_raises_if_no_categories(wm, member_amanda):
    """finish_planning lanza ValueError si no hay categorías creadas"""
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    # No agregamos categorías
    with pytest.raises(ValueError, match="al menos una categoría"):
        wm.finish_planning()


def test_finish_planning_raises_if_no_budget_assigned(wm, member_amanda):
    """finish_planning lanza ValueError si no hay presupuesto asignado"""
    wm.household.budget.set_standard_categories()
    wm.register_member(member_amanda)
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    # Categorías existen pero sin presupuesto asignado
    with pytest.raises(ValueError, match="presupuesto"):
        wm.finish_planning()


def test_finish_planning_with_multiple_members(wm, member_amanda, member_heri):
    """finish_planning funciona correctamente con múltiples miembros"""
    wm.household.budget.set_standard_categories()
    wm.register_member(member_amanda)
    wm.register_member(member_heri)
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 3000)
    wm.set_budget_for_category("variables", 1500)
    wm.finish_planning()

    assert wm.current_phase == Phase.MONTH
