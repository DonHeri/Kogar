from datetime import date, datetime

import pytest
import psycopg2

from src.models.member import Member
from src.models.period import Period
from src.models.constants import Phase, SavingScope
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.saving_entry_repository import SavingEntryRepository
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
def saving_repo(conn):
    """Repositorio de saving_entries con conexión de test."""
    return SavingEntryRepository(conn)


@pytest.fixture
def household_id(household_repo):
    """Hogar creado en BD listo para usar en tests."""
    return household_repo.save()


@pytest.fixture
def member_id(household_id, member_repo):
    """Miembro creado en BD listo para asociar movimientos de ahorro."""
    member = Member("Amanda")
    member.add_incomes(133958)
    return member_repo.save(member=member, household_id=household_id)


@pytest.fixture
def period_id(household_id, period_repo):
    """Período creado en BD listo para asociar movimientos de ahorro."""
    period = Period(
        household_id=household_id,
        start_date=date(2026, 1, 6),
        status=Phase.PLANNING,
    )
    return period_repo.save(period)


# ===============================================
# TESTS — save
# ===============================================


def test_save_returns_valid_id(saving_repo, period_id, member_id):
    """save devuelve un id entero positivo tras insertar el movimiento."""
    entry_id = saving_repo.save(
        period_id=period_id,
        member_id=member_id,
        amount_cents=15000,
        scope=SavingScope.SHARED,
        saving_date=datetime.now(),
    )

    assert isinstance(entry_id, int)
    assert entry_id > 0


def test_save_persists_negative_amount_for_withdrawal(saving_repo, period_id, member_id):
    """save persiste el monto negativo tal cual se le pasa (el signo lo decide el caller)."""
    saving_repo.save(
        period_id=period_id,
        member_id=member_id,
        amount_cents=-5000,
        scope=SavingScope.PERSONAL,
        saving_date=datetime.now(),
    )

    entries = saving_repo.find_by_period(period_id)

    assert entries[0]["amount_cents"] == -5000


# ===============================================
# TESTS — find_by_period
# ===============================================


def test_find_by_period_returns_saved_entry(saving_repo, period_id, member_id):
    """find_by_period devuelve el movimiento guardado con los datos correctos."""
    saving_repo.save(
        period_id=period_id,
        member_id=member_id,
        amount_cents=15000,
        scope=SavingScope.PERSONAL,
        description="ahorro mensual",
        saving_date=datetime.now(),
    )

    entries = saving_repo.find_by_period(period_id)

    assert len(entries) == 1
    assert entries[0]["member_id"] == member_id
    assert entries[0]["amount_cents"] == 15000
    assert entries[0]["scope"] == "personal"
    assert entries[0]["description"] == "ahorro mensual"


def test_find_by_period_serializes_scope_value(saving_repo, period_id, member_id):
    """find_by_period devuelve scope como el string plano guardado en BD (.value del enum)."""
    saving_repo.save(
        period_id=period_id,
        member_id=member_id,
        amount_cents=20000,
        scope=SavingScope.SHARED,
        saving_date=datetime.now(),
    )

    entries = saving_repo.find_by_period(period_id)

    assert entries[0]["scope"] == "shared"
