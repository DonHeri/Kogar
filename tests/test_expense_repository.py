from datetime import date

import pytest
import psycopg2

from tests.helpers import make_category
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


@pytest.fixture
def conn():
    """Conexión directa sin commit — rollback automático al finalizar cada test."""
    connection = psycopg2.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, port=DB_PORT
    )
    yield connection
    connection.rollback()
    connection.close()


@pytest.fixture
def household_repo(conn):
    """Repositorio de hogares con conexión de test."""
    return HouseholdRepository(conn)


@pytest.fixture
def member_repo(conn):
    """Repositorio de miembros con conexión de test."""
    return MemberRepository(conn)


@pytest.fixture
def period_repo(conn):
    """Repositorio de períodos con conexión de test."""
    return PeriodRepository(conn)


@pytest.fixture
def expense_repo(conn):
    """Repositorio de gastos con conexión de test."""
    return ExpenseRepository(conn)


@pytest.fixture
def household_id(household_repo):
    """Hogar creado en BD listo para usar en tests."""
    return household_repo.save()


@pytest.fixture
def member_id_heri(household_id, member_repo):
    """Miembro Heri creado en BD."""
    member = Member("Heri")
    member.add_incomes(135400)
    return member_repo.save(member=member, household_id=household_id)


@pytest.fixture
def member_id_amanda(household_id, member_repo):
    """Miembro Amanda creada en BD."""
    member = Member("Amanda")
    member.add_incomes(146700)
    return member_repo.save(member=member, household_id=household_id)


@pytest.fixture
def period_id(household_id, period_repo):
    """Período creado en BD listo para asociar gastos."""
    period = Period(
        household_id=household_id,
        start_date=date(2026, 2, 6),
        status=Phase.PLANNING,
        method=MetodoReparto.EQUAL,
    )
    return period_repo.save(period=period)


@pytest.fixture
def member_ids(member_id_heri, member_id_amanda):
    """Dict {nombre_normalizado: id_bd} con los dos miembros del test."""
    return {"heri": member_id_heri, "amanda": member_id_amanda}


@pytest.fixture
def sample_expense_id(expense_repo, member_ids, period_id) -> int:
    """Gasto compartido (heri + amanda) guardado en BD. Devuelve su id."""
    expense = Expense(
        member="heri",
        amount_cents=34600,
        category=make_category("fijos", is_shared=True),
        participants=["heri", "amanda"],
    )
    return expense_repo.save(expense=expense, member_ids=member_ids, period_id=period_id)


# ===============================================
# TESTS — save
# ===============================================


def test_save_returns_valid_id(expense_repo, member_ids, period_id):
    """save devuelve un entero positivo tras insertar el gasto."""
    expense = Expense(
        member="heri",
        amount_cents=34600,
        category=make_category("fijos", is_shared=True),
        participants=["heri", "amanda"],
    )

    id = expense_repo.save(expense=expense, member_ids=member_ids, period_id=period_id)

    assert isinstance(id, int)
    assert id > 0


# ===============================================
# TESTS — find_by_period
# ===============================================


def test_find_by_period_returns_saved_expense(
    sample_expense_id, expense_repo, period_id, member_id_heri
):
    """find_by_period devuelve el gasto guardado con los datos correctos."""
    expense = expense_repo.find_by_period(period_id=period_id)[0]

    assert expense["category"] == "fijos"
    assert expense["amount_cents"] == 34600
    assert expense["payer_id"] == member_id_heri


# ===============================================
# TESTS — find_with_participants
# ===============================================


def test_find_with_participants_returns_participant_names(
    sample_expense_id, expense_repo, period_id, member_id_heri
):
    """find_with_participants devuelve el gasto con la lista de participantes."""
    expense = expense_repo.find_with_participants(period_id)[0]

    assert len(expense["participants"]) == 2
    assert expense["payer_id"] == member_id_heri
    assert "amanda" in expense["participants"]
