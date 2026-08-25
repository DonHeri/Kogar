from datetime import datetime

import pytest
import psycopg2
import psycopg2.extras

from src.models.member import Member
from src.models.saving_bucket import SavingBucket

from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.saving_buckets_repository import SavingBucketRepository
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
def bucket_repo(conn):
    """Repositorio de saving_buckets con conexión de test."""
    return SavingBucketRepository(conn)


@pytest.fixture
def household_id(household_repo):
    """Hogar creado en BD listo para usar en tests."""
    return household_repo.save()


@pytest.fixture
def member_ids(household_id, member_repo):
    """Dict {nombre_normalizado: id_bd} con dos miembros creados en BD."""
    heri = Member("Heri")
    heri.add_incomes(135400)
    amanda = Member("Amanda")
    amanda.add_incomes(146700)

    return {
        "heri": member_repo.save(member=heri, household_id=household_id),
        "amanda": member_repo.save(member=amanda, household_id=household_id),
    }


@pytest.fixture
def shared_bucket():
    """Bucket compartido con dos owners, sin persistir."""
    return SavingBucket(
        saving_bucket_name="vacaciones",
        goal_cents=500000,
        scope=SavingScope.SHARED,
        owners=["heri", "amanda"],
        description="viaje de verano",
    )


# ===============================================
# TESTS — save
# ===============================================


def test_save_returns_bucket_own_uuid(
    bucket_repo, shared_bucket, household_id, member_ids
):
    """save devuelve el mismo UUID que ya trae el bucket de dominio (PK directa, sin id serial)."""
    bucket_id = bucket_repo.save(
        saving_bucket=shared_bucket, household_id=household_id, member_ids=member_ids
    )

    assert bucket_id == shared_bucket.id


def test_save_persists_bucket_fields(
    bucket_repo, shared_bucket, household_id, member_ids, conn
):
    """save inserta correctamente los datos del bucket en saving_buckets."""
    bucket_id = bucket_repo.save(
        saving_bucket=shared_bucket, household_id=household_id, member_ids=member_ids
    )

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM saving_buckets WHERE id = %s", (bucket_id,))
    row = cursor.fetchone()

    assert row["household_id"] == household_id
    assert row["bucket_name"] == "vacaciones"
    assert row["goal_cents"] == 500000
    assert row["scope"] == "shared"
    assert row["description"] == "viaje de verano"


def test_save_persists_all_owners(
    bucket_repo, shared_bucket, household_id, member_ids, conn
):
    """save inserta una fila en bucket_owners por cada owner del bucket."""
    bucket_id = bucket_repo.save(
        saving_bucket=shared_bucket, household_id=household_id, member_ids=member_ids
    )

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(
        "SELECT member_id FROM bucket_owners WHERE bucket_id = %s", (bucket_id,)
    )
    owner_ids = {row["member_id"] for row in cursor.fetchall()}

    assert owner_ids == {member_ids["heri"], member_ids["amanda"]}


def test_save_without_deadline_persists_null(
    bucket_repo, household_id, member_ids, conn
):
    """save persiste NULL en deadline cuando el bucket no tiene fecha límite."""
    bucket = SavingBucket(
        saving_bucket_name="colchón",
        goal_cents=100000,
        scope=SavingScope.PERSONAL,
        owners=["heri"],
    )

    bucket_id = bucket_repo.save(
        saving_bucket=bucket, household_id=household_id, member_ids=member_ids
    )

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT deadline FROM saving_buckets WHERE id = %s", (bucket_id,))
    row = cursor.fetchone()

    assert row["deadline"] is None
