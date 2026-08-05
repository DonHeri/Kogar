from datetime import date

import pytest
import psycopg2

from src.models.budget import Budget
from src.models.constants import Phase
from src.models.constants import MetodoReparto
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.period import Period
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.workflow.workflow_manager import WorkflowManager
from src.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


# ===============================================
# FIXTURES
# ===============================================


@pytest.fixture
def conn() -> psycopg2.extensions.connection:
    """Conexión directa sin commit — rollback automático al finalizar cada test"""
    connection = psycopg2.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, port=DB_PORT
    )
    yield connection
    connection.rollback()
    connection.close()


@pytest.fixture
def household_repo(conn: psycopg2.extensions.connection) -> HouseholdRepository:
    """Repositorio de hogares con conexión de test"""
    return HouseholdRepository(conn)


@pytest.fixture
def member_repo(conn: psycopg2.extensions.connection) -> MemberRepository:
    """Repositorio de miembros con conexión de test"""
    return MemberRepository(conn)


@pytest.fixture
def period_repo(conn: psycopg2.extensions.connection) -> PeriodRepository:
    """Repositorio de períodos con conexión de test"""
    return PeriodRepository(conn)


@pytest.fixture
def wm_with_repos(
    member_repo: MemberRepository,
    household_repo: HouseholdRepository,
    period_repo: PeriodRepository,
) -> WorkflowManager:
    """WorkflowManager vacío con los tres repositorios inyectados"""
    household = Household(
        budget=Budget(),
        debt_bucket_tracker=DebtBucketTracker(),
        expense_tracker=ExpenseTracker(),
        saving_bucket_tracker=SavingBucketTracker(),
    )
    wm = WorkflowManager(
        household=household,
        household_repo=household_repo,
        member_repo=member_repo,
        period_repo=period_repo,
    )

    return wm


@pytest.fixture
def wm_pre_registration(wm_with_repos: WorkflowManager) -> WorkflowManager:
    """WM con período abierto y dos miembros con ingresos"""
    # El período nace aquí, con su fecha de corte
    wm_with_repos.start_new_month(start_date=date(2026, 1, 6))
    wm_with_repos.register_member("Heri")
    wm_with_repos.register_member("amanda")
    wm_with_repos.set_member_incomes(name="heri", amount_euros=1652)
    wm_with_repos.set_member_incomes(name="amanda", amount_euros=1456)

    return wm_with_repos


@pytest.fixture
def wm_pre_planning(wm_pre_registration: WorkflowManager) -> WorkflowManager:
    """WM en PLANNING con categorías y presupuesto al 100%, listo para finish_planning"""
    # Finish registration settea categorías standard
    categories = wm_pre_registration.get_active_categories()
    pcts = [50.0, 30.0, 20.0]
    percentages = {category: pct for category, pct in zip(categories, pcts)}
    wm_pre_registration.set_budget_by_percentages(percentages_floats=percentages)

    return wm_pre_registration


@pytest.fixture
def wm_planning_contributions_saved(
    wm_pre_planning: WorkflowManager,
) -> WorkflowManager:
    "WM en PLANNING con contribuciones del período guardadas en BD"
    contributions = wm_pre_planning.household.get_contributions_by_category()
    wm_pre_planning.period_repo.save_agreed_contributions(
        period_id=wm_pre_planning.period_id, contributions=contributions
    )

    return wm_pre_planning


@pytest.fixture
def wm_pre_month(wm_pre_planning: WorkflowManager) -> WorkflowManager:
    """WM en MONTH tras finish_planning, listo para finish_month"""
    wm_pre_planning.finish_planning()

    return wm_pre_planning


@pytest.fixture
def wm_finish_month(wm_pre_month: WorkflowManager) -> WorkflowManager:
    """WM en CLOSED tras finish_month, listo para start_new_month"""
    wm_pre_month.finish_month()

    return wm_pre_month


# ===============================================
# TESTS — Household y miembros
# ===============================================


def test_opening_period_persists_household(
    wm_pre_registration: WorkflowManager,
) -> None:
    """Abrir el período crea el hogar en BD"""
    household_id = wm_pre_registration.household_id

    ids = [h["id"] for h in wm_pre_registration.household_repo.list_households()]

    assert household_id in ids


def test_opening_period_persists_members(wm_pre_registration: WorkflowManager) -> None:
    """Registrar miembros los guarda en BD"""
    household_id = wm_pre_registration.household_id

    member_names = [
        m["full_name"]
        for m in wm_pre_registration.member_repo.list_members(household_id)
    ]

    assert "amanda" in member_names
    assert "heri" in member_names


def test_opening_period_persists_incomes(wm_pre_registration: WorkflowManager) -> None:
    """Los ingresos de cada miembro se guardan en BD"""
    household_id = wm_pre_registration.household_id

    incomes = [
        i["monthly_income"]
        for i in wm_pre_registration.member_repo.list_members(household_id)
    ]

    assert 165200 in incomes
    assert 145600 in incomes


# ===============================================
# TESTS — Periodo
# ===============================================


def test_period_status_is_planning_on_open(
    wm_pre_registration: WorkflowManager,
) -> None:
    """El período nace con status=PLANNING en BD"""
    household_id = wm_pre_registration.household_id

    status = wm_pre_registration.period_repo.get_current(household_id).status

    assert status == Phase.PLANNING


def test_period_status_is_month_after_planning(
    wm_pre_planning: WorkflowManager,
) -> None:
    """finish_planning actualiza el período a status=MONTH en BD"""
    wm_pre_planning.finish_planning()

    status = wm_pre_planning.period_repo.find_by_id(wm_pre_planning.period_id).status

    assert status == Phase.MONTH


def test_period_status_is_closing_after_month(wm_pre_month: WorkflowManager) -> None:
    """finish_month actualiza el período a status=CLOSING en BD"""
    wm_pre_month.finish_month()

    status = wm_pre_month.period_repo.find_by_id(wm_pre_month.period_id).status

    assert status == Phase.CLOSING


def test_period_unique_constraint(
    wm_pre_registration: WorkflowManager, period_repo: PeriodRepository
) -> None:
    """No pueden existir dos períodos con el mismo (household_id, start_date)"""
    household_id = wm_pre_registration.household_id

    duplicate = Period(
        household_id=household_id,
        start_date=date(2026, 1, 6),
        status=Phase.PLANNING,
    )

    with pytest.raises(Exception):
        period_repo.save(duplicate)


def _total_agreed(agreement: dict[str, dict[str, int]]) -> int:
    """Suma el acuerdo desglosado {categoría: {miembro: céntimos}}."""
    return sum(amount for by_member in agreement.values() for amount in by_member.values())


def test_get_agreed_contributions_returns_saved_data(
    wm_planning_contributions_saved: WorkflowManager,
) -> None:
    "get_agreed_contributions devuelve los datos guardados con save_agreed_contributions"
    period_id = wm_planning_contributions_saved.period_id

    contributions = (
        wm_planning_contributions_saved.period_repo.get_agreed_contributions(
            period_id=period_id
        )
    )

    assert _total_agreed(contributions) == 165200 + 145600


def test_save_agreed_contributions_replaces_the_previous_agreement(
    wm_planning_contributions_saved: WorkflowManager,
) -> None:
    """Volver a guardar reemplaza el acuerdo entero, no lo mezcla con el anterior.

    Se borra antes de insertar: una categoría que sale del plan tiene que salir
    del acuerdo, y un ON CONFLICT solo actualiza lo que vuelve a llegar.
    """
    period_id = wm_planning_contributions_saved.period_id
    repo = wm_planning_contributions_saved.period_repo

    old_contributions = repo.get_agreed_contributions(period_id)
    assert _total_agreed(old_contributions) == 165200 + 145600

    repo.save_agreed_contributions(period_id, {"fijos": {"amanda": 500, "heri": 300}})

    assert repo.get_agreed_contributions(period_id) == {
        "fijos": {"amanda": 500, "heri": 300}
    }


# ===============================================
# # TESTS — Distribución
# ===============================================


def test_assign_distribution_method_persists_method(
    wm_pre_registration: WorkflowManager,
) -> None:
    """assign_distribution_method persiste method"""
    household_id = wm_pre_registration.household_id
    wm_pre_registration.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    current_period = wm_pre_registration.period_repo.get_current(household_id)

    repo_method = current_period.method

    assert repo_method == MetodoReparto.PROPORTIONAL


# ===============================================
# TEST - Flujo comienzo nuevo mes
# ===============================================


def test_start_new_month_permite_avanzar_a_planning(
    wm_finish_month: WorkflowManager,
) -> None:
    wm_finish_month.start_new_month()

    wm_finish_month.set_member_incomes(name="heri", amount_euros=1652)
    wm_finish_month.set_member_incomes(name="amanda", amount_euros=1456)

    household_id = wm_finish_month.household_id

    assert (
        wm_finish_month.period_repo.get_current(household_id).status == Phase.PLANNING
    )
