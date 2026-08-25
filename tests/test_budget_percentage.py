"""
Tests para funcionalidad de presupuestos por porcentaje
Cubre: set_budget_by_percentage, get_budget_as_percentage, apply_percentage_distribution
"""

import pytest
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.member import Member
from src.workflow.workflow_manager import WorkflowManager
from src.models.constants import Phase


# ====== FIXTURES ======
@pytest.fixture
def household_with_income():
    """Household con 2 miembros y 300000 céntimos totales"""
    budget = Budget()
    tracker = ExpenseTracker()
    household = Household(budget, tracker)
    
    m1 = Member("member1")
    m1.add_incomes(200000)  # 2000€
    household.register_member(m1)
    
    m2 = Member("member2")
    m2.add_incomes(100000)  # 1000€
    household.register_member(m2)
    
    household.set_standard_categories()
    household.freeze_registration_state()
    
    return household


@pytest.fixture
def wm_in_planning():
    """WorkflowManager en fase PLANNING con ingresos registrados"""
    budget = Budget()
    tracker = ExpenseTracker()
    household = Household(budget, tracker)
    wm = WorkflowManager(household)
    
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 2000)
    wm.set_incomes("Heri", 1000)
    wm.finish_registration()  # → PLANNING
    
    wm.set_standard_categories()
    
    return wm


# ====== HOUSEHOLD.set_budget_by_percentage ======
def test_set_budget_by_percentage_basic(household_with_income):
    """set_budget_by_percentage calcula correctamente"""
    # 50% de 300000 = 150000
    household_with_income.set_budget_by_percentage(5000, "fijos")
    
    assert household_with_income.get_category_budget("fijos") == 150000


def test_set_budget_by_percentage_multiple_categories(household_with_income):
    """Puede asignar porcentajes a múltiples categorías"""
    household_with_income.set_budget_by_percentage(5000, "fijos")        # 50%
    household_with_income.set_budget_by_percentage(3000, "variables")    # 30%
    household_with_income.set_budget_by_percentage(2000, "deuda/ahorro") # 20%
    
    assert household_with_income.get_category_budget("fijos") == 150000
    assert household_with_income.get_category_budget("variables") == 90000
    assert household_with_income.get_category_budget("deuda/ahorro") == 60000


def test_set_budget_by_percentage_zero_percent(household_with_income):
    """Permite asignar 0% (presupuesto = 0)"""
    household_with_income.set_budget_by_percentage(0, "fijos")
    
    assert household_with_income.get_category_budget("fijos") == 0


def test_set_budget_by_percentage_100_percent(household_with_income):
    """Permite asignar 100% a una categoría"""
    household_with_income.set_budget_by_percentage(10000, "fijos")
    
    assert household_with_income.get_category_budget("fijos") == 300000


def test_set_budget_by_percentage_overwrites_previous(household_with_income):
    """Sobrescribe presupuesto previo"""
    household_with_income.set_budget_by_percentage(5000, "fijos")  # 50%
    household_with_income.set_budget_by_percentage(6000, "fijos")  # 60%
    
    assert household_with_income.get_category_budget("fijos") == 180000  # 60%


def test_set_budget_by_percentage_with_remainder(household_with_income):
    """División entera maneja remainder correctamente"""
    # 33.33% de 300000 = 99990 (perdemos 10 céntimos)
    household_with_income.set_budget_by_percentage(3333, "fijos")
    
    assert household_with_income.get_category_budget("fijos") == 99990


def test_set_budget_by_percentage_category_not_exists_raises(household_with_income):
    """Falla si categoría no existe"""
    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_income.set_budget_by_percentage(5000, "inexistente")


# ====== HOUSEHOLD.get_budget_as_percentage ======
def test_get_budget_as_percentage_basic(household_with_income):
    """get_budget_as_percentage es inversa de set_budget_by_percentage"""
    household_with_income.set_budget_by_percentage(5000, "fijos")  # 50%
    
    pct = household_with_income.get_budget_as_percentage("fijos")
    
    assert pct == 5000


def test_get_budget_as_percentage_with_absolute_amount(household_with_income):
    """Calcula % correctamente desde monto absoluto"""
    household_with_income.set_budget_for_category("fijos", 150000)  # Set manual
    
    pct = household_with_income.get_budget_as_percentage("fijos")
    
    # 150000 / 300000 = 50%
    assert pct == 5000


def test_get_budget_as_percentage_with_remainder(household_with_income):
    """División entera pierde precisión en remainder"""
    household_with_income.set_budget_for_category("fijos", 100000)  # Set manual
    
    pct = household_with_income.get_budget_as_percentage("fijos")
    
    # 100000 / 300000 * 10000 = 3333.33 → 3333
    assert pct == 3333


def test_get_budget_as_percentage_zero_budget(household_with_income):
    """Retorna 0 si presupuesto es 0"""
    household_with_income.set_budget_by_percentage(0, "fijos")
    
    pct = household_with_income.get_budget_as_percentage("fijos")
    
    assert pct == 0


def test_get_budget_as_percentage_category_not_exists_raises(household_with_income):
    """Falla si categoría no existe"""
    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_income.get_budget_as_percentage("inexistente")


# ====== WORKFLOWMANAGER.set_budget_by_percentage ======
def test_wm_set_budget_by_percentage_converts_float_to_basis(wm_in_planning):
    """WorkflowManager convierte float a basis points"""
    wm_in_planning.set_budget_by_percentage("fijos", 50.5)  # Float input
    
    # 50.5% de 300000 = 151500
    assert wm_in_planning.get_category_budget("fijos") == 151500


def test_wm_set_budget_by_percentage_validates_phase(wm_in_planning):
    """Solo funciona en fase PLANNING"""
    wm_in_planning.finish_planning()  # → MONTH
    
    with pytest.raises(ValueError, match="solo permitida en fase PLANNING"):
        wm_in_planning.set_budget_by_percentage("fijos", 50)


# ====== WORKFLOWMANAGER.get_budget_as_percentage ======  
def test_wm_get_budget_as_percentage_returns_basis_points(wm_in_planning):
    """get_budget_as_percentage retorna basis points"""
    wm_in_planning.set_budget_by_percentage("fijos", 50)
    
    pct = wm_in_planning.get_budget_as_percentage("fijos")
    
    assert pct == 5000  # basis points, no float


def test_wm_get_budget_as_percentage_accessible_in_planning(wm_in_planning):
    """Funciona en fase PLANNING"""
    wm_in_planning.set_budget_by_percentage("fijos", 50)
    
    # No debe fallar en PLANNING
    pct = wm_in_planning.get_budget_as_percentage("fijos")
    assert pct == 5000


def test_wm_get_budget_as_percentage_accessible_in_month(wm_in_planning):
    """Funciona en fase MONTH"""
    wm_in_planning.set_budget_by_percentage("fijos", 50)
    wm_in_planning.set_budget_by_percentage("variables", 50)
    wm_in_planning.finish_planning()  # → MONTH
    
    pct = wm_in_planning.get_budget_as_percentage("fijos")
    assert pct == 5000


# ====== WORKFLOWMANAGER.apply_percentage_distribution ======
def test_apply_percentage_distribution_basic(wm_in_planning):
    """apply_percentage_distribution asigna múltiples presupuestos"""
    wm_in_planning.apply_percentage_distribution({
        "fijos": 50,
        "variables": 30,
        "deuda/ahorro": 20
    })
    
    assert wm_in_planning.get_category_budget("fijos") == 150000
    assert wm_in_planning.get_category_budget("variables") == 90000
    assert wm_in_planning.get_category_budget("deuda/ahorro") == 60000


def test_apply_percentage_distribution_sum_100_percent(wm_in_planning):
    """Permite suma exactamente 100%"""
    wm_in_planning.apply_percentage_distribution({
        "fijos": 50,
        "variables": 30,
        "deuda/ahorro": 20
    })
    
    total = wm_in_planning.get_total_budgeted()
    assert total == 300000  # 100% de ingresos


def test_apply_percentage_distribution_sum_less_than_100(wm_in_planning):
    """Permite suma < 100%"""
    wm_in_planning.apply_percentage_distribution({
        "fijos": 50,
        "variables": 30
    })  # Total: 80%
    
    total = wm_in_planning.get_total_budgeted()
    loose = wm_in_planning.get_loose_money()
    
    assert total == 240000  # 80%
    assert loose == 60000   # 20% restante


def test_apply_percentage_distribution_fails_if_sum_exceeds_100(wm_in_planning):
    """Falla si suma >100%"""
    with pytest.raises(ValueError, match="suman 110%, máximo 100%"):
        wm_in_planning.apply_percentage_distribution({
            "fijos": 60,
            "variables": 30,
            "deuda/ahorro": 20
        })  # Total: 110%


def test_apply_percentage_distribution_fails_if_category_not_exists(wm_in_planning):
    """Falla si alguna categoría no existe"""
    with pytest.raises(ValueError, match="Categorías no existen.*inexistente"):
        wm_in_planning.apply_percentage_distribution({
            "fijos": 50,
            "inexistente": 50
        })


def test_apply_percentage_distribution_validates_all_before_applying(wm_in_planning):
    """Valida TODO antes de aplicar NADA (operación atómica)"""
    with pytest.raises(ValueError, match="no existen"):
        wm_in_planning.apply_percentage_distribution({
            "fijos": 30,
            "variables": 30,
            "inexistente": 40
        })
    
    # Ninguna categoría debe tener presupuesto
    assert wm_in_planning.get_category_budget("fijos") == 0
    assert wm_in_planning.get_category_budget("variables") == 0


def test_apply_percentage_distribution_with_empty_dict(wm_in_planning):
    """Permite dict vacío (no hace nada)"""
    wm_in_planning.apply_percentage_distribution({})
    
    assert wm_in_planning.get_total_budgeted() == 0


def test_apply_percentage_distribution_validates_phase(wm_in_planning):
    """Solo funciona en fase PLANNING"""
    wm_in_planning.set_budget_by_percentage("fijos", 100)
    wm_in_planning.finish_planning()  # → MONTH
    
    with pytest.raises(ValueError, match="solo permitida en fase PLANNING"):
        wm_in_planning.apply_percentage_distribution({"variables": 50})


def test_apply_percentage_distribution_overwrites_existing(wm_in_planning):
    """Sobrescribe presupuestos existentes"""
    wm_in_planning.set_budget_by_percentage("fijos", 50)
    
    wm_in_planning.apply_percentage_distribution({
        "fijos": 60,
        "variables": 40
    })
    
    # Fijos sobrescrito de 50% → 60%
    assert wm_in_planning.get_category_budget("fijos") == 180000  # 60%


# ====== EDGE CASES COMPLEJOS ======
def test_percentage_roundtrip_loses_precision_with_remainder():
    """SET → GET puede perder precisión por división entera"""
    budget = Budget()
    tracker = ExpenseTracker()
    household = Household(budget, tracker)
    
    m = Member("test")
    m.add_incomes(100000)  # 1000€
    household.register_member(m)
    household.set_standard_categories()
    household.freeze_registration_state()
    
    # 33.33% → 33330 cents
    household.set_budget_by_percentage(3333, "fijos")
    retrieved = household.get_budget_as_percentage("fijos")
    
    # 33330 / 100000 * 10000 = 3333 (exacto en este caso)
    assert retrieved == 3333


def test_multiple_percentages_remainder_accumulates():
    """Remainder se acumula al asignar múltiples %"""
    budget = Budget()
    tracker = ExpenseTracker()
    household = Household(budget, tracker)
    
    m = Member("test")
    m.add_incomes(1000)