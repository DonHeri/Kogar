from datetime import date, datetime

import pytest

from src.models.budget import Budget
from src.models.constants import MetodoReparto, Phase
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.workflow.workflow_manager import WorkflowManager

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def household() -> Household:
    return Household(
        Budget(), ExpenseTracker(), SavingBucketTracker(), DebtBucketTracker()
    )


@pytest.fixture
def wm(household) -> WorkflowManager:
    return WorkflowManager(household)


@pytest.fixture
def wm_in_planning(wm) -> WorkflowManager:
    """WM en PLANNING: un miembro (Amanda, 5000) y categorías estándar."""
    wm.start_new_month()
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 5000)
    wm.finish_registration()
    return wm


@pytest.fixture
def wm_in_month_two_members(wm):
    """WM en MONTH con dos miembros: amanda (60%) y heri (40%), total 1000€"""
    wm.start_new_month()
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 6000)
    wm.set_member_incomes("Heri", 4000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 5000)
    debt_id = wm.add_debt_bucket(
        name="prestamo amanda",
        principal_euros=21200,
        owner="Amanda",
        installment_euros=212,
    )
    wm.finish_planning()
    return (wm, debt_id)


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
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()
    with pytest.raises(ValueError, match="registration"):
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
# TESTS: REGISTRATION PHASE - set_member_incomes
# ====================================================


def test_set_income_valid(wm):
    """set_member_incomes actualiza el ingreso del miembro en centavos correctamente"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    assert wm.get_member_income("amanda") == 300000


def test_set_income_wrong_phase(wm):
    """Intentar asignar ingresos fuera de REGISTRATION lanza ValueError"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()
    with pytest.raises(ValueError, match="registration"):
        wm.set_member_incomes("Amanda", 5000)


def test_set_income_nonexistent_member(wm):
    """Asignar ingresos a un miembro no registrado lanza ValueError"""
    with pytest.raises(ValueError):
        wm.set_member_incomes("Fantasma", 3000)


# ====================================================
# TESTS: REGISTRATION PHASE - finish_registration
# ====================================================


def test_finish_registration_advances_to_planning(wm):
    """finish_registration con datos válidos avanza la fase a PLANNING"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
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
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)

    assert wm.household._registered_incomes == {}

    wm.finish_registration()

    assert wm.household._registered_incomes == {
        "amanda": 300000,
        "heri": 200000,
    }
    assert wm.current_phase == Phase.PLANNING


def test_planning_phase_uses_frozen_incomes(wm):
    """PLANNING usa ingresos congelados, no mutables"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)
    wm.finish_registration()

    total_frozen = wm.get_total_incomes()
    assert total_frozen == 500000

    # Mutamos directamente — los congelados no deben cambiar
    wm.household.members["amanda"].monthly_income = 600000

    total_after_mutation = wm.get_total_incomes()
    assert total_after_mutation == 500000
    assert total_after_mutation != 800000


def test_finish_registration_partial_incomes_ok(wm):
    """finish_registration es válido si al menos un miembro tiene ingresos > 0"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
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
    wm.set_member_incomes("Amanda", 5000)
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
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)
    assert wm.get_total_incomes() == 500000


# ====================================================
# TESTS: validate_phase helper
# ====================================================


def test_validate_phase_correct(wm):
    """validate_phase no lanza excepción cuando la fase actual es la requerida"""
    wm.validate_phase(Phase.REGISTRATION)  # no debe lanzar


def test_validate_phase_wrong(wm):
    """validate_phase lanza ValueError cuando la fase actual no coincide con la requerida"""
    with pytest.raises(ValueError, match="planning"):
        wm.validate_phase(Phase.PLANNING)


# ====================================================
# TESTS: PLANNING PHASE - Budget assignment
# ====================================================


def test_set_budget_for_category_in_planning_phase(wm_in_planning):
    """Puedo asignar presupuesto a una categoría en fase PLANNING"""
    wm = wm_in_planning
    wm.set_budget_for_category("fijos", 2000)
    assert wm.household.get_category_planned_amount("fijos") == 200000


def test_set_budget_for_category_raises_if_not_in_planning(wm):
    """set_budget_for_category lanza ValueError si no estamos en PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")

    with pytest.raises(ValueError, match="planning"):
        wm.set_budget_for_category("fijos", 2000)


def test_set_budget_for_category_multiple_categories(wm):
    """Puedo asignar presupuestos a múltiples categorías"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 10000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 5000)
    wm.set_budget_for_category("variables", 3000)

    assert wm.household.get_category_planned_amount("fijos") == 500000
    assert wm.household.get_category_planned_amount("variables") == 300000


def test_add_category_with_parent_in_planning(wm_in_planning):
    """add_category en WM crea una hija colgando de su raíz."""
    wm = wm_in_planning
    wm.add_category("vivienda", parent="fijos")

    assert wm.household.budget.categories["vivienda"].parent == "fijos"


# ====================================================
# TESTS: PLANNING PHASE - Planning summary
# ====================================================


def test_get_planning_summary_in_planning_phase(wm):
    """get_planning_summary retorna resumen completo en PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 10000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 5000)
    wm.set_budget_for_category("variables", 3000)

    summary = wm.get_planning_summary()

    assert summary["members"] == ["amanda"]
    assert summary["total_household_income"] == 1000000
    assert summary["total_budgeted"] == 1000000
    assert summary["missing_money"]["total"] == 200000
    assert "distribution_percentages" in summary
    assert "contributions_preview" in summary


def test_get_planning_summary_raises_if_not_in_planning(wm):
    """get_planning_summary lanza ValueError si no estamos en PLANNING"""
    with pytest.raises(ValueError, match="planning"):
        wm.get_planning_summary()


def test_get_planning_summary_includes_all_key_data(wm):
    """get_planning_summary incluye todas las claves necesarias"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 10000)
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
        "missing_money",
        "contributions_preview",
    }

    assert required_keys.issubset(set(summary.keys()))


def test_get_planning_summary_returns_negative_missing_money_when_over_budget(wm):
    """set_budget_for_category bloquea presupuesto que supera ingresos"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    # Ingresos: 300000 céntimos — intentar setear 400000 → ValueError
    with pytest.raises(ValueError):
        wm.set_budget_for_category("fijos", 4000)


# ====================================================
# TESTS: PLANNING PHASE - Transitions to MONTH
# ====================================================


def test_finish_planning_transitions_to_month_phase(wm):
    """finish_planning transita de PLANNING a MONTH correctamente"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 5000)
    wm.finish_registration()

    assert wm.current_phase == Phase.PLANNING

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    assert wm.current_phase == Phase.MONTH


def test_finish_planning_raises_if_not_in_planning(wm):
    """finish_planning lanza ValueError si no estamos en PLANNING"""
    with pytest.raises(ValueError, match="planning"):
        wm.finish_planning()


def test_finish_planning_raises_if_no_budget_assigned(wm):
    """finish_planning lanza ValueError si no hay presupuesto asignado"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 5000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="presupuesto"):
        wm.finish_planning()


def test_finish_planning_with_multiple_members(wm):
    """finish_planning funciona correctamente con múltiples miembros"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)
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
    wm.set_member_incomes("Amanda", 6000)
    wm.set_member_incomes("Heri", 4000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.set_budget_for_category("fijos", 5000)
    wm.set_budget_for_category("variables", 2000)

    assert wm.household._agreed_percentages == {}
    assert wm.household._agreed_contributions == {}

    wm.finish_planning()

    assert wm.household._agreed_percentages == {"amanda": 6000, "heri": 4000}
    assert "fijos" in wm.household._agreed_contributions
    assert "variables" in wm.household._agreed_contributions

    fijos_contrib = wm.household._agreed_contributions["fijos"]
    assert "contributions" in fijos_contrib
    assert fijos_contrib["contributions"]["amanda"] == 300000  # 60% de 500000
    assert fijos_contrib["contributions"]["heri"] == 200000  # 40% de 500000


def test_finish_planning_allows_over_budget(wm):
    """set_budget_for_category bloquea presupuesto que supera ingresos"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 1000)
    wm.finish_registration()

    # Presupuesto total: 1500€ > ingresos: 1000€ → ValueError
    with pytest.raises(ValueError):
        wm.set_budget_for_category("fijos", 1500)


# ====================================================
# TESTS: PLANNING PHASE - Category Management
# ====================================================


def test_add_category_in_planning_phase(wm_in_planning):
    """add_category() crea categoría en PLANNING"""
    wm = wm_in_planning
    wm.add_category("educacion")

    assert "educacion" in wm.get_active_categories()


def test_add_category_raises_if_not_in_planning(wm):
    """add_category() lanza error si no estamos en PLANNING"""
    with pytest.raises(ValueError, match="planning"):
        wm.add_category("educacion")


def test_set_standard_categories_creates_defaults(wm):
    """set_standard_categories() establece categorías estándar"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 5000)
    wm.finish_registration()

    wm.set_standard_categories()

    categories = wm.get_active_categories()
    assert "fijos" in categories
    assert "variables" in categories
    assert "reserva" in categories


def test_remove_category_in_planning_phase(wm_in_planning):
    """remove_category() elimina categoría en PLANNING"""
    wm = wm_in_planning
    wm.remove_category("fijos")

    assert "fijos" not in wm.get_active_categories()


def test_remove_category_raises_if_not_in_planning(wm):
    """remove_category() lanza error si no estamos en PLANNING"""
    wm.household.budget.set_standard_categories()

    with pytest.raises(ValueError, match="planning"):
        wm.remove_category("fijos")


# ====================================================
# TESTS: PLANNING PHASE - Distribution Method
# ====================================================


def test_assign_distribution_method_sets_method(wm_in_planning):
    """assign_distribution_method() establece método de reparto"""
    wm = wm_in_planning
    wm.assign_distribution_method(MetodoReparto.EQUAL)

    assert wm.household.method == MetodoReparto.EQUAL


def test_assign_distribution_method_changes_summary(wm):
    """assign_distribution_method() cambia el método en el resumen"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.EQUAL)
    summary = wm.get_planning_summary()

    assert summary["distribution_method"] == "equal"


# ====================================================
# TESTS: Getters de datos congelados
# ====================================================


def test_get_registered_incomes_in_planning(wm):
    """get_registered_incomes() retorna ingresos congelados en PLANNING"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)
    wm.finish_registration()

    frozen_incomes = wm.get_registered_incomes()

    assert frozen_incomes == {"amanda": 300000, "heri": 200000}


def test_get_registered_incomes_fails_in_registration(wm):
    """get_registered_incomes() lanza error en REGISTRATION"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)

    with pytest.raises(ValueError, match="planning"):
        wm.get_registered_incomes()


def test_get_agreed_percentages_in_month(wm):
    """get_agreed_percentages() retorna percentages congelados en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.set_budget_for_category("fijos", 5000)
    wm.finish_planning()

    frozen_percentages = wm.get_agreed_percentages()

    assert frozen_percentages == {"amanda": 6000, "heri": 4000}  # 60/40


def test_get_agreed_percentages_fails_in_planning(wm):
    """get_agreed_percentages() lanza error en PLANNING"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="month"):
        wm.get_agreed_percentages()


def test_get_agreed_contributions_in_month(wm):
    """get_agreed_contributions() retorna contributions congeladas en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 6000)
    wm.set_member_incomes("Heri", 4000)
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
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="month"):
        wm.get_agreed_contributions()


# ====================================================
# TESTS: set_custom_splits
# ====================================================


def test_set_custom_splits_in_planning_phase(wm):
    """set_custom_splits() establece porcentajes personalizados en PLANNING"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)
    wm.finish_registration()

    wm.set_custom_splits({"amanda": 70.0, "heri": 30.0})

    assert wm.household._custom_splits == {"amanda": 7000, "heri": 3000}


def test_set_custom_splits_raises_if_not_in_planning(wm):
    """set_custom_splits() lanza error si no estamos en PLANNING"""
    wm.register_member("Amanda")

    with pytest.raises(ValueError, match="planning"):
        wm.set_custom_splits({"Amanda": 100.0})


# ====================================================
# TESTS: preview_budget_contribution_summary y get_current_contributions
# ====================================================


def test_preview_budget_contribution_summary_in_planning(wm):
    """preview_budget_contribution_summary() muestra preview con método específico"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 5000)

    preview = wm.preview_budget_contribution_summary(MetodoReparto.EQUAL)

    assert "fijos" in preview
    assert preview["fijos"]["contributions"]["amanda"] == 250000
    assert preview["fijos"]["contributions"]["heri"] == 250000


def test_get_current_contributions_in_planning(wm):
    """get_current_contributions() obtiene contribuciones con método configurado"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.set_budget_for_category("fijos", 5000)

    contributions = wm.get_current_contributions()

    assert "fijos" in contributions
    assert contributions["fijos"]["contributions"]["amanda"] == 300000  # 60%
    assert contributions["fijos"]["contributions"]["heri"] == 200000  # 40%


# ====================================================
# TESTS: register_expense (MONTH phase)
# ====================================================


def test_register_expense_in_month_phase(wm):
    """register_expense() registra gasto correctamente en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "fijos", 500.50, "Alquiler")

    expenses = wm.household.expense_tracker.expenses
    assert len(expenses) == 1
    assert expenses[0].member == "amanda"
    assert expenses[0].category.name == "fijos"
    assert expenses[0].amount == 50050
    assert expenses[0].description == "Alquiler"


def test_register_expense_converts_euros_to_cents(wm):
    """register_expense() convierte euros a céntimos correctamente"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "fijos", 123.45)

    expense = wm.household.expense_tracker.expenses[0]
    assert expense.amount == 12345


def test_register_expense_normalizes_member_name(wm):
    """register_expense() normaliza el nombre del miembro"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("AMANDA", "fijos", 100.00)

    expense = wm.household.expense_tracker.expenses[0]
    assert expense.member == "amanda"


def test_register_expense_strips_whitespace(wm):
    """register_expense() limpia espacios en category y description"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "  fijos  ", 100.00, "  Alquiler  ")

    expense = wm.household.expense_tracker.expenses[0]
    assert expense.category.name == "fijos"
    assert expense.description == "Alquiler"


def test_register_expense_raises_if_not_in_month(wm):
    """register_expense() lanza error si no estamos en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="month"):
        wm.register_expense("Amanda", "fijos", 100.00)


def test_register_expense_empty_description_ok(wm):
    """register_expense() acepta description vacía"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "fijos", 100.00, "")

    expense = wm.household.expense_tracker.expenses[0]
    assert expense.description == ""


def test_register_expense_derives_is_shared_from_category(wm):
    """Sin is_shared explícito, se hereda del default (is_shared) de la categoría"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.register_member("Heri")
    wm.set_member_incomes("Heri", 2000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense(
        "Amanda", "fijos", 100.00, participants=wm.household.get_member_names()
    )  # SHARED → is_shared=True
    wm.register_expense(
        "Amanda", "variables", 50.00, participants=["Amanda"]
    )  # PERSONAL → is_shared=False

    expenses = wm.household.expense_tracker.expenses
    assert expenses[0].is_shared is True
    assert expenses[1].is_shared is False


def test_register_expense_explicit_is_shared_overrides_behavior(wm):
    """is_shared explícito sobreescribe el default de la categoría"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.register_member("Heri")
    wm.set_member_incomes("Heri", 2000)
    wm.finish_registration()
    wm.set_budget_for_category("variables", 1000)
    wm.finish_planning()

    # variables es PERSONAL por defecto, pero el usuario lo marca como compartido
    wm.register_expense(
        "Amanda", "variables", 80.00, participants=wm.household.get_member_names()
    )

    expense = wm.household.expense_tracker.expenses[0]
    assert expense.is_shared is True


# ====================================================
# TESTS: get_registration_summary y get_month_summary
# ====================================================


def test_get_registration_summary_in_registration_phase(wm):
    """get_registration_summary() retorna resumen en REGISTRATION"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 3000)
    wm.set_member_incomes("Heri", 2000)

    summary = wm.get_registration_summary()

    assert "members" in summary
    assert "member_incomes" in summary
    assert "total_household_income" in summary
    assert summary["members"] == ["amanda", "heri"]
    assert summary["total_household_income"] == 500000


def test_get_registration_summary_after_freezing(wm):
    """get_registration_summary() funciona después de congelar ingresos"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    summary = wm.get_registration_summary()

    assert summary["total_household_income"] == 300000


def test_get_month_summary_in_month_phase(wm):
    """get_month_summary() retorna resumen completo en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "fijos", 500.00)

    summary = wm.get_month_summary()

    assert "totals" in summary
    assert "by_category" in summary
    assert summary["totals"]["total_budgeted"] == 300000
    assert summary["totals"]["total_spent"] == 50000


def test_get_month_summary_raises_if_not_in_month(wm):
    """get_month_summary() lanza error si no estamos en MONTH"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="month"):
        wm.get_month_summary()


# ====================================================
# TESTS: get_budget_as_percentage (WorkflowManager)
# ====================================================


def test_get_budget_as_percentage_wrong_phase(wm):
    """get_budget_as_percentage lanza error si no estamos en PLANNING"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)

    with pytest.raises(ValueError, match="planning"):
        wm.get_budget_as_percentage("fijos")


def test_get_budget_as_percentage_returns_basis_points(wm):
    """Retorna basis points representando % de ingresos"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 1500)  # 50% de 3000€

    pct_basis = wm.get_budget_as_percentage("fijos")

    assert pct_basis == 5000  # 50%


def test_get_budget_as_percentage_zero_budget(wm):
    """Retorna 0 cuando presupuesto es 0"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("variables", 0)

    pct_basis = wm.get_budget_as_percentage("variables")

    assert pct_basis == 0


def test_get_budget_as_percentage_roundtrip(wm):
    """set_budget_for_category + get_budget_as_percentage es consistente"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 1200)  # 40% de 3000€
    retrieved = wm.get_budget_as_percentage("fijos")

    assert retrieved == 4000  # 40%


# ====================================================
# TESTS: set_budget_by_percentages (WorkflowManager)
# ====================================================


def test_set_budget_by_percentages_basic(wm):
    """Asigna presupuestos basados en distribución porcentual"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_by_percentages({"fijos": 50.0, "variables": 30.0, "reserva": 20.0})

    # Ingresos: 300000 céntimos
    assert wm.household.budget.get_planned_amount("fijos") == 150000  # 50%
    assert wm.household.budget.get_planned_amount("variables") == 90000  # 30%
    assert wm.household.budget.get_planned_amount("reserva") == 60000  # 20%


def test_set_budget_by_percentages_sum_exceeds_100(wm):
    """Lanza error si la suma de porcentajes excede 100%"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="suman.*%.*máximo.*100%"):
        wm.set_budget_by_percentages(
            {"fijos": 60.0, "variables": 50.0, "reserva": 20.0}
        )


def test_set_budget_by_percentages_missing_category(wm):
    """Lanza error si alguna categoría no existe en el presupuesto"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="categoría debe estar creada"):
        wm.set_budget_by_percentages(
            {"fijos": 50.0, "categoria_falsa": 30.0, "otra_falsa": 20.0}
        )


def test_set_budget_by_percentages_partial_allocation_raises(wm):
    """Lanza error si los porcentajes no suman 100%"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError):
        wm.set_budget_by_percentages({"fijos": 50.0, "variables": 20.0})


def test_set_budget_by_percentages_wrong_phase(wm):
    """Lanza error si no estamos en PLANNING"""
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)

    with pytest.raises(ValueError, match="planning"):
        wm.set_budget_by_percentages({"fijos": 50.0})


def test_set_budget_by_percentages_empty_dict_raises(wm):
    """Lanza error con diccionario vacío (no suma 100%)"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError):
        wm.set_budget_by_percentages({})


def test_set_budget_by_percentages_fractional_percentages(wm):
    """Maneja correctamente porcentajes fraccionarios sin pérdida de céntimos"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_by_percentages({"fijos": 33.33, "variables": 33.33, "reserva": 33.34})

    # Ingresos: 300000 céntimos (3000€)
    assert wm.household.budget.get_planned_amount("fijos") == 99990
    assert wm.household.budget.get_planned_amount("variables") == 99990
    assert wm.household.budget.get_planned_amount("reserva") == 100020


# ====================================================
# TESTS: finish_month
# ====================================================


@pytest.fixture
def wm_in_month(wm):
    """WM listo en fase MONTH"""
    wm.start_new_month()
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 1000)
    wm.finish_planning()
    return wm


def test_finish_month_transitions_to_closing(wm_in_month):
    """finish_month transita de MONTH a CLOSING"""
    assert wm_in_month.current_phase == Phase.MONTH
    wm_in_month.finish_month()
    assert wm_in_month.current_phase == Phase.CLOSING


def test_finish_month_adds_closing_to_completed_phases(wm_in_month):
    """finish_month registra CLOSING como fase completada"""
    wm_in_month.finish_month()
    assert Phase.CLOSING in wm_in_month._completed_phases


def test_finish_month_raises_if_not_in_month(wm):
    """finish_month lanza ValueError si no estamos en MONTH"""
    with pytest.raises(ValueError):
        wm.finish_month()


def test_get_settlement_accessible_after_finish_month(wm_in_month):
    """get_settlement sigue accesible después de cerrar el mes"""
    wm_in_month.finish_month()
    result = wm_in_month.get_settlement()
    assert result == []


# ====================================================
# TESTS: Validación de fase
# ====================================================


def test_register_expense_raises_in_planning(wm):
    """register_expense lanza ValueError si estamos en PLANNING, no en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="month"):
        wm.register_expense("Amanda", "fijos", 100.0)


def test_set_budget_for_category_raises_in_month(wm):
    """set_budget_for_category lanza ValueError una vez en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    with pytest.raises(ValueError, match="planning"):
        wm.set_budget_for_category("fijos", 1000)


# ====================================================
# TESTS: Flujo completo REGISTRATION → CLOSING
# ====================================================


# ====================================================
# TESTS: Saving Buckets
# ====================================================


def test_create_bucket_returns_uuid(wm_in_month_two_members: WorkflowManager):
    """create_saving_bucket retorna un UUID válido"""
    from uuid import UUID

    wm, _ = wm_in_month_two_members
    bucket_id = wm.create_saving_bucket("Viaje", ["Amanda", "Heri"], 2000)
    assert isinstance(bucket_id, UUID)


def test_deposit_to_bucket_increases_balance(wm_in_month_two_members):
    """deposit_to_bucket registra el depósito y el balance del bucket aumenta"""
    wm, _ = wm_in_month_two_members
    bucket_id = wm.create_saving_bucket("Fondo", ["Amanda", "Heri"], 50000)

    wm.deposit_to_saving_bucket(bucket_id, "Amanda", 300.0)  # 30000 céntimos

    bucket = wm.get_bucket_by_id(bucket_id)
    assert bucket.balance == 30000


def test_withdraw_from_bucket_reduces_balance(wm_in_month_two_members):
    """withdraw_from_bucket reduce el balance correctamente"""
    wm, _ = wm_in_month_two_members
    bucket_id = wm.create_saving_bucket("Fondo", ["Amanda", "Heri"], 50000)
    wm.deposit_to_saving_bucket(bucket_id, "Amanda", 300.0)

    wm.withdraw_from_saving_bucket(bucket_id, "Amanda", 100.0)  # 10000 céntimos

    bucket = wm.get_bucket_by_id(bucket_id)
    assert bucket.balance == 20000


def test_withdraw_exceeding_balance_raises(wm_in_month_two_members):
    """Retirar más de lo disponible lanza ValueError"""
    wm, _ = wm_in_month_two_members
    bucket_id = wm.create_saving_bucket("Fondo", ["Amanda", "Heri"], 50000)
    wm.deposit_to_saving_bucket(bucket_id, "Amanda", 100.0)  # 10000 céntimos

    with pytest.raises(ValueError, match="Saldo insuficiente"):
        wm.withdraw_from_saving_bucket(bucket_id, "Amanda", 200.0)


def test_get_all_buckets_returns_all(wm_in_month_two_members):
    """get_all_buckets retorna todos los buckets creados"""
    wm, _ = wm_in_month_two_members
    wm.create_saving_bucket("B1", ["Amanda", "Heri"], 10000)
    wm.create_saving_bucket("B2", ["Amanda", "Heri"], 20000)

    buckets = wm.get_all_buckets()  # Incluye bucket personal de cada persona

    assert len(buckets) == 4  # 2 creados + 1 personal por miembro


def test_get_buckets_by_member_filters_correctly(wm_in_month_two_members):
    """get_buckets_by_member solo retorna buckets del miembro solicitado"""
    wm, _ = wm_in_month_two_members
    wm.create_saving_bucket("Solo Amanda", ["Amanda"], 10000)
    wm.create_saving_bucket("Compartido", ["Amanda", "Heri"], 20000)

    amanda_buckets = wm.get_buckets_by_member("Amanda")
    heri_buckets = wm.get_buckets_by_member("Heri")

    assert len(amanda_buckets) == 3  # 2 + bucket personal
    assert len(heri_buckets) == 2  # 1 + bucket personal


def test_deposit_outside_month_raises(wm):
    """deposit_to_bucket fuera de MONTH lanza ValueError"""
    from uuid import uuid4

    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="month"):
        wm.deposit_to_saving_bucket(uuid4(), "Amanda", 100.0)


def test_withdraw_outside_month_raises(wm):
    """withdraw_from_bucket fuera de MONTH lanza ValueError"""
    from uuid import uuid4

    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="month"):
        wm.withdraw_from_saving_bucket(uuid4(), "Amanda", 100.0)


def test_full_flow_registration_to_closing(wm):
    """Flujo completo de punta a punta: registro → planificación → mes → cierre"""
    # El período nace aquí: start_new_month es el único punto de apertura
    wm.start_new_month()

    # REGISTRATION
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 6000)  # 600000 céntimos
    wm.set_member_incomes("Heri", 4000)  # 400000 céntimos
    assert wm.current_phase == Phase.REGISTRATION

    wm.finish_registration()
    assert wm.current_phase == Phase.PLANNING

    # PLANNING — total income: 1000000¢, PROPORTIONAL: 60% Amanda, 40% Heri
    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.set_budget_for_category("fijos", 5000)  # 500000¢
    wm.set_budget_for_category("variables", 2000)  # 200000¢
    # reserva autocalcula: 1000000 - 500000 - 200000 = 300000¢
    # Amanda 60%: 180000¢ capacity. Heri 40%: 120000¢ capacity.
    amanda_debt = wm.add_debt_bucket(
        name="prestamo", principal_euros=10000, owner="Amanda", installment_euros=100
    )  # cuota 10000¢ — cabe en 180000¢ ✓

    wm.finish_planning()
    assert wm.current_phase == Phase.MONTH

    # MONTH — gastos compartidos en fijos
    wm.register_expense(
        "Amanda", "fijos", 200.0, participants=wm.household.get_member_names()
    )  # 20000¢
    wm.register_expense(
        "Heri", "fijos", 300.0, participants=wm.household.get_member_names()
    )  # 30000¢
    # Total compartido: 50000¢. Amanda should pay 60%=30000¢, Heri 40%=20000¢
    # Amanda pagó 20000¢ (debe 10000¢ más). Heri pagó 30000¢ (pagó 10000¢ de más).
    wm.register_debt_payment("Amanda", amanda_debt, 50.0)  # 5000¢

    settlement = wm.get_settlement()
    assert len(settlement) == 1
    assert settlement[0]["from"] == "amanda"
    assert settlement[0]["to"] == "heri"
    assert settlement[0]["amount"] == 10000  # Amanda le debe 10000¢ a Heri

    wm.finish_month()
    assert wm.current_phase == Phase.CLOSING


# ===============================================
# TESTS: Comienzo de un nuevo mes
# ===============================================


def test_start_new_month_return_to_registration_phase(wm_in_month_two_members):
    """Al comenzar nuevo mes, el status se reinicia"""
    wm, _ = wm_in_month_two_members
    wm.finish_month()
    old_status = wm.current_phase
    wm.start_new_month()
    new_status = wm.current_phase

    assert old_status == Phase.CLOSING
    assert new_status == Phase.REGISTRATION


def test_last_payments_dont_appear_in_new_month(wm):
    """Lo pagado se queda en su mes; la deuda, que es del hogar, cruza al siguiente.

    Necesita fechas de corte reales: el mes se delimita por su ventana temporal,
    así que dos meses simulados el mismo día no se podrían distinguir.
    """
    # ── Mes 1: del 28-ene al 28-feb ──
    wm.start_new_month(start_date=date(2026, 1, 28))
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_member_incomes("Amanda", 6000)
    wm.set_member_incomes("Heri", 4000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 5000)
    debt_id = wm.add_debt_bucket(
        name="prestamo amanda",
        principal_euros=21200,
        owner="Amanda",
        installment_euros=212,
    )
    wm.finish_planning()

    # Pago dentro de la ventana del mes 1
    wm.register_debt_payment(
        member="amanda",
        bucket_id=debt_id,
        amount_euros=150,
        payment_date=datetime(2026, 2, 10),
    )

    totals_month_one = wm.get_debt_status(member="amanda")["totals"]

    # ── Mes 2: arranca donde cerró el mes 1 ──
    wm.finish_month(end_date=date(2026, 2, 28))
    wm.start_new_month()
    wm.set_member_incomes("Amanda", 6000)
    wm.set_member_incomes("Heri", 4000)
    wm.finish_registration()

    totals_month_two = wm.get_debt_status(member="amanda")["totals"]

    assert totals_month_one["paid"] == 15000
    assert totals_month_one["committed"] == 21200

    # El pago se quedó en el mes 1, pero la cuota sigue comprometida
    assert totals_month_two["paid"] == 0
    assert totals_month_two["committed"] == 21200


def test_payment_on_cut_off_day_counts_only_in_the_month_that_starts(wm):
    """El día de corte pertenece al mes que empieza, no a los dos.

    El rango del período es semiabierto [inicio, fin): sin eso, un pago hecho
    justo el día del corte se contaría en el mes que cierra y en el que abre.
    """
    wm.start_new_month(start_date=date(2026, 1, 28))
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 6000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 1000)
    debt_id = wm.add_debt_bucket(
        name="prestamo", principal_euros=21200, owner="Amanda", installment_euros=212
    )
    wm.finish_planning()

    # Pago exactamente el día en que se corta el mes
    wm.register_debt_payment(
        member="amanda",
        bucket_id=debt_id,
        amount_euros=150,
        payment_date=datetime(2026, 2, 28),
    )

    wm.finish_month(end_date=date(2026, 2, 28))
    paid_closed_month = wm.get_debt_status(member="amanda")["totals"]["paid"]

    wm.start_new_month()
    wm.set_member_incomes("Amanda", 6000)
    wm.finish_registration()
    paid_new_month = wm.get_debt_status(member="amanda")["totals"]["paid"]

    assert paid_closed_month == 0
    assert paid_new_month == 15000


def test_open_period_has_no_upper_bound(wm):
    """Mientras el mes sigue abierto no tiene techo: lo registrado hoy cuenta."""
    wm.start_new_month(start_date=date(2026, 1, 28))
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 6000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 1000)
    debt_id = wm.add_debt_bucket(
        name="prestamo", principal_euros=21200, owner="Amanda", installment_euros=212
    )
    wm.finish_planning()

    # Sin payment_date: se sella con la fecha de hoy
    wm.register_debt_payment(member="amanda", bucket_id=debt_id, amount_euros=90)

    assert wm.get_debt_status(member="amanda")["totals"]["paid"] == 9000


@pytest.fixture
def wm_month_from_28_jan(wm):
    """WM en MONTH con un período que arranca el 28-ene-2026 y un bucket de deuda."""
    wm.start_new_month(start_date=date(2026, 1, 28))
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 6000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 1000)
    debt_id = wm.add_debt_bucket(
        name="prestamo", principal_euros=21200, owner="Amanda", installment_euros=212
    )
    wm.finish_planning()
    return wm, debt_id


def test_payment_before_period_start_is_rejected(wm_month_from_28_jan):
    """Un pago con fecha de un período ya cerrado se rechaza con aviso."""
    wm, debt_id = wm_month_from_28_jan

    with pytest.raises(ValueError, match="anterior al inicio del período"):
        wm.register_debt_payment(
            member="amanda",
            bucket_id=debt_id,
            amount_euros=150,
            payment_date=datetime(2026, 1, 20),
        )


def test_payment_on_period_start_day_is_accepted(wm_month_from_28_jan):
    """El día de inicio sí pertenece al período: el rango es [inicio, fin)."""
    wm, debt_id = wm_month_from_28_jan

    wm.register_debt_payment(
        member="amanda",
        bucket_id=debt_id,
        amount_euros=150,
        payment_date=datetime(2026, 1, 28),
    )

    assert wm.get_debt_status(member="amanda")["totals"]["paid"] == 15000


def test_saving_deposit_before_period_start_is_rejected(wm_month_from_28_jan):
    """La misma regla aplica a los movimientos de ahorro."""
    wm, _ = wm_month_from_28_jan
    bucket_id = wm.create_saving_bucket("Viaje", ["Amanda"], 2000)

    with pytest.raises(ValueError, match="anterior al inicio del período"):
        wm.deposit_to_saving_bucket(
            bucket_id=bucket_id,
            member="Amanda",
            amount_euros=100,
            date=datetime(2026, 1, 20),
        )
