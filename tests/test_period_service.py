from datetime import date

import psycopg2
import pytest

from src.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from src.models.constants import MetodoReparto, Phase
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
from src.workflow.household_service import HouseholdService
from src.workflow.period_service import PeriodService


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
def repos(conn: psycopg2.extensions.connection) -> dict[str, object]:
    return {
        "household": HouseholdRepository(conn),
        "member": MemberRepository(conn),
        "period": PeriodRepository(conn),
        "budget_categories": BudgetCategoryRepository(conn),
        "expense": ExpenseRepository(conn),
        "debt_bucket": DebtBucketRepository(conn),
        "debt_entry": DebtEntryRepository(conn),
        "saving_bucket": SavingBucketRepository(conn),
        "saving_bucket_entry": SavingBucketEntryRepository(conn),
    }


@pytest.fixture
def loader(repos: dict[str, object]) -> HouseholdLoader:
    return HouseholdLoader(
        household_repo=repos["household"],
        member_repo=repos["member"],
        period_repo=repos["period"],
        budget_categories_repo=repos["budget_categories"],
        expense_repository=repos["expense"],
        debt_bucket_repository=repos["debt_bucket"],
        debt_entry_repository=repos["debt_entry"],
        saving_bucket_repository=repos["saving_bucket"],
        saving_bucket_entry_repository=repos["saving_bucket_entry"],
    )


@pytest.fixture
def household_service(
    repos: dict[str, object], loader: HouseholdLoader
) -> HouseholdService:
    return HouseholdService(
        repos["household"], repos["member"], repos["period"], loader
    )


@pytest.fixture
def period_service(repos: dict[str, object], loader: HouseholdLoader) -> PeriodService:
    return PeriodService(loader, repos["period"], repos["budget_categories"])


@pytest.fixture
def household_id(household_service: HouseholdService) -> int:
    return household_service.create_household()


@pytest.fixture
def period_in_planning(
    period_service: PeriodService,
    household_service: HouseholdService,
    household_id: int,
) -> int:
    """Período abierto el 28-ene-2026 con dos miembros e ingresos 6000/4000."""
    period_id = period_service.start_new_month(
        household_id=household_id, start_date=date(2026, 1, 28)
    )
    household_service.register_member(household_id=household_id, name="Amanda")
    household_service.register_member(household_id=household_id, name="Heri")
    household_service.set_member_income(
        household_id=household_id, name="Amanda", amount_euros=6000
    )
    household_service.set_member_income(
        household_id=household_id, name="Heri", amount_euros=4000
    )
    period_service.set_standard_categories(period_id=period_id)
    return period_id


# ===============================================
# TESTS — Apertura del período
# ===============================================


def test_first_period_opens_without_a_previous_one(
    period_service: PeriodService, repos: dict[str, object], household_id: int
) -> None:
    """El primer período de un hogar se abre sin nada anterior que consultar"""
    period_id = period_service.start_new_month(
        household_id=household_id, start_date=date(2026, 1, 28)
    )

    period = repos["period"].find_by_id(period_id)

    assert period.status == Phase.PLANNING
    assert period.start_date == date(2026, 1, 28)


def test_cannot_open_a_period_while_another_is_open(
    period_service: PeriodService, household_id: int
) -> None:
    """Con un período en curso no se puede abrir otro"""
    period_service.start_new_month(household_id=household_id)

    with pytest.raises(ValueError, match="Cierra el mes en curso"):
        period_service.start_new_month(household_id=household_id)


def test_new_period_starts_today_when_no_date_given(
    period_service: PeriodService, repos: dict[str, object], household_id: int
) -> None:
    """Sin fecha, empieza hoy: la fecha no se hereda del período anterior.

    Si el usuario cierra en marzo y no vuelve hasta mayo, heredar abriría un período
    que arranca dos meses atrás. El hueco entre ambos es uso normal.
    """
    first = period_service.start_new_month(
        household_id=household_id, start_date=date(2026, 1, 28)
    )
    period_service.finish_month(period_id=first, end_date=date(2026, 2, 28))

    second = period_service.start_new_month(household_id=household_id)

    assert repos["period"].find_by_id(second).start_date == date.today()


def test_new_period_cannot_start_before_the_previous_one_ends(
    period_service: PeriodService, household_id: int
) -> None:
    """Un hueco es legítimo; un solape no: el movimiento contaría en los dos"""
    first = period_service.start_new_month(
        household_id=household_id, start_date=date(2026, 1, 28)
    )
    period_service.finish_month(period_id=first, end_date=date(2026, 2, 28))

    with pytest.raises(ValueError, match="solaparían"):
        period_service.start_new_month(
            household_id=household_id, start_date=date(2026, 2, 15)
        )


# ===============================================
# TESTS — Cierre del período
# ===============================================


def test_finish_month_uses_the_given_cut_off_date(
    period_service: PeriodService, repos: dict[str, object], household_id: int
) -> None:
    """La fecha de corte la decide el usuario, no el día en que pulsa el botón"""
    period_id = period_service.start_new_month(
        household_id=household_id, start_date=date(2026, 1, 28)
    )

    period_service.finish_month(period_id=period_id, end_date=date(2026, 2, 28))

    period = repos["period"].find_by_id(period_id)
    assert period.end_date == date(2026, 2, 28)
    assert period.status == Phase.CLOSING


def test_finish_month_closes_a_period_that_was_never_used(
    period_service: PeriodService, repos: dict[str, object], household_id: int
) -> None:
    """Cerrar un período que no llegó a MONTH es legítimo, no excepcional"""
    period_id = period_service.start_new_month(household_id=household_id)

    period_service.finish_month(period_id=period_id)

    assert repos["period"].find_by_id(period_id).status == Phase.CLOSING


def test_cannot_close_a_period_twice(
    period_service: PeriodService, household_id: int
) -> None:
    """Un período cerrado es inmutable: no se le puede reescribir el fin"""
    period_id = period_service.start_new_month(household_id=household_id)
    period_service.finish_month(period_id=period_id, end_date=date(2026, 2, 28))

    with pytest.raises(ValueError, match="ya está cerrado"):
        period_service.finish_month(period_id=period_id)


# ===============================================
# TESTS — Confirmar el plan
# ===============================================


def test_finish_planning_saves_the_agreement_and_advances(
    period_service: PeriodService, repos: dict[str, object], period_in_planning: int
) -> None:
    """Confirmar el plan guarda las contribuciones acordadas y pasa a MONTH"""
    period_service.set_planned_amount(
        period_id=period_in_planning, category="fijos", amount_euros=5000
    )

    period_service.finish_planning(period_id=period_in_planning)

    assert repos["period"].find_by_id(period_in_planning).status == Phase.MONTH

    contributions = repos["period"].get_agreed_contributions(period_in_planning)
    assert contributions == {"amanda": 600000, "heri": 400000}


def test_finish_planning_does_not_duplicate_categories(
    period_service: PeriodService, repos: dict[str, object], period_in_planning: int
) -> None:
    """Las categorías ya se guardaron al crearlas: confirmar el plan no las reescribe"""
    before = len(repos["budget_categories"].find_by_period(period_in_planning))
    period_service.set_planned_amount(
        period_id=period_in_planning, category="fijos", amount_euros=5000
    )

    period_service.finish_planning(period_id=period_in_planning)

    after = len(repos["budget_categories"].find_by_period(period_in_planning))
    assert after == before


def test_finish_planning_requires_a_budget(
    period_service: PeriodService, period_in_planning: int
) -> None:
    """Sin presupuesto asignado no se puede confirmar el plan"""
    with pytest.raises(ValueError, match="presupuesto"):
        period_service.finish_planning(period_id=period_in_planning)


def test_cannot_plan_a_period_already_in_month(
    period_service: PeriodService, period_in_planning: int
) -> None:
    """Con el mes en marcha, el presupuesto ya no se toca"""
    period_service.set_planned_amount(
        period_id=period_in_planning, category="fijos", amount_euros=5000
    )
    period_service.finish_planning(period_id=period_in_planning)

    with pytest.raises(ValueError, match="planning"):
        period_service.set_planned_amount(
            period_id=period_in_planning, category="fijos", amount_euros=9000
        )


# ===============================================
# TESTS — Arrastre entre períodos
# ===============================================


def test_new_period_carries_over_the_budget(
    period_service: PeriodService,
    repos: dict[str, object],
    household_id: int,
    period_in_planning: int,
) -> None:
    """El período nuevo hereda categorías y presupuesto como punto de partida"""
    period_service.set_planned_amount(
        period_id=period_in_planning, category="fijos", amount_euros=5000
    )
    period_service.finish_planning(period_id=period_in_planning)
    period_service.finish_month(
        period_id=period_in_planning, end_date=date(2026, 2, 28)
    )

    new_period = period_service.start_new_month(
        household_id=household_id, start_date=date(2026, 2, 28)
    )

    carried = {
        row["name"]: row["planned_amount"]
        for row in repos["budget_categories"].find_by_period(new_period)
    }
    assert carried["fijos"] == 500000


def test_carry_over_can_be_turned_off(
    period_service: PeriodService,
    repos: dict[str, object],
    household_id: int,
    period_in_planning: int,
) -> None:
    """Arrastrar es un default útil, no una imposición"""
    period_service.set_planned_amount(
        period_id=period_in_planning, category="fijos", amount_euros=5000
    )
    period_service.finish_planning(period_id=period_in_planning)
    period_service.finish_month(
        period_id=period_in_planning, end_date=date(2026, 2, 28)
    )

    new_period = period_service.start_new_month(
        household_id=household_id, start_date=date(2026, 2, 28), carry_over=False
    )

    assert repos["budget_categories"].find_by_period(new_period) == []


def test_carry_over_keeps_the_distribution_method(
    period_service: PeriodService,
    repos: dict[str, object],
    household_id: int,
    period_in_planning: int,
) -> None:
    """El método de reparto también se arrastra"""
    period_service.set_distribution_method(
        method=MetodoReparto.EQUAL, period_id=period_in_planning
    )
    period_service.set_planned_amount(
        period_id=period_in_planning, category="fijos", amount_euros=5000
    )
    period_service.finish_planning(period_id=period_in_planning)
    period_service.finish_month(
        period_id=period_in_planning, end_date=date(2026, 2, 28)
    )

    new_period = period_service.start_new_month(
        household_id=household_id, start_date=date(2026, 2, 28)
    )

    assert repos["period"].find_by_id(new_period).method == MetodoReparto.EQUAL


def test_carry_over_does_not_bring_the_previous_agreement(
    period_service: PeriodService,
    repos: dict[str, object],
    household_id: int,
    period_in_planning: int,
) -> None:
    """Se arrastra la configuración, no lo acordado: el nuevo plan está por confirmar"""
    period_service.set_planned_amount(
        period_id=period_in_planning, category="fijos", amount_euros=5000
    )
    period_service.finish_planning(period_id=period_in_planning)
    period_service.finish_month(
        period_id=period_in_planning, end_date=date(2026, 2, 28)
    )

    new_period = period_service.start_new_month(
        household_id=household_id, start_date=date(2026, 2, 28)
    )

    assert repos["period"].get_agreed_contributions(new_period) == {}


# ===============================================
# TESTS — Orden de fases
# ===============================================


def test_phase_order_follows_the_cycle() -> None:
    """El ciclo vivo es PLANNING -> MONTH -> CLOSING"""
    assert Phase.PLANNING.order < Phase.MONTH.order < Phase.CLOSING.order


def test_registration_is_outside_the_cycle() -> None:
    """REGISTRATION quedó en desuso: no forma parte del ciclo"""
    assert Phase.REGISTRATION not in Phase.cycle()
    assert Phase.REGISTRATION.order == -1


def test_phase_accessible_allows_current_and_past(
    period_service: PeriodService,
) -> None:
    """Una consulta de PLANNING sigue disponible con el mes en marcha"""
    period_service.validate_phase_accessible(
        required_phase=Phase.PLANNING, current_phase=Phase.MONTH
    )


def test_phase_accessible_rejects_future_phases(period_service: PeriodService) -> None:
    """Lo que aún no ha ocurrido no se puede consultar"""
    with pytest.raises(ValueError, match="month o posterior"):
        period_service.validate_phase_accessible(
            required_phase=Phase.MONTH, current_phase=Phase.PLANNING
        )


# ===============================================
# TESTS — Miembros e ingresos congelados
# ===============================================


def test_members_are_editable_before_any_period_exists(
    household_service: HouseholdService, household_id: int
) -> None:
    """Dar de alta el hogar es anterior al primer período: sin período no hay acuerdo
    que proteger, así que registrar y poner ingreso tiene que seguir funcionando."""
    household_service.register_member(household_id=household_id, name="Amanda")
    household_service.set_member_income(
        household_id=household_id, name="Amanda", amount_euros=6000
    )


def test_cannot_change_income_once_the_plan_is_confirmed(
    period_service: PeriodService,
    household_service: HouseholdService,
    household_id: int,
    period_in_planning: int,
) -> None:
    """finish_planning congela las contribuciones contra los ingresos de ese momento.
    Cambiar un ingreso después dejaría el acuerdo persistido apuntando a números
    que ya no existen."""
    period_service.set_planned_amount(
        period_id=period_in_planning, category="fijos", amount_euros=5000
    )
    period_service.finish_planning(period_id=period_in_planning)

    with pytest.raises(ValueError, match="planning"):
        household_service.set_member_income(
            household_id=household_id, name="Amanda", amount_euros=9000
        )


def test_cannot_register_a_member_once_the_plan_is_confirmed(
    period_service: PeriodService,
    household_service: HouseholdService,
    household_id: int,
    period_in_planning: int,
) -> None:
    """Un miembro nuevo con el mes en marcha no aparece en el acuerdo ya guardado:
    el reparto quedaría repartido entre dos y cobrado a tres."""
    period_service.set_planned_amount(
        period_id=period_in_planning, category="fijos", amount_euros=5000
    )
    period_service.finish_planning(period_id=period_in_planning)

    with pytest.raises(ValueError, match="planning"):
        household_service.register_member(household_id=household_id, name="Nuria")


def test_income_still_editable_while_planning(
    household_service: HouseholdService,
    household_id: int,
    period_in_planning: int,
) -> None:
    """Mientras el plan sigue abierto el ingreso se ajusta con normalidad"""
    household_service.set_member_income(
        household_id=household_id, name="Amanda", amount_euros=7000
    )
