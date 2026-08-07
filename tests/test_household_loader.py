from uuid import UUID
from datetime import date

import pytest
import psycopg2

from tests.helpers import make_category
from src.models.budget_category import BudgetCategory
from src.models.category import Category
from src.models.constants import Phase, MetodoReparto
from src.models.expense import Expense
from src.models.member import Member
from src.models.period import Period
from src.storage.budget_categories_repository import BudgetCategoryRepository
from src.storage.expense_repository import ExpenseRepository
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.debt_bucket_repository import DebtBucketRepository
from src.storage.debt_entry_repository import DebtEntryRepository
from src.storage.saving_bucket_repository import SavingBucketRepository
from src.storage.saving_bucket_entry_repository import SavingBucketEntryRepository
from src.workflow.household_loader import HouseholdLoader
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
def expense_repo(conn: psycopg2.extensions.connection) -> ExpenseRepository:
    """Repositorio de gastos con conexión de test."""
    return ExpenseRepository(conn)


@pytest.fixture
def budget_categories_repo(
    conn: psycopg2.extensions.connection,
) -> BudgetCategoryRepository:
    """Repositorio de presupuestos con conexión de test."""
    return BudgetCategoryRepository(conn)


@pytest.fixture
def debt_bucket_repo(conn: psycopg2.extensions.connection) -> DebtBucketRepository:
    """Repositorio de debt_buckets con conexión de test."""
    return DebtBucketRepository(conn)


@pytest.fixture
def debt_entry_repo(conn: psycopg2.extensions.connection) -> DebtEntryRepository:
    """Repositorio de debt_entries con conexión de test."""
    return DebtEntryRepository(conn)


@pytest.fixture
def saving_bucket_repo(conn: psycopg2.extensions.connection) -> SavingBucketRepository:
    """Repositorio de saving_buckets con conexión de test."""
    return SavingBucketRepository(conn)


@pytest.fixture
def saving_bucket_entry_repo(
    conn: psycopg2.extensions.connection,
) -> SavingBucketEntryRepository:
    """Repositorio de bucket_entries con conexión de test."""
    return SavingBucketEntryRepository(conn)


@pytest.fixture
def household_loader(
    household_repo: HouseholdRepository,
    member_repo: MemberRepository,
    period_repo: PeriodRepository,
    expense_repo: ExpenseRepository,
    budget_categories_repo: BudgetCategoryRepository,
    debt_bucket_repo: DebtBucketRepository,
    debt_entry_repo: DebtEntryRepository,
    saving_bucket_repo: SavingBucketRepository,
    saving_bucket_entry_repo: SavingBucketEntryRepository,
) -> HouseholdLoader:
    """Loader bajo prueba, con repos reales apuntando a la conexión de test."""
    return HouseholdLoader(
        budget_categories_repo=budget_categories_repo,
        expense_repository=expense_repo,
        household_repo=household_repo,
        member_repo=member_repo,
        period_repo=period_repo,
        debt_bucket_repository=debt_bucket_repo,
        debt_entry_repository=debt_entry_repo,
        saving_bucket_repository=saving_bucket_repo,
        saving_bucket_entry_repository=saving_bucket_entry_repo,
    )


@pytest.fixture
def household_id(household_repo: HouseholdRepository) -> int:
    """Hogar creado en BD listo para usar en tests."""
    return household_repo.save()


@pytest.fixture
def member_id_heri(household_id: int, member_repo: MemberRepository) -> int:
    """Miembro Heri creado en BD."""
    member = Member("Heri")
    member.add_incomes(135400)
    return member_repo.save(member=member, household_id=household_id)


@pytest.fixture
def member_id_amanda(household_id: int, member_repo: MemberRepository) -> int:
    """Miembro Amanda creada en BD."""
    member = Member("Amanda")
    member.add_incomes(146700)
    return member_repo.save(member=member, household_id=household_id)


@pytest.fixture
def member_ids(member_id_heri: int, member_id_amanda: int) -> dict[str, int]:
    """Dict {nombre_normalizado: id_bd} con los dos miembros del test."""
    return {"heri": member_id_heri, "amanda": member_id_amanda}


@pytest.fixture
def period_id(
    household_id: int, period_repo: PeriodRepository, member_ids: dict[str, int]
) -> int:
    """Período en fase MONTH, listo para rehidratar."""
    period = Period(
        household_id=household_id,
        start_date=date(2026, 2, 6),
        status=Phase.MONTH,
        method=MetodoReparto.PROPORTIONAL,
    )
    return period_repo.save(period=period)


@pytest.fixture
def budget_categories(
    period_id: int, budget_categories_repo: BudgetCategoryRepository
) -> dict[str, BudgetCategory]:
    """Dos categorías raíz (fijos, variables) + una hija (alquiler bajo fijos)."""
    fijos = BudgetCategory(Category("fijos", is_shared=True), 900.0, parent=None)
    variables = BudgetCategory(
        Category("variables", is_shared=False), 300.0, parent=None
    )
    alquiler = BudgetCategory(
        Category("alquiler", is_shared=True), 600.0, parent="fijos"
    )

    for budget_category in (fijos, variables, alquiler):
        budget_categories_repo.save(
            household_period_id=period_id, budget_category=budget_category
        )

    return {"fijos": fijos, "variables": variables, "alquiler": alquiler}


@pytest.fixture
def sample_expense_id(
    expense_repo: ExpenseRepository,
    member_ids: dict[str, int],
    period_id: int,
    budget_categories: dict[str, BudgetCategory],
) -> UUID:
    """Gasto compartido en 'fijos' (heri paga, heri+amanda participan), guardado en BD."""
    expense = Expense(
        member="heri",
        amount_cents=34600,
        category=make_category("fijos", is_shared=True),
        participants=["heri", "amanda"],
    )
    return expense_repo.save(
        expense=expense, member_ids=member_ids, period_id=period_id
    )


# ===============================================
# TESTS — load_base
# ===============================================


def test_load_base_returns_member_ids_mapping(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """member_ids devuelto mapea nombre normalizado -> id de BD."""
    _, returned_member_ids, _ = household_loader.load_base(
        period_id=period_id
    )

    assert returned_member_ids == member_ids


def test_load_base_rehydrates_members_with_income(
    household_loader: HouseholdLoader, household_id: int, period_id: int
) -> None:
    """Los miembros rehidratados conservan su ingreso mensual en céntimos."""
    household, _, _ = household_loader.load_base(
        period_id=period_id
    )

    assert household.members["heri"].monthly_income == 135400
    assert household.members["amanda"].monthly_income == 146700


def test_load_base_returns_the_period_with_its_status_and_dates(
    household_loader: HouseholdLoader, household_id: int, period_id: int
) -> None:
    """El loader devuelve el Period entero: quien orquesta necesita la fase para
    validar y el rango de fechas para las consultas de deuda."""
    _, _, period = household_loader.load_base(
        period_id=period_id
    )

    assert period.status == Phase.MONTH
    assert period.start_date == date(2026, 2, 6)
    assert period.household_id == household_id


def test_load_base_rehydrates_budget_categories_with_planned_amounts(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    budget_categories: dict[str, BudgetCategory],
) -> None:
    """Cada BudgetCategory persistida se reconstruye con su planned_amount."""
    household, _, _ = household_loader.load_base(
        period_id=period_id
    )

    assert household.budget.get_planned_amount("fijos") == 90000
    assert household.budget.get_planned_amount("variables") == 30000
    assert household.budget.get_planned_amount("alquiler") == 60000


def test_load_base_rehydrates_parent_before_child_regardless_of_insertion_order(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    budget_categories_repo: BudgetCategoryRepository,
) -> None:
    """Regresión: si la hija se persiste antes que la madre, load_base no debe
    romper con 'La categoría debe estar creada'. El orden de hidratación no
    puede depender del orden físico de inserción en BD."""
    child = BudgetCategory(Category("alquiler", is_shared=True), 600.0, parent="fijos")
    parent = BudgetCategory(Category("fijos", is_shared=True), 900.0, parent=None)

    # Se guarda la hija ANTES que la madre a propósito
    budget_categories_repo.save(household_period_id=period_id, budget_category=child)
    budget_categories_repo.save(household_period_id=period_id, budget_category=parent)

    household, _, _ = household_loader.load_base(
        period_id=period_id
    )

    assert household.budget.get_planned_amount("fijos") == 90000
    assert household.budget.get_planned_amount("alquiler") == 60000


def test_load_base_does_not_hydrate_expenses(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """load_base es la receta ligera: no reconstruye histórico de gastos aunque exista en BD."""
    household, _, _ = household_loader.load_base(
        period_id=period_id
    )

    assert household.get_total_spent() == 0


def test_load_base_rehydrates_custom_splits_in_basis_points(
    household_loader: HouseholdLoader,
    period_repo: PeriodRepository,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """Los splits vuelven de BD en basis points y entran tal cual.

    La conversión desde 0-100 vive en los servicios, no en Household, así que la
    BD y el usuario entran por la misma puerta. Cuando el dominio convertía, 5299
    volvía como 529900 sin que nada lanzara.
    """
    period_repo.update_method(method=MetodoReparto.CUSTOM, period_id=period_id)
    period_repo.save_percentages(
        period_id=period_id, percentages={"heri": 5299, "amanda": 4701}
    )

    household, _, _ = household_loader.load_base(period_id=period_id)

    assert household.get_custom_splits() == {"heri": 5299, "amanda": 4701}


def test_load_base_leaves_splits_empty_when_the_period_has_none(
    household_loader: HouseholdLoader,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """Un período PROPORTIONAL no guarda splits, y cargarlo no puede exigirlos."""
    household, _, _ = household_loader.load_base(period_id=period_id)

    assert household.get_custom_splits() == {}


def test_load_base_ignores_percentages_when_the_method_is_not_custom(
    household_loader: HouseholdLoader,
    period_repo: PeriodRepository,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """Los porcentajes de un período PROPORTIONAL son su acuerdo, no una decisión.

    period_percentages guarda las dos cosas. Cargarlas como _custom_splits en un
    período que no es CUSTOM inventaría un reparto propio que nadie definió.
    """
    period_repo.save_percentages(
        period_id=period_id, percentages={"heri": 4800, "amanda": 5200}
    )

    household, _, _ = household_loader.load_base(period_id=period_id)

    assert household.get_custom_splits() == {}


def test_load_base_rehydrates_the_frozen_agreement(
    household_loader: HouseholdLoader,
    period_repo: PeriodRepository,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """El acuerdo congelado sobrevive a la recarga, desglosado por categoría."""
    period_repo.save_agreed_contributions(
        period_id=period_id,
        contributions={
            "fijos": {"heri": 30000, "amanda": 20000},
            "reserva": {"heri": 10000, "amanda": 5000},
        },
    )
    period_repo.save_percentages(
        period_id=period_id, percentages={"heri": 6000, "amanda": 4000}
    )

    household, _, _ = household_loader.load_base(period_id=period_id)

    assert household.get_agreed_contributions() == {
        "fijos": {"heri": 30000, "amanda": 20000},
        "reserva": {"heri": 10000, "amanda": 5000},
    }
    assert household.get_agreed_percentages() == {"heri": 6000, "amanda": 4000}
    assert household.get_member_owed_total("heri") == 40000


def test_load_base_leaves_the_agreement_empty_while_planning(
    household_loader: HouseholdLoader,
    period_repo: PeriodRepository,
    household_id: int,
    member_ids: dict[str, int],
) -> None:
    """Un período en PLANNING no ha congelado nada, y cargarlo no puede fingirlo."""
    planning_period = Period(
        household_id=household_id,
        start_date=date(2026, 3, 6),
        status=Phase.PLANNING,
        method=MetodoReparto.PROPORTIONAL,
    )
    planning_id = period_repo.save(period=planning_period)

    household, _, _ = household_loader.load_base(period_id=planning_id)

    with pytest.raises(ValueError, match="no han sido congeladas"):
        household.get_agreed_contributions()


# ===============================================
# TESTS — load_for_queries
# ===============================================


def test_load_for_queries_keeps_member_ids_and_phase(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """load_for_queries no rompe el contrato de load_base (member_ids, period)."""
    _, returned_member_ids, period = household_loader.load_for_queries(
        period_id=period_id
    )

    assert returned_member_ids == member_ids
    assert period.status == Phase.MONTH


def test_load_for_queries_resolves_payer_by_id(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """El gasto rehidratado atribuye correctamente el pagador (payer_id -> nombre)."""
    household, _, _ = household_loader.load_for_queries(
        period_id=period_id
    )

    assert household.get_member_paid_total("heri") == 34600
    assert household.get_member_paid_total("amanda") == 0


def test_load_for_queries_rehydrates_participants(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """Los participantes del gasto se reconstruyen completos."""
    household, _, _ = household_loader.load_for_queries(
        period_id=period_id
    )

    expense = household.expense_tracker.get_all_expenses()[0]
    assert set(expense.participants) == {"heri", "amanda"}


def test_load_for_queries_rehydrates_weights(
    expense_repo: ExpenseRepository,
    household_loader: HouseholdLoader,
    member_ids: dict[str, int],
    period_id: int,
    budget_categories: dict[str, BudgetCategory],
) -> None:
    """Los pesos sobreviven al viaje de ida y vuelta a BD.

    Sin esto, un gasto repartido 70/30 volvería como 50/50 al recargar y el
    settlement daría un número distinto según si el hogar estaba en memoria o
    se acababa de cargar.
    """
    expense_repo.save(
        expense=Expense(
            member="heri",
            amount_cents=10000,
            category=make_category("fijos", is_shared=True),
            participants=["heri", "amanda"],
            weights={"heri": 7000, "amanda": 3000},
        ),
        member_ids=member_ids,
        period_id=period_id,
    )

    household, _, _ = household_loader.load_household(period_id, load=Load.FOR_QUERIES)

    expense = household.expense_tracker.get_all_expenses()[0]
    assert expense.weights == {"heri": 7000, "amanda": 3000}


def test_load_for_queries_resolves_category_object(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """La categoría del gasto se resuelve contra el budget ya hidratado."""
    household, _, _ = household_loader.load_for_queries(
        period_id=period_id
    )

    assert household.get_category_spent("fijos") == 34600


def test_load_for_queries_preserves_the_expense_id(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """El gasto rehidratado conserva su id, no recibe uno nuevo."""
    household, _, _ = household_loader.load_for_queries(
        period_id=period_id
    )

    expense = household.expense_tracker.get_all_expenses()[0]
    assert expense.id == sample_expense_id


def test_load_for_queries_with_no_expenses_returns_empty_tracker(
    household_loader: HouseholdLoader, household_id: int, period_id: int
) -> None:
    """Sin gastos en BD, load_for_queries no rompe y el tracker queda vacío."""
    household, _, _ = household_loader.load_for_queries(
        period_id=period_id
    )

    assert household.get_total_spent() == 0
