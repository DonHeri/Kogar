import pytest
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.constants import Phase, MetodoReparto
from src.workflow.workflow_manager import WorkflowManager


# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def household():
    return Household(Budget(), ExpenseTracker())


@pytest.fixture
def wm(household):
    return WorkflowManager(household)


# ====================================================
# TESTS: Initialization
# ====================================================


def test_workflow_manager_starts_in_registration_phase(wm):
    """WorkflowManager debe iniciar en fase REGISTRATION"""
    assert wm.current_phase == Phase.REGISTRATION


# ====================================================
# TESTS: REGISTRATION PHASE - register_member
# ====================================================


def test_register_member_in_registration_phase(wm):
    """Un miembro registrado en fase REGISTRATION aparece en get_registered_members"""
    wm.register_member("Amanda")
    assert "amanda" in wm.get_registered_members()


def test_register_member_wrong_phase(wm):
    """Intentar registrar un miembro fuera de REGISTRATION lanza ValueError"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()
    with pytest.raises(ValueError, match="registro"):
        wm.register_member("Nuevo")


def test_register_duplicate_member(wm):
    """Registrar un miembro con nombre ya existente lanza ValueError"""
    wm.register_member("Amanda")
    with pytest.raises(ValueError, match="ya está registrado"):
        wm.register_member("Amanda")


def test_register_member_strips_whitespace(wm):
    """register_member limpia espacios en blanco del nombre"""
    wm.register_member("  Amanda  ")
    assert "amanda" in wm.get_registered_members()
    assert "  Amanda  " not in wm.get_registered_members()


# ====================================================
# TESTS: REGISTRATION PHASE - set_incomes
# ====================================================


def test_set_income_valid(wm):
    """set_incomes actualiza el ingreso del miembro en centavos correctamente"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    assert wm.get_member_income("amanda") == 300000


def test_set_income_wrong_phase(wm):
    """Intentar asignar ingresos fuera de REGISTRATION lanza ValueError"""
    wm.register_member("Amanda")
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


def test_finish_registration_advances_to_planning(wm):
    """finish_registration con datos válidos avanza la fase a PLANNING"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()
    assert wm.current_phase == Phase.PLANNING


def test_finish_registration_no_members(wm):
    """finish_registration sin miembros registrados lanza ValueError"""
    with pytest.raises(ValueError, match="Registra al menos un miembro"):
        wm.finish_registration()


def test_finish_registration_zero_incomes(wm):
    """finish_registration con todos los ingresos en 0 lanza ValueError"""
    wm.register_member("Amanda")
    with pytest.raises(ValueError, match="Al menos un miembro debe tener ingresos"):
        wm.finish_registration()


def test_finish_registration_freezes_incomes(wm):
    """finish_registration congela los ingresos registrados"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)

    # Antes de finish_registration, no hay ingresos congelados
    assert wm.household._registered_incomes == {}

    wm.finish_registration()

    # Después de finish_registration, ingresos están congelados
    assert wm.household._registered_incomes == {
        "amanda": 300000,  # 3000 EUR en céntimos
        "heri": 200000,  # 2000 EUR en céntimos
    }
    assert wm.current_phase == Phase.PLANNING


def test_planning_phase_uses_frozen_incomes(wm):
    """PLANNING usa ingresos congelados, no mutables"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    # Ingresos congelados: Amanda=3000, Heri=2000, Total=5000
    total_frozen = wm.get_total_incomes()
    assert total_frozen == 500000  # 5000 EUR

    # Intentar modificar ingresos MUTABLES directamente (simula bug o acceso directo)
    wm.household.members["amanda"].monthly_income = 600000  # 6000 EUR

    # get_total_incomes() debe seguir usando datos CONGELADOS, no mutables
    total_after_mutation = wm.get_total_incomes()
    assert total_after_mutation == 500000  # Sigue siendo 5000 EUR (congelado)
    assert total_after_mutation != 800000  # NO debe ser 8000 EUR (6000 + 2000)


def test_finish_registration_partial_incomes_ok(wm):
    """finish_registration es válido si al menos un miembro tiene ingresos > 0"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
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


def test_get_registered_members_multiple(wm):
    """get_registered_members retorna todos los nombres registrados"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    members = wm.get_registered_members()
    assert set(members) == {"amanda", "heri"}


def test_get_member_income_nonexistent(wm):
    """get_member_income con nombre inexistente lanza ValueError"""
    with pytest.raises(ValueError, match="does not exist"):
        wm.get_member_income("Nadie")


def test_get_member_income_after_planning(wm):
    """get_member_income está disponible en cualquier fase y retorna centavos"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()
    assert wm.get_member_income("amanda") == 500000


def test_get_total_incomes_empty(wm):
    """get_total_incomes sin miembros registrados lanza ValueError"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        wm.get_total_incomes()


def test_get_total_incomes_multiple_members(wm):
    """get_total_incomes suma correctamente los ingresos de todos los miembros en centavos"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
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


def test_set_budget_for_category_in_planning_phase(wm):
    """Puedo asignar presupuesto a una categoría en fase PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    # En PLANNING, asignar presupuesto
    wm.set_budget_for_category("fijos", 2000)
    assert wm.household.get_category_budget("fijos") == 200000


def test_set_budget_for_category_raises_if_not_in_planning(wm):
    """set_budget_for_category lanza ValueError si no estamos en PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")

    # Aún en REGISTRATION
    with pytest.raises(ValueError, match="planificación"):
        wm.set_budget_for_category("fijos", 2000)


def test_set_budget_for_category_multiple_categories(wm):
    """Puedo asignar presupuestos a múltiples categorías"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 10000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 5000)
    wm.set_budget_for_category("variables", 3000)

    assert wm.household.get_category_budget("fijos") == 500000
    assert wm.household.get_category_budget("variables") == 300000


# ====================================================
# TESTS: PLANNING PHASE - Planning summary
# ====================================================


def test_get_planning_summary_in_planning_phase(wm):
    """get_planning_summary retorna resumen completo en PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 10000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 5000)
    wm.set_budget_for_category("variables", 3000)

    summary = wm.get_planning_summary()

    assert summary["members"] == ["amanda"]
    assert summary["total_household_income"] == 1000000
    assert summary["total_budgeted"] == 800000
    assert summary["loose_money"] == 200000
    assert "distribution_percentages" in summary
    assert "contributions_preview" in summary


def test_get_planning_summary_raises_if_not_in_planning(wm):
    """get_planning_summary lanza ValueError si no estamos en PLANNING"""
    with pytest.raises(ValueError, match="planificación"):
        wm.get_planning_summary()


def test_get_planning_summary_includes_all_key_data(wm):
    """get_planning_summary incluye todas las claves necesarias"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
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


def test_finish_planning_transitions_to_month_phase(wm):
    """finish_planning transita de PLANNING a MONTH correctamente"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
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


def test_finish_planning_raises_if_no_categories(wm):
    """finish_planning lanza ValueError si no hay categorías creadas"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    # No agregamos categorías
    with pytest.raises(ValueError, match="al menos una categoría"):
        wm.finish_planning()


def test_finish_planning_raises_if_no_budget_assigned(wm):
    """finish_planning lanza ValueError si no hay presupuesto asignado"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    # Categorías existen pero sin presupuesto asignado
    with pytest.raises(ValueError, match="presupuesto"):
        wm.finish_planning()


def test_finish_planning_with_multiple_members(wm):
    """finish_planning funciona correctamente con múltiples miembros"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 3000)
    wm.set_budget_for_category("variables", 1500)
    wm.finish_planning()

    assert wm.current_phase == Phase.MONTH


def test_finish_planning_freezes_agreed_state(wm):
    """finish_planning congela percentages y contributions acordadas"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.set_budget_for_category("fijos", 5000)
    wm.set_budget_for_category("variables", 2000)

    # Antes de finish_planning, no hay datos congelados
    assert wm.household._agreed_percentages == {}
    assert wm.household._agreed_contributions == {}

    wm.finish_planning()

    # Después de finish_planning, datos están congelados
    assert wm.household._agreed_percentages == {"amanda": 6000, "heri": 4000}
    assert "fijos" in wm.household._agreed_contributions
    assert "variables" in wm.household._agreed_contributions

    # Verificar estructura de contributions
    fijos_contrib = wm.household._agreed_contributions["fijos"]
    assert "contributions" in fijos_contrib
    assert fijos_contrib["contributions"]["amanda"] == 300000  # 60% de 500000
    assert fijos_contrib["contributions"]["heri"] == 200000  # 40% de 500000


# ====================================================
# TESTS: PLANNING PHASE - Category Management
# ====================================================


def test_add_category_in_planning_phase(wm):
    """add_category() crea categoría en PLANNING"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    wm.add_category("educacion")

    assert "educacion" in wm.get_active_categories()


def test_add_category_raises_if_not_in_planning(wm):
    """add_category() lanza error si no estamos en PLANNING"""
    with pytest.raises(ValueError, match="planificación"):
        wm.add_category("educacion")


def test_set_standard_categories_creates_defaults(wm):
    """set_standard_categories() establece categorías estándar"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    wm.set_standard_categories()

    categories = wm.get_active_categories()
    assert "fijos" in categories
    assert "variables" in categories
    assert "ahorro" in categories
    assert "deuda" in categories


def test_remove_category_in_planning_phase(wm):
    """remove_category() elimina categoría en PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    wm.remove_category("fijos")

    assert "fijos" not in wm.get_active_categories()


def test_remove_category_raises_if_not_in_planning(wm):
    """remove_category() lanza error si no estamos en PLANNING"""
    wm.household.budget.set_standard_categories()

    with pytest.raises(ValueError, match="planificación"):
        wm.remove_category("fijos")


# ====================================================
# TESTS: PLANNING PHASE - Distribution Method
# ====================================================


def test_assign_distribution_method_sets_method(wm):
    """assign_distribution_method() establece método de reparto"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.EQUAL)

    assert wm.household.method == MetodoReparto.EQUAL


def test_assign_distribution_method_changes_summary(wm):
    """assign_distribution_method() cambia el método en el resumen"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.EQUAL)
    summary = wm.get_planning_summary()

    assert summary["distribution_method"] == "igual"


# ====================================================
# TESTS: Getters de datos congelados
# ====================================================


def test_get_registered_incomes_in_planning(wm):
    """get_registered_incomes() retorna ingresos congelados en PLANNING"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    frozen_incomes = wm.get_registered_incomes()

    assert frozen_incomes == {"amanda": 300000, "heri": 200000}


def test_get_registered_incomes_fails_in_registration(wm):
    """get_registered_incomes() lanza error en REGISTRATION"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)

    with pytest.raises(
        ValueError, match="Operación solo permitida en fase planificación"
    ):
        wm.get_registered_incomes()


def test_get_agreed_percentages_in_month(wm):
    """get_agreed_percentages() retorna percentages congelados en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.set_budget_for_category("fijos", 5000)
    wm.finish_planning()

    frozen_percentages = wm.get_agreed_percentages()

    assert frozen_percentages == {"amanda": 6000, "heri": 4000}  # 60/40


def test_get_agreed_percentages_fails_in_planning(wm):
    """get_agreed_percentages() lanza error en PLANNING"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(
        ValueError, match="Operación solo permitida en fase transcurso_mes"
    ):
        wm.get_agreed_percentages()


def test_get_agreed_contributions_in_month(wm):
    """get_agreed_contributions() retorna contributions congeladas en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.set_budget_for_category("fijos", 5000)
    wm.set_budget_for_category("variables", 2000)
    wm.finish_planning()

    frozen_contributions = wm.get_agreed_contributions()

    assert "fijos" in frozen_contributions
    assert "variables" in frozen_contributions
    assert frozen_contributions["fijos"]["contributions"]["amanda"] == 300000  # 60%
    assert frozen_contributions["fijos"]["contributions"]["heri"] == 200000  # 40%


def test_get_agreed_contributions_fails_in_planning(wm):
    """get_agreed_contributions() lanza error en PLANNING"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(
        ValueError, match="Operación solo permitida en fase transcurso_mes"
    ):
        wm.get_agreed_contributions()
