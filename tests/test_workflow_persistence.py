import pytest
import psycopg2

from src.models.budget import Budget
from src.models.constants import Phase
from src.models.constants import MetodoReparto
from src.models.debt_tracker import DebtTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.period import Period
from src.models.saving_tracker import SavingTracker
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.workflow.workflow_manager import WorkflowManager
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
def period_repo(conn):
    """Repositorio de períodos con conexión de test"""
    return PeriodRepository(conn)


@pytest.fixture
def wm_with_repos(member_repo, household_repo, period_repo):
    """WorkflowManager vacío con los tres repositorios inyectados"""
    household = Household(
        budget=Budget(),
        debt_tracker=DebtTracker(),
        expense_tracker=ExpenseTracker(),
        saving_tracker=SavingTracker(),
    )
    wm = WorkflowManager(
        household=household,
        household_repo=household_repo,
        member_repo=member_repo,
        period_repo=period_repo,
    )

    return wm


@pytest.fixture
def wm_pre_registration(wm_with_repos):
    """WM con dos miembros e ingresos registrados, listo para finish_registration"""
    wm_with_repos.register_member("Heri")
    wm_with_repos.register_member("amanda")
    wm_with_repos.set_member_incomes(name="heri", amount_eur=1652)
    wm_with_repos.set_member_incomes(name="amanda", amount_eur=1456)

    return wm_with_repos


@pytest.fixture
def wm_pre_planning(wm_pre_registration):
    """WM en PLANNING con categorías y presupuesto al 100%, listo para finish_planning"""
    wm_pre_registration.finish_registration(year=2026, month=1)
    # Finish registration settea categorías standard
    categories = wm_pre_registration.get_active_categories()
    pcts = [50.0, 30.0, 20.0]
    percentages = {category: pct for category, pct in zip(categories, pcts)}
    wm_pre_registration.set_budget_by_percentages(percentages_floats=percentages)

    return wm_pre_registration


@pytest.fixture
def wm_planning_contributions_saved(wm_pre_planning):
    "WM en PLANNING con contribuciones del período guardadas en BD"
    contributions = wm_pre_planning.get_total_contributions_by_member()
    wm_pre_planning.period_repo.save_agreed_contributions(
        period_id=wm_pre_planning.period_id, contributions=contributions
    )

    return wm_pre_planning


@pytest.fixture
def wm_pre_month(wm_pre_planning):
    """WM en MONTH tras finish_planning, listo para finish_month"""
    wm_pre_planning.finish_planning()

    return wm_pre_planning


# ===============================================
# TESTS — Household y miembros
# ===============================================


def test_finish_registration_persists_household(wm_pre_registration):
    """finish_registration guarda el hogar en BD"""
    household_id = wm_pre_registration.finish_registration(year=2026, month=1)

    ids = [h["id"] for h in wm_pre_registration.household_repo.list_households()]

    assert household_id in ids


def test_finish_registration_persists_members(wm_pre_registration):
    """finish_registration guarda los miembros del hogar en BD"""
    household_id = wm_pre_registration.finish_registration(year=2026, month=1)

    member_names = [
        m["full_name"]
        for m in wm_pre_registration.member_repo.list_members(household_id)
    ]

    assert "amanda" in member_names
    assert "heri" in member_names


def test_finish_registration_persists_incomes(wm_pre_registration):
    """finish_registration guarda los ingresos de cada miembro en BD"""
    household_id = wm_pre_registration.finish_registration(year=2026, month=1)

    incomes = [
        i["monthly_income"]
        for i in wm_pre_registration.member_repo.list_members(household_id)
    ]

    assert 165200 in incomes
    assert 145600 in incomes


# ===============================================
# TESTS — Periodo
# ===============================================


def test_period_status_is_planning_after_registration(wm_pre_registration):
    """finish_registration crea el período con status=PLANNING en BD"""
    household_id = wm_pre_registration.finish_registration(year=2026, month=1)

    status = wm_pre_registration.period_repo.get_current(household_id).status

    assert status == Phase.PLANNING


def test_period_status_is_month_after_planning(wm_pre_planning):
    """finish_planning actualiza el período a status=MONTH en BD"""
    wm_pre_planning.finish_planning()

    status = wm_pre_planning.period_repo.get_by_id(wm_pre_planning.period_id).status

    assert status == Phase.MONTH


def test_period_status_is_closing_after_month(wm_pre_month):
    """finish_month actualiza el período a status=CLOSING en BD"""
    wm_pre_month.finish_month()

    status = wm_pre_month.period_repo.get_by_id(wm_pre_month.period_id).status

    assert status == Phase.CLOSING


def test_period_unique_constraint(wm_pre_registration, period_repo):
    """No pueden existir dos períodos con el mismo (household_id, year, month)"""
    household_id = wm_pre_registration.finish_registration(year=2026, month=1)

    duplicate = Period(
        household_id=household_id,
        year=2026,
        month=1,
        status=Phase.PLANNING,
    )

    with pytest.raises(Exception):
        period_repo.save(duplicate)


def test_get_agreed_contributions_returns_saved_data(wm_planning_contributions_saved):
    "get_agreed_contributions devuelve los datos guardados con save_agreed_contributions"
    period_id = wm_planning_contributions_saved.period_id

    contributions = (
        wm_planning_contributions_saved.period_repo.get_agreed_contributions(
            period_id=period_id
        )
    )

    total = sum(contributions.values())

    assert total == 165200 + 145600


def test_save_agreed_contributions_overwrites_existing(
    wm_planning_contributions_saved,
):
    "save_agreed_contributions sobreescribe importes existentes para el mismo período"
    period_id = wm_planning_contributions_saved.period_id
    old_contributions = (
        wm_planning_contributions_saved.period_repo.get_agreed_contributions(period_id)
    )
    assert sum(old_contributions.values()) == 165200 + 145600

    new_contributions = {
        member: (amount + 20) for member, amount in old_contributions.items()
    }
    wm_planning_contributions_saved.period_repo.save_agreed_contributions(
        period_id, new_contributions
    )
    assert (
        sum(
            amount
            for amount in wm_planning_contributions_saved.period_repo.get_agreed_contributions(
                period_id
            ).values()
        )
        == 165200 + 145600 + 40
    )


# ===============================================
# # TESTS — Distribución
# ===============================================


def test_assign_distribution_method_persists_method(wm_pre_registration):
    """assign_distribution_method persiste method"""
    household_id = wm_pre_registration.finish_registration(year=2026, month=1)
    wm_pre_registration.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    current_period = wm_pre_registration.period_repo.get_current(household_id)

    repo_method = current_period.method

    assert repo_method == MetodoReparto.PROPORTIONAL
