import pytest

from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.member import Member
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.utils.currency import to_cents
from src.workflow.settlement_calculator import SettlementCalculator
from tests.helpers import make_category


def _setup_settlement(hh):
    """Congela estados para habilitar el settlement"""
    hh.prepare_period()
    hh.freeze_planning_state()


def _get_settlement(hh):
    return SettlementCalculator.calculate(hh)


# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def members_with_incomes() -> dict[str, Member]:
    """Dos miembros con ingresos diferentes"""
    m1 = Member("Member1")
    m2 = Member("Member2")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    return {m1.name: m1, m2.name: m2}


@pytest.fixture
def base_household() -> Household:
    b = Budget()
    e = ExpenseTracker()
    s = SavingBucketTracker()
    d = DebtBucketTracker()
    b.set_standard_categories()
    return Household(
        budget=b,
        expense_tracker=e,
        saving_bucket_tracker=s,
        debt_bucket_tracker=d,
        method=MetodoReparto.EQUAL,
    )


@pytest.fixture
def household_with_members(
    base_household: Household, members_with_incomes: dict[str, Member]
) -> Household:
    """Household ya configurado con dos miembros con ingresos"""
    for member in members_with_incomes.values():
        base_household.register_member(member)
    return base_household


# ====================================================
# TESTS: calculate
# ====================================================


def test_get_settlement_empty_when_no_shared_expenses(
    household_with_members: Household,
) -> None:
    """Sin gastos compartidos el settlement es vacío"""

    _setup_settlement(household_with_members)

    household_with_members.expense_tracker.add_expense(
        Expense(
            "member1",
            make_category("variables", is_shared=False),
            50000,
            participants=["member1"],
        )
    )

    assert _get_settlement(household_with_members) == []


def test_expense_shared_flag_behavior(
    household_with_members: Household,
) -> None:
    """Un gasto pagado por un miembro pero que es del otro no se contabiliza en el settlement del pagador"""

    _setup_settlement(household_with_members)

    household_with_members.expense_tracker.add_expense(
        Expense("member1", make_category("variables"), 10000, ["member2"])
    )

    assert _get_settlement(household_with_members)[0]["from"] == "member2"
    assert _get_settlement(household_with_members)[0]["to"] == "member1"
    assert _get_settlement(household_with_members)[0]["amount"] == 10000


def test_get_settlement_empty_when_no_expenses(
    household_with_members: Household,
) -> None:
    """Sin gastos en absoluto el settlement es vacío"""
    _setup_settlement(household_with_members)
    assert _get_settlement(household_with_members) == []


def test_get_settlement_one_paid_all_equal_split(
    household_with_members: Household,
) -> None:
    """member1 pagó todo lo compartido — member2 le debe la mitad (EQUAL)"""

    _setup_settlement(household_with_members)

    # member1 paga 10000 compartido, member2 no paga nada
    # EQUAL: cada uno debe 5000 → member2 debe 5000 a member1
    household_with_members.expense_tracker.add_expense(
        Expense(
            "member1",
            make_category("fijos"),
            10000,
            participants=["member1", "member2"],
        )
    )

    transfers = _get_settlement(household_with_members)

    assert len(transfers) == 1
    assert transfers[0]["from"] == "member2"
    assert transfers[0]["to"] == "member1"
    assert transfers[0]["amount"] == 5000


def test_get_settlement_ignores_non_shared_expenses(
    household_with_members: Household,
) -> None:
    """Los gastos is_shared=False no entran en el settlement"""

    _setup_settlement(household_with_members)
    members = household_with_members.get_member_names()
    household_with_members.expense_tracker.add_expense(
        Expense("member1", make_category("fijos"), 10000, participants=members)
    )
    household_with_members.expense_tracker.add_expense(
        Expense(
            "member1",
            make_category("variables", is_shared=False),
            99999,
            participants=["member1"],
        )
    )

    transfers = _get_settlement(household_with_members)

    assert len(transfers) == 1
    assert transfers[0]["amount"] == 5000  # solo el gasto compartido cuenta


def test_get_settlement_already_balanced(household_with_members: Household) -> None:
    """Si cada uno pagó exactamente su parte no hay transferencias"""

    _setup_settlement(household_with_members)

    # EQUAL → cada uno debe 5000 de 10000 total
    household_with_members.expense_tracker.add_expense(
        Expense(
            "member1",
            make_category("fijos"),
            5000,
            participants=household_with_members.get_member_names(),
        )
    )
    household_with_members.expense_tracker.add_expense(
        Expense(
            "member2",
            make_category("fijos"),
            5000,
            participants=household_with_members.get_member_names(),
        )
    )

    assert _get_settlement(household_with_members) == []


def test_get_settlement_three_members_equal(base_household: Household) -> None:
    """3 miembros EQUAL: uno paga todo → los otros dos le deben a partes iguales"""
    m1, m2, m3 = Member("alice"), Member("bob"), Member("carol")
    for m in (m1, m2, m3):
        m.monthly_income = 100000
        base_household.register_member(m)

    _setup_settlement(base_household)

    # alice paga 3000 compartido, bob y carol no pagan nada
    # EQUAL: cada uno debe 1000 → bob y carol deben 1000 c/u a alice
    base_household.expense_tracker.add_expense(
        Expense(
            "alice",
            make_category("fijos"),
            3000,
            participants=base_household.get_member_names(),
        )
    )

    transfers = _get_settlement(base_household)

    assert len(transfers) == 2
    assert all(t["to"] == "alice" for t in transfers)
    assert all(t["amount"] == 1000 for t in transfers)
    froms = {t["from"] for t in transfers}
    assert froms == {"bob", "carol"}


def test_get_settlement_three_members_only_should_pay_two(
    base_household: Household,
) -> None:
    """3 miembros EQUAL: uno paga todo → los otros dos le deben a partes iguales"""
    m1, m2, m3 = Member("alice"), Member("bob"), Member("carol")
    for m in (m1, m2, m3):
        m.monthly_income = 100000
        base_household.register_member(m)

    _setup_settlement(base_household)

    # alice paga 3000 compartido con carol
    base_household.expense_tracker.add_expense(
        Expense("alice", make_category("fijos"), 3000, participants=["alice", "carol"])
    )

    transfers = _get_settlement(base_household)
    assert len(transfers) == 1
    assert transfers[0]["to"] == "alice"
    assert transfers[0]["from"] == "carol"
    assert transfers[0]["amount"] == 1500
