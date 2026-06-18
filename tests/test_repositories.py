from datetime import date, datetime

import pytest
import psycopg2
from src.models.member import Member
from src.models.period import Period
from src.models.constants import Phase
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.debt_repository import DebtRepository
from src.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# ===============================================
# FIXTURES
# ===============================================


@pytest.fixture
def conn():
    """Conexión directa sin commit — rollback automático al finalizar cada test"""
    connection = psycopg2.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, port=DB_PORT
    )
    yield connection
    connection.rollback()
    connection.close()


@pytest.fixture
def household_repo(conn):
    """Repositorio de hogares con conexión de test"""
    return HouseholdRepository(conn)


@pytest.fixture
def member_repo(conn):
    """Repositorio de miembros con conexión de test"""
    return MemberRepository(conn)


@pytest.fixture
def household_id(household_repo):
    """Hogar creado listo para usar en tests de miembros"""
    return household_repo.save()


@pytest.fixture
def member():
    """Miembro base para tests"""
    m = Member("Amanda")
    m.monthly_income = 133958
    return m


@pytest.fixture
def member_2():
    """Miembro base para tests"""
    m = Member("Heri")
    m.monthly_income = 143558
    return m


@pytest.fixture
def member_id(household_id, member, member_repo):
    """Miembro creado en base de datos para test"""
    member_id = member_repo.save(member=member, household_id=household_id)
    return member_id


# ===============================================
# TESTS: HouseholdRepository
# ===============================================


def test_save_returns_correct_id(household_repo):
    """save devuelve un id entero mayor que cero"""
    household_id = household_repo.save()

    assert isinstance(household_id, int)
    assert household_id > 0


def test_del_household_removes_household(household_repo):
    household_id = household_repo.save()
    household_repo.del_household(household_id=household_id)

    assert household_repo.get_household(household_id) is None


def test_list_households_returns_all_households(household_repo):
    household_id = household_repo.save()
    households = household_repo.list_households()
    ids = [household["id"] for household in households]
    assert len(households) >= 1
    assert household_id in ids


def test_get_household_returns_correct_data(household_repo, household_id):
    household = household_repo.get_household(household_id)
    assert household["status"] is True
    assert household["id"] == household_id


# ===============================================
# TESTS: MemberRepository
# ===============================================


def test_save_persist_data(member_repo, household_id, member):
    """save persiste nombre e ingresos correctamente"""
    member_repo.save(member=member, household_id=household_id)
    members = member_repo.list_members(household_id=household_id)
    assert len(members) == 1
    assert members[0]["full_name"] == "amanda"
    assert members[0]["monthly_income"] == 133958


def test_del_member_removes_member_from_db(member_id, member_repo):
    member_repo.del_member(member_id=member_id)
    assert member_repo.get_member_by_id(member_id=member_id) is None


def test_get_member_by_id_returns_correct_data(member_id, member_repo):
    member = member_repo.get_member_by_id(member_id=member_id)

    assert member["full_name"] == "amanda"
    assert member["monthly_income"] == 133958


def test_list_members_returns_all_members_for_household(
    member_repo, household_id, member, member_2
):

    member1_id = member_repo.save(member=member, household_id=household_id)
    member2_id = member_repo.save(member_2, household_id=household_id)
    members = member_repo.list_members(household_id=household_id)

    ids = [member["id"] for member in members]
    assert len(members) == 2
    assert member1_id in ids
    assert member2_id in ids


def test_rename_member_changes_full_name(member_id, member_repo):
    new_name = "Maria Elena"
    member_repo.rename(member_id=member_id, new_name=new_name)

    member = member_repo.get_member_by_id(member_id)
    assert member["full_name"] == "maria elena"


def test_change_incomes_updates_income(member_id, member_repo):
    new_incomes = 178538
    member_repo.change_incomes(member_id=member_id, new_incomes_cents=new_incomes)

    member = member_repo.get_member_by_id(member_id)

    assert member["monthly_income"] == new_incomes


# ===============================================
# FIXTURES: DebtRepository
# ===============================================


@pytest.fixture
def period_repo(conn):
    """Repositorio de períodos con conexión de test"""
    return PeriodRepository(conn)


@pytest.fixture
def period_id(period_repo, household_id):
    """Período creado en BD, listo para colgar pagos de deuda"""
    period = Period(
        household_id=household_id,
        start_date=date(2026, 1, 6),
        status=Phase.PLANNING,
    )
    return period_repo.save(period)


@pytest.fixture
def debt_repo(conn):
    """Repositorio de deuda con conexión de test"""
    return DebtRepository(conn)


# ===============================================
# TESTS: DebtRepository
# ===============================================


def test_debt_save_returns_correct_id(debt_repo, period_id, member_id):
    """save devuelve un id entero mayor que cero"""
    entry_id = debt_repo.save(
        period_id=period_id,
        member_id=member_id,
        amount_cents=20000,
        payment_date=datetime.now(),
    )

    assert isinstance(entry_id, int)
    assert entry_id > 0


def test_debt_find_by_period_returns_saved_payment(debt_repo, period_id, member_id):
    """find_by_period devuelve el pago guardado con sus datos"""
    debt_repo.save(
        period_id=period_id,
        member_id=member_id,
        amount_cents=20000,
        payment_date=datetime.now(),
        description="pago enero",
    )

    entries = debt_repo.find_by_period(period_id)

    assert len(entries) == 1
    assert entries[0]["member_id"] == member_id
    assert entries[0]["amount_cents"] == 20000
    assert entries[0]["description"] == "pago enero"
