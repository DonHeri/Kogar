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
from src.workflow.household_loader import HouseholdLoader
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
def budget_categories_repo(conn):
    """Repositorio de presupuestos con conexión de test."""
    return BudgetCategoryRepository(conn)


@pytest.fixture
def household_loader(
    household_repo, member_repo, period_repo, expense_repo, budget_categories_repo
):
    """Loader bajo prueba, con repos reales apuntando a la conexión de test."""
    return HouseholdLoader(
        budget_categories_repo=budget_categories_repo,
        expense_repository=expense_repo,
        household_repo=household_repo,
        member_repo=member_repo,
        period_repo=period_repo,
    )


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
def member_ids(member_id_heri, member_id_amanda):
    """Dict {nombre_normalizado: id_bd} con los dos miembros del test."""
    return {"heri": member_id_heri, "amanda": member_id_amanda}


@pytest.fixture
def period_id(household_id, period_repo, member_ids):
    """Período en fase MONTH, listo para rehidratar."""
    period = Period(
        household_id=household_id,
        start_date=date(2026, 2, 6),
        status=Phase.MONTH,
        method=MetodoReparto.PROPORTIONAL,
    )
    return period_repo.save(period=period)


@pytest.fixture
def budget_categories(period_id, budget_categories_repo):
    """Dos categorías raíz (fijos, variables) + una hija (alquiler bajo fijos)."""
    fijos = BudgetCategory(Category("fijos", is_shared=True), 900.0, parent=None)
    variables = BudgetCategory(Category("variables", is_shared=False), 300.0, parent=None)
    alquiler = BudgetCategory(Category("alquiler", is_shared=True), 600.0, parent="fijos")

    for budget_category in (fijos, variables, alquiler):
        budget_categories_repo.save(
            household_period_id=period_id, budget_category=budget_category
        )

    return {"fijos": fijos, "variables": variables, "alquiler": alquiler}


@pytest.fixture
def sample_expense_id(expense_repo, member_ids, period_id, budget_categories):
    """Gasto compartido en 'fijos' (heri paga, heri+amanda participan), guardado en BD."""
    expense = Expense(
        member="heri",
        amount_cents=34600,
        category=make_category("fijos", is_shared=True),
        participants=["heri", "amanda"],
    )
    return expense_repo.save(expense=expense, member_ids=member_ids, period_id=period_id)


# ===============================================
# TESTS — load_base
# ===============================================


def test_load_base_returns_member_ids_mapping(
    household_loader, household_id, period_id, member_ids
):
    """member_ids devuelto mapea nombre normalizado -> id de BD."""
    _, returned_member_ids, _ = household_loader.load_base(
        household_id=household_id, period_id=period_id
    )

    assert returned_member_ids == member_ids


def test_load_base_rehydrates_members_with_income(
    household_loader, household_id, period_id
):
    """Los miembros rehidratados conservan su ingreso mensual en céntimos."""
    household, _, _ = household_loader.load_base(
        household_id=household_id, period_id=period_id
    )

    assert household.members["heri"].monthly_income == 135400
    assert household.members["amanda"].monthly_income == 146700


def test_load_base_returns_phase_from_period_status(
    household_loader, household_id, period_id
):
    """La fase devuelta viene del status persistido del período."""
    _, _, phase = household_loader.load_base(
        household_id=household_id, period_id=period_id
    )

    assert phase == Phase.MONTH


def test_load_base_rehydrates_budget_categories_with_planned_amounts(
    household_loader, household_id, period_id, budget_categories
):
    """Cada BudgetCategory persistida se reconstruye con su planned_amount."""
    household, _, _ = household_loader.load_base(
        household_id=household_id, period_id=period_id
    )

    assert household.budget.get_planned_amount("fijos") == 90000
    assert household.budget.get_planned_amount("variables") == 30000
    assert household.budget.get_planned_amount("alquiler") == 60000


def test_load_base_rehydrates_parent_before_child_regardless_of_insertion_order(
    household_loader, household_id, period_id, budget_categories_repo
):
    """Regresión: si la hija se persiste antes que la madre, load_base no debe
    romper con 'La categoría debe estar creada'. El orden de hidratación no
    puede depender del orden físico de inserción en BD."""
    child = BudgetCategory(Category("alquiler", is_shared=True), 600.0, parent="fijos")
    parent = BudgetCategory(Category("fijos", is_shared=True), 900.0, parent=None)

    # Se guarda la hija ANTES que la madre a propósito
    budget_categories_repo.save(household_period_id=period_id, budget_category=child)
    budget_categories_repo.save(household_period_id=period_id, budget_category=parent)

    household, _, _ = household_loader.load_base(
        household_id=household_id, period_id=period_id
    )

    assert household.budget.get_planned_amount("fijos") == 90000
    assert household.budget.get_planned_amount("alquiler") == 60000


def test_load_base_does_not_hydrate_expenses(
    household_loader, household_id, period_id, sample_expense_id
):
    """load_base es la receta ligera: no reconstruye histórico de gastos aunque exista en BD."""
    household, _, _ = household_loader.load_base(
        household_id=household_id, period_id=period_id
    )

    assert household.get_total_spent() == 0


# ===============================================
# TESTS — load_for_queries
# ===============================================


def test_load_for_queries_keeps_member_ids_and_phase(
    household_loader, household_id, period_id, member_ids
):
    """load_for_queries no rompe el contrato de load_base (member_ids, phase)."""
    _, returned_member_ids, phase = household_loader.load_for_queries(
        household_id=household_id, period_id=period_id
    )

    assert returned_member_ids == member_ids
    assert phase == Phase.MONTH


def test_load_for_queries_resolves_payer_by_id(
    household_loader, household_id, period_id, sample_expense_id
):
    """El gasto rehidratado atribuye correctamente el pagador (payer_id -> nombre)."""
    household, _, _ = household_loader.load_for_queries(
        household_id=household_id, period_id=period_id
    )

    assert household.get_member_paid_total("heri") == 34600
    assert household.get_member_paid_total("amanda") == 0


def test_load_for_queries_rehydrates_participants(
    household_loader, household_id, period_id, sample_expense_id
):
    """Los participantes del gasto se reconstruyen completos."""
    household, _, _ = household_loader.load_for_queries(
        household_id=household_id, period_id=period_id
    )

    expense = household.expense_tracker.get_all_expenses()[0]
    assert set(expense.participants) == {"heri", "amanda"}


def test_load_for_queries_resolves_category_object(
    household_loader, household_id, period_id, sample_expense_id
):
    """La categoría del gasto se resuelve contra el budget ya hidratado."""
    household, _, _ = household_loader.load_for_queries(
        household_id=household_id, period_id=period_id
    )

    assert household.get_category_spent("fijos") == 34600


def test_load_for_queries_with_no_expenses_returns_empty_tracker(
    household_loader, household_id, period_id
):
    """Sin gastos en BD, load_for_queries no rompe y el tracker queda vacío."""
    household, _, _ = household_loader.load_for_queries(
        household_id=household_id, period_id=period_id
    )

    assert household.get_total_spent() == 0
