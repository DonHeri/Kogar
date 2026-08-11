import pytest

from src.workflow.incomes_entries_service import IncomeEntryService
from src.models.household import Household

from src.models.income_entry import IncomeEntry
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense import Expense
from src.models.budget import Budget
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.member import Member
from src.models.constants import MetodoReparto
from src.workflow.budget_distribution_service import BudgetDistributionService


# ===============================================
# ----------------- FIXTURES --------------------
# ===============================================


@pytest.fixture
def members_with_incomes() -> dict[str, Member]:
    """Dos miembros con ingresos diferentes"""
    m1 = Member("Member1")
    m2 = Member("Member2")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    return {m1.name: m1, m2.name: m2}


@pytest.fixture
def full_household(members_with_incomes: dict[str, Member]) -> Household:
    """Crea un hogar con los miembros proporcionados"""
    b = Budget()
    e = ExpenseTracker()
    s = SavingBucketTracker()
    d = DebtBucketTracker()
    household = Household(
        budget=b, expense_tracker=e, saving_bucket_tracker=s, debt_bucket_tracker=d
    )
    for member in members_with_incomes.values():
        household.register_member(member)
    household.prepare_period()

    household.set_distribution_method(method=MetodoReparto.EQUAL)
    BudgetDistributionService.set_budget_by_percentages(
        household=household,
        percentages={"fijos": 5000, "variables": 2000, "reserva": 3000},
    )
    return household


@pytest.fixture
def full_household_with_child_categories(full_household: Household) -> Household:
    """Household con dos hijas (vivienda, suministros) colgando de fijos."""
    full_household.add_category("vivienda", parent="fijos")
    full_household.add_category("suministros", parent="fijos")
    return full_household


# ===============================================
# --------------- add_income --------------------
# ===============================================
def test_add_income_entry_records_it_without_touching_the_plan(
    full_household: Household,
) -> None:
    """Un ingreso extra se registra como hecho del mes y no mueve el presupuesto.

    Antes suba la reserva, y con ella cambiaba lo que debía cada miembro: el extra
    que cobraba uno se repartía entre todos. Este test es la red que impide que
    vuelva a colarse si alguien reconecta el servicio.
    """

    last_incomes = full_household.get_total_incomes()
    entry = IncomeEntry(
        member_name="member1",
        amount_cents=50000,
    )
    last_reserve = full_household.get_category_planned_amount("reserva")
    categories_budgets = {
        name: full_household.get_category_planned_amount(name)
        for name in full_household.get_active_categories()
    }

    IncomeEntryService.add_income_entry(income_entry=entry, household=full_household)

    # El hecho queda registrado
    assert len(full_household._income_entries) == 1
    entry = full_household._income_entries[0]
    assert entry.amount_cents == 50000
    assert entry.member_name == "member1"

    # Y el plan no se entera: ni el ingreso total ni ninguna categoría se mueven
    assert full_household.get_total_incomes() == last_incomes
    assert full_household.get_category_planned_amount("reserva") == last_reserve
    assert categories_budgets["fijos"] == full_household.get_category_planned_amount(
        "fijos"
    )
    assert categories_budgets[
        "variables"
    ] == full_household.get_category_planned_amount("variables")
