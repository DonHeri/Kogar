from datetime import datetime

import pytest
import psycopg2
import psycopg2.extras

from src.models.member import Member
from src.models.debt_bucket import DebtBucket

from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.debt_bucket_repository import DebtBucketRepository
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
def household_id(household_repo: HouseholdRepository) -> int:
    """Hogar creado en BD listo para usar en tests."""
    return household_repo.save()


@pytest.fixture
def member_repo(conn: psycopg2.extensions.connection) -> MemberRepository:
    """Repositorio de miembros con conexión de test."""
    return MemberRepository(conn)


@pytest.fixture
def member_ids(household_id: int, member_repo: MemberRepository) -> dict[str, int]:
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
def debt_bucket_repo(conn: psycopg2.extensions.connection) -> DebtBucketRepository:
    """Repositorio de saving_buckets con conexión de test."""
    return DebtBucketRepository(conn)


@pytest.fixture
def debt_bucket() -> DebtBucket:

    return DebtBucket(
        debt_bucket_name="financiacion moto",
        principal_cents=350000,
        owner="heri",
        installment_cents=13080,
        description="Financiación moto HONDA PCX 125",
    )


# ===============================================
# TESTS — save
# ===============================================


def test_save_returns_bucket_own_uuid(
    debt_bucket_repo: DebtBucketRepository,
    debt_bucket: DebtBucket,
    household_id: int,
    member_ids: dict[str, int],
) -> None:
    """save devuelve el mismo UUID que ya trae el bucket de dominio (PK directa, sin id serial)."""
    bucket_id = debt_bucket_repo.save(
        debt_bucket=debt_bucket, household_id=household_id, members_ids=member_ids
    )

    assert bucket_id == debt_bucket.id


def test_save_persists_bucket_fields(
    debt_bucket_repo: DebtBucketRepository,
    debt_bucket: DebtBucket,
    household_id: int,
    member_ids: dict[str, int],
    conn: psycopg2.extensions.connection,
) -> None:
    """save inserta correctamente los datos del bucket en saving_buckets."""
    bucket_id = debt_bucket_repo.save(
        debt_bucket=debt_bucket, household_id=household_id, members_ids=member_ids
    )

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM debt_buckets WHERE id = %s", (bucket_id,))
    row = cursor.fetchone()

    assert row["household_id"] == household_id
    assert row["bucket_name"] == "financiacion moto"
    assert row["principal_cents"] == 350000
    assert row["member_id"] == member_ids[debt_bucket.owner]
    assert row["installment_cents"] == 13080
    assert row["description"] == "Financiación moto HONDA PCX 125"


def test_find_by_household_return_bucket(
    debt_bucket_repo: DebtBucketRepository,
    debt_bucket: DebtBucket,
    household_id: int,
    member_ids: dict[str, int],
):
    debt_bucket_repo.save(
        debt_bucket=debt_bucket, household_id=household_id, members_ids=member_ids
    )

    bucket = debt_bucket_repo.find_by_household(household_id=household_id)

    assert bucket[0]["id"] == debt_bucket.id
    assert bucket[0]["principal_cents"] == debt_bucket.principal_cents
    assert bucket[0]["installment_cents"] == debt_bucket.installment_cents
    assert bucket[0]["description"] == debt_bucket.description
