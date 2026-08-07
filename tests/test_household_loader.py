from uuid import UUID
from datetime import date, datetime

import pytest
import psycopg2

from tests.helpers import make_category
from src.models.budget_category import BudgetCategory
from src.models.category import Category
from src.models.constants import Phase, MetodoReparto
from src.models.debt_bucket import DebtBucket
from src.models.debt_entry import DebtEntry
from src.models.saving_bucket import SavingBucket
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
from src.workflow.household_loader import HouseholdLoader, Load
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
    household_id: int,
    period_repo: PeriodRepository,
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
    period_id: int,
    member_id_heri: int,
    budget_categories_repo: BudgetCategoryRepository,
) -> dict[str, BudgetCategory]:
    """Dos categorías raíz (fijos, variables) + una hija (alquiler bajo fijos)."""
    fijos = BudgetCategory(
        Category("fijos", is_shared=True), 90000, ["member1", "member2"], parent=None
    )
    variables = BudgetCategory(
        Category("variables", is_shared=False), 30000, ["member1"], parent=None
    )
    alquiler = BudgetCategory(
        Category("alquiler", is_shared=True), 60000, ["member1", "member2"], parent="fijos"
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


@pytest.fixture
def debt_bucket_id(
    debt_bucket_repo: DebtBucketRepository,
    debt_entry_repo: DebtEntryRepository,
    household_id: int,
    member_ids: dict[str, int],
    period_id: int,
) -> UUID:
    """Deuda de heri (1200 €, cuota 200 €) con un pago de 200 € ya registrado."""
    bucket = DebtBucket(
        debt_bucket_name="moto",
        principal_cents=120000,
        owner="heri",
        installment_cents=20000,
    )
    bucket_id = debt_bucket_repo.save(
        debt_bucket=bucket, household_id=household_id, members_ids=member_ids
    )

    debt_entry_repo.save(
        debt_entry=DebtEntry(
            member_name="heri",
            amount_cents=20000,
            date=datetime(2026, 2, 10),
        ),
        debt_bucket_id=bucket_id,
        period_id=period_id,
        members_ids=member_ids,
    )

    return bucket_id


@pytest.fixture
def saving_bucket_id(
    saving_bucket_repo: SavingBucketRepository,
    saving_bucket_entry_repo: SavingBucketEntryRepository,
    household_id: int,
    member_ids: dict[str, int],
    period_id: int,
) -> UUID:
    """Bucket compartido 'vacaciones' con un depósito de 150 € de amanda."""
    bucket = SavingBucket(
        saving_bucket_name="vacaciones",
        owners=["heri", "amanda"],
        goal_cents=500000,
    )
    bucket_id = saving_bucket_repo.save(
        saving_bucket=bucket, household_id=household_id, member_ids=member_ids
    )

    saving_bucket_entry_repo.save(
        bucket_id=bucket_id,
        period_id=period_id,
        member_id=member_ids["amanda"],
        amount_cents=15000,
        entry_date=datetime(2026, 2, 12),
    )

    return bucket_id


# ===============================================
# TESTS — Load.BUDGET
# ===============================================


def test_load_budget_returns_member_ids_mapping(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """member_ids devuelto mapea nombre normalizado -> id de BD."""
    _, returned_member_ids, _ = household_loader.load_household(
        period_id, load=Load.BUDGET
    )

    assert returned_member_ids == member_ids


def test_load_budget_rehydrates_members_with_income(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """Los miembros rehidratados conservan su ingreso mensual en céntimos."""
    household, _, _ = household_loader.load_household(period_id, load=Load.BUDGET)

    assert household.members["heri"].monthly_income == 135400
    assert household.members["amanda"].monthly_income == 146700


def test_load_budget_returns_the_period_with_its_status_and_dates(
    household_loader: HouseholdLoader, household_id: int, period_id: int
) -> None:
    """El loader devuelve el Period entero: quien orquesta necesita la fase para
    validar y el rango de fechas para las consultas de deuda."""
    _, _, period = household_loader.load_household(period_id, load=Load.BUDGET)

    assert period.status == Phase.MONTH
    assert period.start_date == date(2026, 2, 6)
    assert period.household_id == household_id


def test_load_budget_rehydrates_budget_categories_with_planned_amounts(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    budget_categories: dict[str, BudgetCategory],
) -> None:
    """Cada BudgetCategory persistida se reconstruye con su planned_amount."""
    household, _, _ = household_loader.load_household(period_id, load=Load.BUDGET)

    assert household.budget.get_planned_amount("fijos") == 90000
    assert household.budget.get_planned_amount("variables") == 30000
    assert household.budget.get_planned_amount("alquiler") == 60000


def test_load_budget_rehydrates_parent_before_child_regardless_of_insertion_order(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    member_id_heri: int,
    budget_categories_repo: BudgetCategoryRepository,
) -> None:
    """Regresión: si la hija se persiste antes que la madre, Load.BUDGET no debe
    romper con 'La categoría debe estar creada'. El orden de hidratación no
    puede depender del orden físico de inserción en BD."""
    child = BudgetCategory(Category("alquiler", is_shared=True), 60000, ["member1", "member2"], parent="fijos")
    parent = BudgetCategory(
        Category("fijos", is_shared=True), 90000, ["member1", "member2"], parent=None
    )

    # Se guarda la hija ANTES que la madre a propósito
    budget_categories_repo.save(household_period_id=period_id, budget_category=child)
    budget_categories_repo.save(household_period_id=period_id, budget_category=parent)

    household, _, _ = household_loader.load_household(period_id, load=Load.BUDGET)

    assert household.budget.get_planned_amount("fijos") == 90000
    assert household.budget.get_planned_amount("alquiler") == 60000


def test_load_budget_does_not_hydrate_expenses(
    household_loader: HouseholdLoader,
    household_id: int,
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """Load.BUDGET es la carga ligera: no reconstruye histórico de gastos aunque exista en BD."""
    household, _, _ = household_loader.load_household(period_id, load=Load.BUDGET)

    assert household.get_total_spent() == 0


def test_load_budget_rehydrates_custom_splits_in_basis_points(
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

    household, _, _ = household_loader.load_household(period_id, load=Load.BUDGET)

    assert household.get_custom_splits() == {"heri": 5299, "amanda": 4701}


def test_load_budget_leaves_splits_empty_when_the_period_has_none(
    household_loader: HouseholdLoader,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """Un período PROPORTIONAL no guarda splits, y cargarlo no puede exigirlos."""
    household, _, _ = household_loader.load_household(period_id, load=Load.BUDGET)

    assert household.get_custom_splits() == {}


def test_load_budget_ignores_percentages_when_the_method_is_not_custom(
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

    household, _, _ = household_loader.load_household(period_id, load=Load.BUDGET)

    assert household.get_custom_splits() == {}


def test_load_budget_rehydrates_the_frozen_agreement(
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

    household, _, _ = household_loader.load_household(period_id, load=Load.BUDGET)

    assert household.get_agreed_contributions() == {
        "fijos": {"heri": 30000, "amanda": 20000},
        "reserva": {"heri": 10000, "amanda": 5000},
    }
    assert household.get_agreed_percentages() == {"heri": 6000, "amanda": 4000}
    assert household.get_member_owed_total("heri") == 40000


def test_load_budget_leaves_the_agreement_empty_while_planning(
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

    household, _, _ = household_loader.load_household(planning_id, load=Load.BUDGET)

    with pytest.raises(ValueError, match="no han sido congeladas"):
        household.get_agreed_contributions()


# ===============================================
# TESTS — Load.FOR_QUERIES
# ===============================================


def test_load_for_queries_keeps_member_ids_and_phase(
    household_loader: HouseholdLoader,
    period_id: int,
    member_ids: dict[str, int],
) -> None:
    """Load.FOR_QUERIES no rompe el contrato de Load.BUDGET (member_ids, period)."""
    _, returned_member_ids, period = household_loader.load_household(
        period_id, load=Load.FOR_QUERIES
    )

    assert returned_member_ids == member_ids
    assert period.status == Phase.MONTH


def test_load_for_queries_resolves_payer_by_id(
    household_loader: HouseholdLoader,
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """El gasto rehidratado atribuye correctamente el pagador (payer_id -> nombre)."""
    household, _, _ = household_loader.load_household(period_id, load=Load.FOR_QUERIES)

    assert household.get_member_paid_total("heri") == 34600
    assert household.get_member_paid_total("amanda") == 0


def test_load_for_queries_rehydrates_participants(
    household_loader: HouseholdLoader,
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """Los participantes del gasto se reconstruyen completos."""
    household, _, _ = household_loader.load_household(period_id, load=Load.FOR_QUERIES)

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
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """La categoría del gasto se resuelve contra el budget ya hidratado."""
    household, _, _ = household_loader.load_household(period_id, load=Load.FOR_QUERIES)

    assert household.get_category_spent("fijos") == 34600


def test_load_for_queries_preserves_the_expense_id(
    household_loader: HouseholdLoader,
    period_id: int,
    sample_expense_id: UUID,
) -> None:
    """El gasto rehidratado conserva su id, no recibe uno nuevo."""
    household, _, _ = household_loader.load_household(period_id, load=Load.FOR_QUERIES)

    expense = household.expense_tracker.get_all_expenses()[0]
    assert expense.id == sample_expense_id


def test_load_for_queries_with_no_expenses_returns_empty_tracker(
    household_loader: HouseholdLoader, household_id: int, period_id: int
) -> None:
    """Sin gastos en BD, Load.FOR_QUERIES no rompe y el tracker queda vacío."""
    household, _, _ = household_loader.load_household(period_id, load=Load.FOR_QUERIES)

    assert household.get_total_spent() == 0


# ===============================================
# TESTS — Load.FULL
# ===============================================


def test_load_full_brings_the_four_parts_on_the_same_household(
    household_loader: HouseholdLoader,
    period_id: int,
    budget_categories: dict[str, BudgetCategory],
    sample_expense_id: UUID,
    debt_bucket_id: UUID,
    saving_bucket_id: UUID,
) -> None:
    """Presupuesto, gastos, deuda y ahorro conviven en el MISMO objeto Household.

    Es la comprobación que faltaba: cada parte tenía su test por separado, pero
    ninguno verificaba que las cuatro se reconstruyen juntas sin pisarse. Un fallo
    de orden en la hidratación solo se ve aquí.
    """
    household, _, period = household_loader.load_household(period_id, load=Load.FULL)

    # 1) presupuesto, con su jerarquía
    assert household.budget.get_planned_amount("fijos") == 90000
    assert household.budget.get_planned_amount("alquiler") == 60000

    # 2) gastos, resueltos contra ese mismo presupuesto
    assert household.get_total_spent() == 34600
    assert household.get_category_spent("fijos") == 34600

    # 3) deuda, con su pago ya aplicado al saldo
    debt = household.debt_bucket_tracker.get_bucket_by_id(debt_bucket_id)
    assert debt.owner == "heri"
    assert debt.total_paid == 20000
    assert debt.remaining_balance == 100000

    # 4) ahorro, con su depósito
    saving = household.get_bucket_by_id(saving_bucket_id)
    assert saving.balance == 15000
    assert saving.balance_by_member["amanda"] == 15000

    assert period.status == Phase.MONTH


# ===============================================
# TESTS — Load.DEBTS y Load.SAVINGS
# ===============================================


def test_load_debts_brings_the_bucket_with_its_payments(
    household_loader: HouseholdLoader,
    period_id: int,
    debt_bucket_id: UUID,
) -> None:
    """Con Load.DEBTS el bucket llega entero, con su histórico de pagos."""
    household, _, _ = household_loader.load_household(period_id, load=Load.DEBTS)

    bucket = household.debt_bucket_tracker.get_bucket_by_id(debt_bucket_id)
    assert bucket.total_paid == 20000
    assert bucket.remaining_balance == 100000


def test_load_debts_leaves_budget_and_expenses_out(
    household_loader: HouseholdLoader,
    period_id: int,
    budget_categories: dict[str, BudgetCategory],
    sample_expense_id: UUID,
    debt_bucket_id: UUID,
) -> None:
    """Lo que NO se pide, no se carga — y esto es el motivo de todo el refactor.

    Los datos existen en BD (hay presupuesto y hay un gasto), así que si aparecen
    es que el loader los trajo sin que nadie se los pidiera.
    """
    household, _, _ = household_loader.load_household(period_id, load=Load.DEBTS)

    assert household.get_total_spent() == 0
    assert household.budget.categories == {}


def test_load_savings_brings_the_bucket_with_its_balance(
    household_loader: HouseholdLoader,
    period_id: int,
    saving_bucket_id: UUID,
) -> None:
    """Con Load.SAVINGS el bucket llega con su saldo por miembro."""
    household, _, _ = household_loader.load_household(period_id, load=Load.SAVINGS)

    bucket = household.get_bucket_by_id(saving_bucket_id)
    assert bucket.balance == 15000
    assert bucket.goal == 500000


def test_load_savings_leaves_debt_out(
    household_loader: HouseholdLoader,
    period_id: int,
    debt_bucket_id: UUID,
    saving_bucket_id: UUID,
) -> None:
    """Ahorro y deuda son ejes independientes: pedir uno no arrastra el otro."""
    household, _, _ = household_loader.load_household(period_id, load=Load.SAVINGS)

    assert household.get_all_buckets() != {}
    assert household.debt_bucket_tracker.get_all_buckets() == {}


# ===============================================
# TESTS — composición de flags
# ===============================================


def test_expenses_alone_drags_budget(
    household_loader: HouseholdLoader,
    period_id: int,
    budget_categories: dict[str, BudgetCategory],
    sample_expense_id: UUID,
) -> None:
    """Pedir EXPENSES sin BUDGET no puede fallar: el loader lo añade.

    Los gastos resuelven su categoría contra el árbol del presupuesto, así que sin
    él la hidratación reventaría. La dependencia se arregla por el llamador en vez
    de exigírsela, que es lo que hace `load_household` con `load |= Load.BUDGET`.
    """
    household, _, _ = household_loader.load_household(period_id, load=Load.EXPENSES)

    assert household.budget.get_planned_amount("fijos") == 90000
    assert household.get_total_spent() == 34600


def test_flags_compose_and_bring_only_what_was_asked(
    household_loader: HouseholdLoader,
    period_id: int,
    budget_categories: dict[str, BudgetCategory],
    sample_expense_id: UUID,
    debt_bucket_id: UUID,
    saving_bucket_id: UUID,
) -> None:
    """Dos flags combinados traen sus dos partes, y ninguna más."""
    household, _, _ = household_loader.load_household(
        period_id, load=Load.DEBTS | Load.SAVINGS
    )

    assert household.debt_bucket_tracker.get_all_buckets() != {}
    assert household.get_all_buckets() != {}

    assert household.budget.categories == {}
    assert household.get_total_spent() == 0
