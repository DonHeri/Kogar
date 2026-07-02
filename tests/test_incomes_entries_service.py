import pytest

from src.workflow.incomes_entries_service import IncomeEntryService
from src.models.household import Household

from src.models.income_entry import IncomeEntry
from src.models.debt_tracker import DebtTracker
from src.models.expense import Expense
from src.models.budget import Budget
from src.models.saving_tracker import SavingTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.member import Member
from src.models.constants import MetodoReparto
from src.workflow.budget_distribution_service import BudgetDistributionService


# ===============================================
# ----------------- FIXTURES --------------------
# ===============================================


@pytest.fixture
def members_with_incomes():
    """Dos miembros con ingresos diferentes"""
    m1 = Member("Member1")
    m2 = Member("Member2")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    return {m1.name: m1, m2.name: m2}


@pytest.fixture
def full_household(members_with_incomes):
    """Crea un hogar con los miembros proporcionados"""
    b = Budget()
    e = ExpenseTracker()
    s = SavingTracker()
    d = DebtTracker()
    household = Household(budget=b, expense_tracker=e, saving_tracker=s, debt_tracker=d)
    for member in members_with_incomes.values():
        household.register_member(member)
    household.freeze_registration_state()

    household.assign_distribution_method(method=MetodoReparto.EQUAL)
    BudgetDistributionService.set_budget_by_percentages(
        household=household,
        percentages={"fijos": 5000, "variables": 2000, "reserva": 3000},
    )
    return household


@pytest.fixture
def full_household_with_child_categories(full_household):
    """Household con dos hijas (vivienda, suministros) colgando de fijos."""
    full_household.add_category("vivienda", parent="fijos")
    full_household.add_category("suministros", parent="fijos")
    return full_household


# ===============================================
# --------------- add_income --------------------
# ===============================================
def test_add_income_entry_creates_entry(full_household):
    """Verifica que se cree una entrada de ingreso al agregar un ingreso."""

    last_incomes = full_household.get_total_incomes()
    entry = IncomeEntry(
        member_name="member1",
        amount_cents=50000,
    )
    last_reserve = full_household.get_category_budget("reserva")
    categories_budgets = {
        name: full_household.get_category_budget(name)
        for name in full_household.get_active_categories()
    }

    IncomeEntryService.add_income_entry(income_entry=entry, household=full_household)
    new_reserve = full_household.get_category_budget("reserva")

    assert new_reserve == last_reserve + 50000
    assert len(full_household._income_entries) == 1
    entry = full_household._income_entries[0]
    assert entry.amount_cents == 50000
    assert entry.member_name == "member1"
    assert full_household.get_total_incomes() == last_incomes + 50000

    # Cambia total, pero no cambia la distribución de los presupuestos de las categorías
    assert categories_budgets["fijos"] == full_household.get_category_budget("fijos")
    assert categories_budgets["variables"] == full_household.get_category_budget(
        "variables"
    )
