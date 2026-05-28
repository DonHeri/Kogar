import pytest
import psycopg2

from src.models.budget import Budget
from src.models.debt_tracker import DebtTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.saving_tracker import SavingTracker
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
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
def wm_with_repos(member_repo, household_repo):
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
    )

    return wm


@pytest.fixture
def wm_ready_to_finish(wm_with_repos):
    # Arrange
    wm_with_repos.register_member("Heri")
    wm_with_repos.register_member("amanda")
    wm_with_repos.set_member_incomes(name="heri", amount_eur=1652)
    wm_with_repos.set_member_incomes(name="amanda", amount_eur=1456)

    return wm_with_repos


# ===============================================
# TESTS
# ===============================================


def test_finish_registration_add_household(wm_ready_to_finish):
    # Act
    household_id = wm_ready_to_finish.finish_registration(year=2026, month=1)
    # Assert
    ids = [
        h["id"]
        for h in wm_ready_to_finish.household_repo.list_households()
    ]

    assert household_id in ids


def test_finish_registration_add_members(wm_ready_to_finish):

    # Act
    household_id = wm_ready_to_finish.finish_registration(year=2026, month=1)

    member_names = [
        m["full_name"]
        for m in wm_ready_to_finish.member_repo.list_members(
            household_id
        )
    ]

    # Assert
    assert "amanda" in member_names
    assert "heri" in member_names


def test_finish_registration_add_incomes(wm_ready_to_finish):

    # Act
    household_id = wm_ready_to_finish.finish_registration(year=2026, month=1)

    incomes = [
        i["monthly_income"]
        for i in wm_ready_to_finish.member_repo.list_members(
            household_id
        )
    ]

    # Assert
    assert 165200 in incomes
    assert 145600 in incomes
