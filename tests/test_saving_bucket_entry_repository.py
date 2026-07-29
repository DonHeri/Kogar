from datetime import date, datetime
from uuid import UUID

import pytest
import psycopg2

from src.models.member import Member
from src.models.period import Period
from src.models.saving_bucket import SavingBucket
from src.models.constants import Phase
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.saving_bucket_repository import SavingBucketRepository
from src.storage.saving_bucket_entry_repository import SavingBucketEntryRepository
from src.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


# ===============================================
# FIXTURES
# ===============================================


@pytest.fixture
def conn() -> psycopg2.extensions.connection:
    """Conexión directa sin commit — rollback automático al finalizar cada test."""
    connection = psycopg2.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, port=DB_PORT
    )
    yield connection
    connection.rollback()
    connection.close()


@pytest.fixture
def household_repo(conn: psycopg2.extensions.connection) -> HouseholdRepository:
    """Repositorio de hogares con conexión de test."""
    return HouseholdRepository(conn)


@pytest.fixture
def member_repo(conn: psycopg2.extensions.connection) -> MemberRepository:
    """Repositorio de miembros con conexión de test."""
    return MemberRepository(conn)


@pytest.fixture
def period_repo(conn: psycopg2.extensions.connection) -> PeriodRepository:
    """Repositorio de períodos con conexión de test."""
    return PeriodRepository(conn)


@pytest.fixture
def bucket_repo(conn: psycopg2.extensions.connection) -> SavingBucketRepository:
    """Repositorio de saving_buckets con conexión de test."""
    return SavingBucketRepository(conn)


@pytest.fixture
def bucket_entry_repo(
    conn: psycopg2.extensions.connection,
) -> SavingBucketEntryRepository:
    """Repositorio de bucket_entries con conexión de test."""
    return SavingBucketEntryRepository(conn)


@pytest.fixture
def household_id(household_repo: HouseholdRepository) -> int:
    """Hogar creado en BD listo para usar en tests."""
    return household_repo.save()


@pytest.fixture
def member_id(household_id: int, member_repo: MemberRepository) -> int:
    """Miembro creado en BD, único owner del bucket personal."""
    member = Member("Heri")
    member.add_incomes(135400)
    return member_repo.save(member=member, household_id=household_id)


@pytest.fixture
def period_id(household_id: int, period_repo: PeriodRepository) -> int:
    """Período creado en BD listo para asociar movimientos del bucket."""
    period = Period(
        household_id=household_id,
        start_date=date(2026, 1, 6),
        status=Phase.PLANNING,
    )
    return period_repo.save(period)


@pytest.fixture
def bucket_id(
    bucket_repo: SavingBucketRepository, household_id: int, member_id: int
) -> UUID:
    """Bucket personal persistido, listo para colgar movimientos."""
    bucket = SavingBucket(
        saving_bucket_name="colchón",
        goal_cents=100000,
        owners=["heri"],
    )
    return bucket_repo.save(
        saving_bucket=bucket, household_id=household_id, member_ids={"heri": member_id}
    )


# ===============================================
# TESTS — save
# ===============================================


def test_save_returns_valid_id(
    bucket_entry_repo: SavingBucketEntryRepository,
    bucket_id: UUID,
    period_id: int,
    member_id: int,
) -> None:
    """save devuelve un id entero positivo tras insertar el movimiento."""
    entry_id = bucket_entry_repo.save(
        bucket_id=bucket_id,
        period_id=period_id,
        member_id=member_id,
        amount_cents=15000,
        entry_date=datetime.now(),
    )

    assert isinstance(entry_id, int)
    assert entry_id > 0


def test_save_persists_negative_amount_for_withdrawal(
    bucket_entry_repo: SavingBucketEntryRepository,
    bucket_id: UUID,
    period_id: int,
    member_id: int,
) -> None:
    """save persiste el monto negativo tal cual se le pasa (el signo lo decide el caller)."""
    bucket_entry_repo.save(
        bucket_id=bucket_id,
        period_id=period_id,
        member_id=member_id,
        amount_cents=-5000,
        entry_date=datetime.now(),
    )

    entries = bucket_entry_repo.find_by_period(period_id)

    assert entries[0]["amount_cents"] == -5000


# ===============================================
# TESTS — find_by_period
# ===============================================


def test_find_by_period_returns_saved_entry(
    bucket_entry_repo: SavingBucketEntryRepository,
    bucket_id: UUID,
    period_id: int,
    member_id: int,
) -> None:
    """find_by_period devuelve el movimiento guardado con los datos correctos."""
    bucket_entry_repo.save(
        bucket_id=bucket_id,
        period_id=period_id,
        member_id=member_id,
        amount_cents=15000,
        entry_date=datetime.now(),
    )

    entries = bucket_entry_repo.find_by_period(period_id)

    assert len(entries) == 1
    assert entries[0]["bucket_id"] == bucket_id
    assert entries[0]["member_id"] == member_id
    assert entries[0]["amount_cents"] == 15000
