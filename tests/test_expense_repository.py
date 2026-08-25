import pytest
import psycopg2

from tests.helpers import make_category
from src.models.category import Category
from src.models.member import Member
from src.models.expense import Expense
from src.models.period import Period
from src.models.constants import Phase, MetodoReparto
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.expense_repository import ExpenseRepository
from src.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


# ===============================================
# FIXTURES
# ===============================================


# ====== Conexión ======
@pytest.fixture
def conn():
    """Conexión directa sin commit — rollback automático al finalizar cada test"""
    connection = psycopg2.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, port=DB_PORT
    )
    yield connection
    connection.rollback()
    connection.close()


# ====== Repositorios ======
@pytest.fixture
def household_repo(conn):
    """Repositorio de hogares con conexión de test"""
    return HouseholdRepository(conn)


@pytest.fixture
def member_repo(conn):
    """Repositorio de miembros con conexión de test"""
    return MemberRepository(conn)


@pytest.fixture
def period_repo(conn):
    """Repositorio de períodos con conexión de test"""
    return PeriodRepository(conn)


@pytest.fixture
def expense_repo(conn):
    """Repositorio de expenses con conexión de test"""
    return ExpenseRepository(conn)


# ======  ======
@pytest.fixture
def household_id(household_repo):  # TODO cambiar name
    household_id = household_repo.save()

    return household_id


@pytest.fixture
def id_member_1(household_id, member_repo):  # TODO cambiar name
    member = Member("Heri")
    member.add_incomes(135400)

    id = member_repo.save(member=member, household_id=household_id)

    return id


@pytest.fixture
def id_member_2(household_id, member_repo):  # TODO cambiar name
    member = Member("Amanda")
    member.add_incomes(146700)
    id = member_repo.save(member=member, household_id=household_id)

    return id


@pytest.fixture
def period_id(household_id, period_repo):
    period = Period(
        household_id=household_id,
        year=2026,
        month=2,
        status=Phase.PLANNING,
        method=MetodoReparto.EQUAL,
    )

    id = period_repo.save(period=period)

    return id


@pytest.fixture
def member_ids(id_member_1, id_member_2):
    return {"heri": id_member_1, "amanda": id_member_2}


@pytest.fixture
def id_sample_expense(expense_repo, member_ids, period_id) -> int:
    expense = Expense(
        member="heri",
        amount_cents=34600,
        category=make_category("fijos", is_shared=True),
        participants=["heri", "amanda"],
    )

    id = expense_repo.save(expense=expense, member_ids=member_ids, period_id=period_id)

    return id


# ===============================================
# save
# ===============================================


def test_save_return_correct_id(expense_repo, member_ids, period_id):
    expense = Expense(
        member="heri",
        amount_cents=34600,
        category=make_category("fijos", is_shared=True),
        participants=["heri", "amanda"],
    )

    id = expense_repo.save(expense=expense, member_ids=member_ids, period_id=period_id)

    assert id > 0
    assert isinstance(id, int)


def test_find_by_period_return_saved_expense(
    id_member_1, id_sample_expense, expense_repo, period_id
):
    id = id_sample_expense

    expense = expense_repo.find_by_period(period_id=period_id)[0]

    assert expense["category"] == "fijos"
    assert expense["amount_cents"] == 34600
    assert expense["payer_id"] == id_member_1


def test_find_with_participant_return_participants(
    id_member_1, expense_repo, period_id, id_sample_expense
):
    expense = id_sample_expense
    expenses_with_participants = expense_repo.find_with_participants(period_id)[0]

    assert len(expenses_with_participants["participants"]) == 2
    assert expenses_with_participants["payer_id"] == id_member_1
    assert "amanda" in expenses_with_participants["participants"]
