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
from src.workflow.expense_service import ExpenseService
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
def expense_repo(conn):
    """Repositorio de gastos con conexión de test"""
    return ExpenseRepository(conn)


@pytest.fixture
def budget_categories_repo(conn):
    """Repositorio de presupuestos con conexión de test"""
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
def expense_service(expense_repo, household_loader):
    return ExpenseService(expense_repo=expense_repo, household_loader=household_loader)


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
def period_id_month(household_id, period_repo):
    """Período en fase MONTH, listo para rehidratar."""
    period = Period(
        household_id=household_id,
        start_date=date(2026, 2, 6),
        status=Phase.MONTH,
        method=MetodoReparto.PROPORTIONAL,
    )
    return period_repo.save(period=period)


# Para raise
@pytest.fixture
def period_id_planning(household_id, period_repo):
    """Período en fase MONTH, listo para rehidratar."""
    period = Period(
        household_id=household_id,
        start_date=date(2025, 2, 6),
        status=Phase.PLANNING,
        method=MetodoReparto.PROPORTIONAL,
    )
    return period_repo.save(period=period)


@pytest.fixture
def budget_categories(period_id_month, budget_categories_repo):
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
            household_period_id=period_id_month, budget_category=budget_category
        )

    return {"fijos": fijos, "variables": variables, "alquiler": alquiler}


@pytest.fixture
def sample_expense_id(expense_repo, member_ids, period_id_month, budget_categories):
    """Gasto compartido en 'fijos' (heri paga, heri+amanda participan), guardado en BD."""
    expense = Expense(
        member="heri",
        amount_cents=34600,
        category=make_category("fijos", is_shared=True),
        participants=["heri", "amanda"],
    )
    return expense_repo.save(
        expense=expense, member_ids=member_ids, period_id=period_id_month
    )


# ============================================================
# Register expense service
# ============================================================
""" 
Participants explícitos: pásalos tú a mano (p.ej. participants=["heri"] en un gasto de "fijos", que por defecto metería a los dos) y comprueba que el guardado respeta exactamente lo que diste, no lo derivado.
"""


def test_register_expense_with_valid_data_persists_to_db(
    expense_service,
    expense_repo,
    household_id,
    period_id_month,
    member_ids,
    budget_categories,
):
    """register_expense con datos válidos deja fila en expenses + expense_participants."""
    expense_service.register_expense(
        household_id=household_id,
        period_id=period_id_month,
        member="amanda",
        category="fijos",
        amount_euros=575.67,
        description="Alquiler de febrero",
    )

    saved = expense_repo.find_with_participants(period_id_month)[0]

    assert saved["amount_cents"] == 57567
    assert saved["category"] == "fijos"
    assert saved["payer_id"] == member_ids["amanda"]
    assert set(saved["participants"]) == {"heri", "amanda"}  # fijos es compartida


def test_register_expense_with_incorrect_phase_raises_error(
    expense_service,
    household_id,
    period_id_planning,
    budget_categories,
):
    with pytest.raises(
        ValueError,
        match=f"Operación solo permitida en fase month. Fase actual: planning",
    ):
        expense_service.register_expense(
            household_id=household_id,
            period_id=period_id_planning,
            member="amanda",
            category="fijos",
            amount_euros=575.67,
            description="Alquiler de febrero",
        )


# FIXME naming
def test_register_expense_into_personal_category(
    expense_service,
    expense_repo,
    household_id,
    period_id_month,
    member_ids,
    budget_categories,
):
    """register_expense en una categoría no compartida, devuelve un solo participante"""
    expense_service.register_expense(
        household_id=household_id,
        period_id=period_id_month,
        member="amanda",
        category="variables",
        amount_euros=87.67,
        description="Alquiler de febrero",
    )

    saved = expense_repo.find_with_participants(period_id_month)[0]

    assert saved["amount_cents"] == 8767
    assert saved["category"] == "variables"
    assert saved["payer_id"] == member_ids["amanda"]
    assert set(saved["participants"]) == {"amanda"}  # fijos es compartida


# FIXME naming
def test_register_expense_into_shared_category_one_payer(
    expense_service,
    expense_repo,
    household_id,
    period_id_month,
    member_ids,
    budget_categories,
):
    """register_expense en una categoría no compartida, devuelve un solo participante"""
    expense_service.register_expense(
        household_id=household_id,
        period_id=period_id_month,
        member="heri",
        category="fijos",
        amount_euros=200.67,
        participants=["heri"],
        description="Pago luz de febrero",
    )

    saved = expense_repo.find_with_participants(period_id_month)[0]

    assert saved["amount_cents"] == 20067
    assert saved["category"] == "variables"
    assert saved["payer_id"] == member_ids["heri"]
    assert set(saved["participants"]) == {
        "heri"
    }  # fijos es compartida pero hay un solo pagador
