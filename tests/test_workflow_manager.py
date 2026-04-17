import pytest

from src.models.budget import Budget
from src.models.constants import MetodoReparto, Phase
from src.models.debt_tracker import DebtTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.saving_tracker import SavingTracker
from src.workflow.workflow_manager import WorkflowManager

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def household():
    return Household(Budget(), ExpenseTracker(), SavingTracker(), DebtTracker())


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
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
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

    wm.set_budget_for_category("fijos", 2000)
    assert wm.household.get_category_budget("fijos") == 200000


def test_set_budget_for_category_raises_if_not_in_planning(wm):
    """set_budget_for_category lanza ValueError si no estamos en PLANNING"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")

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
    assert summary["missing_money"]["total"] == 200000
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
        "missing_money",
        "contributions_preview",
    }

    assert required_keys.issubset(set(summary.keys()))


def test_get_planning_summary_returns_negative_missing_money_when_over_budget(wm):
    """get_planning_summary permite over-budget y muestra missing_money negativo"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    # Ingresos: 300000€ — presupuesto: 700000€
    wm.set_budget_for_category("fijos", 4000)
    wm.set_budget_for_category("variables", 3000)

    summary = wm.get_planning_summary()

    assert summary["missing_money"]["total"] == -400000


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

    with pytest.raises(ValueError, match="al menos una categoría"):
        wm.finish_planning()


def test_finish_planning_raises_if_no_budget_assigned(wm):
    """finish_planning lanza ValueError si no hay presupuesto asignado"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 5000)
    wm.finish_registration()

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

    assert wm.household._agreed_percentages == {}
    assert wm.household._agreed_contributions == {}

    wm.finish_planning()

    assert wm.household._agreed_percentages == {"amanda": 6000, "heri": 4000}
    assert "fijos" in wm.household._agreed_contributions
    assert "variables" in wm.household._agreed_contributions

    fijos_contrib = wm.household._agreed_contributions["fijos"]
    assert "contributions" in fijos_contrib
    assert fijos_contrib["contributions"]["amanda"] == 300000  # 60% de 500000
    assert fijos_contrib["contributions"]["heri"] == 200000   # 40% de 500000


def test_finish_planning_allows_over_budget(wm):
    """finish_planning no bloquea aunque el presupuesto supere los ingresos"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 1000)
    wm.finish_registration()

    # Presupuesto total: 1500€ > ingresos: 1000€
    wm.set_budget_for_category("fijos", 1500)

    wm.finish_planning()  # no debe lanzar

    from src.models.constants import Phase
    assert wm.current_phase == Phase.MONTH


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
    assert "reserva" in categories


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
    assert frozen_contributions["fijos"]["contributions"]["heri"] == 200000   # 40%


def test_get_agreed_contributions_fails_in_planning(wm):
    """get_agreed_contributions() lanza error en PLANNING"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(
        ValueError, match="Operación solo permitida en fase transcurso_mes"
    ):
        wm.get_agreed_contributions()


# ====================================================
# TESTS: set_custom_splits
# ====================================================

def test_set_custom_splits_in_planning_phase(wm):
    """set_custom_splits() establece porcentajes personalizados en PLANNING"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    wm.set_custom_splits({"amanda": 70.0, "heri": 30.0})

    assert wm.household._custom_splits == {"amanda": 7000, "heri": 3000}


def test_set_custom_splits_raises_if_not_in_planning(wm):
    """set_custom_splits() lanza error si no estamos en PLANNING"""
    wm.register_member("Amanda")

    with pytest.raises(ValueError, match="planificación"):
        wm.set_custom_splits({"Amanda": 100.0})


# ====================================================
# TESTS: preview_budget_contribution_summary y get_current_contributions
# ====================================================

def test_preview_budget_contribution_summary_in_planning(wm):
    """preview_budget_contribution_summary() muestra preview con método específico"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
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
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)
    wm.finish_registration()

    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.set_budget_for_category("fijos", 5000)

    contributions = wm.get_current_contributions()

    assert "fijos" in contributions
    assert contributions["fijos"]["contributions"]["amanda"] == 300000  # 60%
    assert contributions["fijos"]["contributions"]["heri"] == 200000   # 40%


# ====================================================
# TESTS: register_expense (MONTH phase)
# ====================================================

def test_register_expense_in_month_phase(wm):
    """register_expense() registra gasto correctamente en MONTH"""
    from src.models.expense import Expense

    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "fijos", 500.50, "Alquiler")

    expenses = wm.household.expense_tracker.expenses
    assert len(expenses) == 1
    assert expenses[0].member == "amanda"
    assert expenses[0].category == "fijos"
    assert expenses[0].amount == 50050
    assert expenses[0].description == "Alquiler"


def test_register_expense_converts_euros_to_cents(wm):
    """register_expense() convierte euros a céntimos correctamente"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
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
    wm.set_incomes("Amanda", 3000)
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
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "  fijos  ", 100.00, "  Alquiler  ")

    expense = wm.household.expense_tracker.expenses[0]
    assert expense.category == "fijos"
    assert expense.description == "Alquiler"


def test_register_expense_raises_if_not_in_month(wm):
    """register_expense() lanza error si no estamos en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="transcurso_mes"):
        wm.register_expense("Amanda", "fijos", 100.00)


def test_register_expense_empty_description_ok(wm):
    """register_expense() acepta description vacía"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "fijos", 100.00, "")

    expense = wm.household.expense_tracker.expenses[0]
    assert expense.description == ""


def test_register_expense_derives_is_shared_from_category_behavior(wm):
    """Sin is_shared explícito, se deriva del CategoryBehavior de la categoría"""
    from src.models.constants import CategoryBehavior

    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()
    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "fijos", 100.00)     # SHARED → is_shared=True
    wm.register_expense("Amanda", "variables", 50.00)  # PERSONAL → is_shared=False

    expenses = wm.household.expense_tracker.expenses
    assert expenses[0].is_shared is True
    assert expenses[1].is_shared is False


def test_register_expense_explicit_is_shared_overrides_behavior(wm):
    """is_shared explícito sobreescribe el default de la categoría"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()
    wm.set_budget_for_category("variables", 1000)
    wm.finish_planning()

    # variables es PERSONAL por defecto, pero el usuario lo marca como compartido
    wm.register_expense("Amanda", "variables", 80.00, is_shared=True)

    expense = wm.household.expense_tracker.expenses[0]
    assert expense.is_shared is True


# ====================================================
# TESTS: get_registration_summary y get_month_summary
# ====================================================

def test_get_registration_summary_in_registration_phase(wm):
    """get_registration_summary() retorna resumen en REGISTRATION"""
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 2000)

    summary = wm.get_registration_summary()

    assert "members" in summary
    assert "member_incomes" in summary
    assert "total_household_income" in summary
    assert summary["members"] == ["amanda", "heri"]
    assert summary["total_household_income"] == 500000


def test_get_registration_summary_after_freezing(wm):
    """get_registration_summary() funciona después de congelar ingresos"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    summary = wm.get_registration_summary()

    assert summary["total_household_income"] == 300000


def test_get_month_summary_in_month_phase(wm):
    """get_month_summary() retorna resumen completo en MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 2000)
    wm.finish_planning()

    wm.register_expense("Amanda", "fijos", 500.00)

    summary = wm.get_month_summary()

    assert "totals" in summary
    assert "by_category" in summary
    assert summary["totals"]["total_budgeted"] == 200000
    assert summary["totals"]["total_spent"] == 50000


def test_get_month_summary_raises_if_not_in_month(wm):
    """get_month_summary() lanza error si no estamos en MONTH"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="transcurso_mes"):
        wm.get_month_summary()


# ====================================================
# TESTS: set_budget_by_percentage (WorkflowManager)
# ====================================================


def test_set_budget_by_percentage_wrong_phase(wm):
    """set_budget_by_percentage lanza error si no estamos en PLANNING"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)

    with pytest.raises(ValueError, match="planificación"):
        wm.set_budget_by_percentage("fijos", 50.0)


def test_set_budget_by_percentage_converts_float_to_basis(wm):
    """Convierte porcentaje float a basis points y llama a Household"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_by_percentage("fijos", 50.0)

    # 50% de 300000 céntimos = 150000
    assert wm.household.budget.get_category_budget("fijos") == 150000


def test_set_budget_by_percentage_fractional(wm):
    """Maneja correctamente porcentajes fraccionarios"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_by_percentage("variables", 33.33)

    # 33.33% de 300000 = 99990 céntimos
    assert wm.household.budget.get_category_budget("variables") == 99990


def test_set_budget_by_percentage_zero(wm):
    """Asigna 0 cuando el porcentaje es 0"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_by_percentage("reserva", 0.0)

    assert wm.household.budget.get_category_budget("reserva") == 0


# ====================================================
# TESTS: get_budget_as_percentage (WorkflowManager)
# ====================================================


def test_get_budget_as_percentage_wrong_phase(wm):
    """get_budget_as_percentage lanza error si no estamos en PLANNING"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)

    with pytest.raises(ValueError, match="planificación"):
        wm.get_budget_as_percentage("fijos")


def test_get_budget_as_percentage_returns_basis_points(wm):
    """Retorna basis points representando % de ingresos"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("fijos", 1500)  # 50% de 3000€

    pct_basis = wm.get_budget_as_percentage("fijos")

    assert pct_basis == 5000  # 50%


def test_get_budget_as_percentage_zero_budget(wm):
    """Retorna 0 cuando presupuesto es 0"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_for_category("variables", 0)

    pct_basis = wm.get_budget_as_percentage("variables")

    assert pct_basis == 0


def test_get_budget_as_percentage_roundtrip(wm):
    """set_budget_by_percentage + get_budget_as_percentage es consistente"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_budget_by_percentage("reserva", 40.0)
    retrieved = wm.get_budget_as_percentage("reserva")

    assert retrieved == 4000  # 40%


# ====================================================
# TESTS: apply_percentage_distribution (WorkflowManager)
# ====================================================


def test_apply_percentage_distribution_basic(wm):
    """Asigna presupuestos basados en distribución porcentual"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.apply_percentage_distribution(
        {"fijos": 50.0, "variables": 30.0, "reserva": 20.0}
    )

    # Ingresos: 300000 céntimos
    assert wm.household.budget.get_category_budget("fijos") == 150000    # 50%
    assert wm.household.budget.get_category_budget("variables") == 90000  # 30%
    assert wm.household.budget.get_category_budget("reserva") == 60000   # 20%


def test_apply_percentage_distribution_sum_exceeds_100(wm):
    """Lanza error si la suma de porcentajes excede 100%"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="suman.*%.*máximo.*100%"):
        wm.apply_percentage_distribution(
            {"fijos": 60.0, "variables": 50.0, "reserva": 20.0}
        )


def test_apply_percentage_distribution_missing_category(wm):
    """Lanza error si alguna categoría no existe en el presupuesto"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    with pytest.raises(ValueError, match="Categorías no existen"):
        wm.apply_percentage_distribution(
            {"fijos": 50.0, "categoria_falsa": 30.0, "otra_falsa": 20.0}
        )


def test_apply_percentage_distribution_partial_allocation(wm):
    """Permite distribución parcial (suma < 100%)"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.apply_percentage_distribution({"fijos": 50.0, "variables": 20.0})

    assert wm.household.budget.get_category_budget("fijos") == 150000   # 50%
    assert wm.household.budget.get_category_budget("variables") == 60000  # 20%


def test_apply_percentage_distribution_wrong_phase(wm):
    """Lanza error si no estamos en PLANNING"""
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)

    with pytest.raises(ValueError, match="planificación"):
        wm.apply_percentage_distribution({"fijos": 50.0})


def test_apply_percentage_distribution_empty_dict(wm):
    """Maneja correctamente diccionario vacío (no hace nada)"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.apply_percentage_distribution({})

    assert wm.household.budget.get_category_budget("fijos") == 0


def test_apply_percentage_distribution_fractional_percentages(wm):
    """Maneja correctamente porcentajes fraccionarios en distribución"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.apply_percentage_distribution(
        {"fijos": 33.33, "variables": 33.33, "reserva": 33.34}
    )

    # Ingresos: 300000 céntimos (3000€)
    assert wm.household.budget.get_category_budget("fijos") == 99990
    assert wm.household.budget.get_category_budget("variables") == 99990
    assert wm.household.budget.get_category_budget("reserva") == 100020


# ====================================================
# TESTS: finish_month
# ====================================================


@pytest.fixture
def wm_in_month(wm):
    """WM listo en fase MONTH"""
    wm.household.budget.set_standard_categories()
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
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