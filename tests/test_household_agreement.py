"""El acuerdo del período: lo que se congela al cerrar la planificación.

Mientras el período se planifica, el reparto se recalcula con el ingreso vivo:
cambias un sueldo y las contribuciones se mueven. `freeze_planning_state()` corta
eso. A partir de ahí manda una foto —cuánto puso cada uno en cada categoría— y el
mes entero se mide contra ella.

Congelar es lo que hace que el balance de un miembro signifique algo. Si el
acuerdo siguiera moviéndose, subirse el sueldo a mitad de mes le cambiaría la
deuda a todo el mundo hacia atrás.

Ese acuerdo también viaja a la base de datos y vuelve. Por eso aquí se comprueban
las tres cosas: que se congela, que aguanta, y que la ida y vuelta lo deja igual.
"""

import pytest

from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.member import Member
from src.models.saving_bucket import SavingBucket
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.workflow.budget_distribution_service import BudgetDistributionService
from tests.helpers import make_category


def _household(method: MetodoReparto = MetodoReparto.EQUAL) -> Household:
    """Hogar con dos miembros (200.000 ¢ y 100.000 ¢) y categorías estándar."""
    budget = Budget()
    budget.set_standard_categories()
    household = Household(
        budget=budget,
        expense_tracker=ExpenseTracker(),
        saving_bucket_tracker=SavingBucketTracker(),
        debt_bucket_tracker=DebtBucketTracker(),
        method=method,
    )
    for name, income in (("amanda", 200000), ("heri", 100000)):
        member = Member(name)
        member.monthly_income = income
        household.register_member(member)
    return household


@pytest.fixture
def planned() -> Household:
    """Hogar con el presupuesto puesto, listo para congelar.

    Se usa BudgetDistributionService y no el setter directo porque es quien
    recalcula la reserva: 300.000 ¢ de ingreso menos 150.000 ¢ presupuestados
    dejan 150.000 ¢ de reserva. Poniendo los importes a mano la reserva se queda
    a cero y el hogar reparte la mitad del ingreso, que no es el caso real.
    """
    household = _household(MetodoReparto.PROPORTIONAL)
    BudgetDistributionService.set_budget_for_category(household, "fijos", 100000)
    BudgetDistributionService.set_budget_for_category(household, "variables", 50000)
    return household


# ====================================================
# TESTS: antes de congelar no hay acuerdo
# ====================================================


def test_there_is_no_agreement_before_freezing(planned: Household) -> None:
    """Preguntar por el acuerdo antes de congelarlo dice qué falta hacer.

    Devolver un dict vacío sería peor: quien lo consulte vería a todo el mundo
    debiendo cero y lo tomaría por un mes ya saldado.
    """
    with pytest.raises(ValueError, match="no han sido congeladas"):
        planned.get_agreed_contributions()

    with pytest.raises(ValueError, match="no han sido congelados"):
        planned.get_agreed_percentages()


def test_the_live_split_is_available_before_freezing(planned: Household) -> None:
    """Lo que sí se puede ver es el reparto en vivo: es el borrador del acuerdo."""
    live = planned.get_current_contributions()

    assert live["fijos"]["contributions"] == {"amanda": 66667, "heri": 33333}


# ====================================================
# TESTS: congelar
# ====================================================


def test_freezing_captures_the_split_of_every_category(planned: Household) -> None:
    """El acuerdo guarda categoría por categoría, no solo el total.

    Hace falta ese detalle para responder "cuánto te toca de fijos", que es lo
    que el usuario compara con lo que ha gastado.
    """
    planned.freeze_planning_state()

    assert planned.get_agreed_contributions() == {
        "fijos": {"amanda": 66667, "heri": 33333},
        "variables": {"amanda": 33333, "heri": 16667},
        "reserva": {"amanda": 100000, "heri": 50000},
    }


def test_the_frozen_split_adds_up_to_the_whole_budget(planned: Household) -> None:
    """Todo el presupuesto queda repartido: nada se queda sin dueño."""
    planned.freeze_planning_state()

    total_agreed = sum(
        amount
        for by_member in planned.get_agreed_contributions().values()
        for amount in by_member.values()
    )

    assert total_agreed == planned.get_total_budgeted() == 300000


def test_a_later_income_change_does_not_move_the_agreement(planned: Household) -> None:
    """Subirle el sueldo a heri después de congelar no le cambia lo que debe.

    Es la razón de ser del congelado. El reparto en vivo sí se mueve —sirve para
    planificar el mes siguiente— pero el acuerdo del mes en curso se queda quieto.
    """
    planned.freeze_planning_state()
    agreed_before = planned.get_agreed_contributions()["fijos"]

    planned.set_member_income("heri", 900000)

    assert planned.get_agreed_contributions()["fijos"] == agreed_before
    assert planned.get_current_contributions()["fijos"]["contributions"] != agreed_before


def test_a_later_budget_change_does_not_move_the_agreement(planned: Household) -> None:
    """Tocar una categoría después de congelar tampoco reescribe el acuerdo."""
    planned.freeze_planning_state()

    planned.budget.set_planned_amount("fijos", 10000)

    assert planned.get_agreed_contributions()["fijos"] == {
        "amanda": 66667,
        "heri": 33333,
    }


def test_what_a_member_owes_is_the_sum_of_the_agreement(planned: Household) -> None:
    """Lo que debe un miembro es su columna del acuerdo, sumada."""
    planned.freeze_planning_state()

    assert planned.get_member_owed_total("amanda") == 66667 + 33333 + 100000
    assert planned.get_member_owed_total("heri") == 33333 + 16667 + 50000


def test_the_balance_compares_what_was_spent_against_the_agreement(
    planned: Household,
) -> None:
    """Balance = pagado − acordado. Negativo es que debes; positivo, que pusiste de más."""
    planned.freeze_planning_state()
    planned.register_expense(
        Expense("amanda", make_category("fijos"), 300000, ["amanda"])
    )

    assert planned.get_member_balance("amanda") == 300000 - 200000
    assert planned.get_member_balance("heri") == -100000


# ====================================================
# TESTS: ida y vuelta a la base de datos
# ====================================================


def test_restoring_an_agreement_reproduces_the_frozen_one(planned: Household) -> None:
    """Lo que devuelve el congelado entra tal cual al restaurarlo.

    Son la misma forma a propósito: si la BD guardara una representación distinta,
    habría que traducir en los dos sentidos y cada traducción es una ocasión de
    equivocarse de unidad.
    """
    planned.freeze_planning_state()
    contributions = planned.get_agreed_contributions()
    percentages = planned.get_agreed_percentages()

    reloaded = _household(MetodoReparto.PROPORTIONAL)
    reloaded.restore_agreement(
        contributions=contributions, percentages=percentages
    )

    assert reloaded.get_agreed_contributions() == contributions
    assert reloaded.get_agreed_percentages() == percentages
    assert reloaded.get_member_owed_total("amanda") == planned.get_member_owed_total(
        "amanda"
    )


def test_a_restored_agreement_does_not_need_a_budget(planned: Household) -> None:
    """El acuerdo restaurado vale por sí solo, sin recalcular nada.

    Un hogar recién cargado desde BD puede responder cuánto debe cada uno aunque
    el presupuesto que lo originó no se haya vuelto a montar.
    """
    reloaded = _household()
    reloaded.restore_agreement(
        contributions={"fijos": {"amanda": 30000, "heri": 20000}},
        percentages={"amanda": 6000, "heri": 4000},
    )

    assert reloaded.get_member_owed_total("amanda") == 30000


def test_restoring_copies_the_incoming_dicts(planned: Household) -> None:
    """El hogar no se queda con los dicts que le pasan.

    Quien los construyó —el loader, leyendo filas— puede reutilizarlos sin miedo
    a estar reescribiendo el acuerdo del hogar por detrás.
    """
    incoming = {"fijos": {"amanda": 30000, "heri": 20000}}
    reloaded = _household()
    reloaded.restore_agreement(
        contributions=incoming, percentages={"amanda": 6000, "heri": 4000}
    )

    incoming["fijos"]["amanda"] = 999999

    assert reloaded.get_agreed_contributions()["fijos"]["amanda"] == 30000


# ====================================================
# TESTS: el acuerdo y el mes nuevo
# ====================================================


def test_a_new_month_clears_the_agreement_and_the_expenses(planned: Household) -> None:
    """El mes nuevo empieza sin acuerdo y sin gastos: son del mes que se cerró."""
    planned.freeze_planning_state()
    planned.register_expense(
        Expense("amanda", make_category("fijos"), 30000, ["amanda"])
    )

    planned.reset_for_new_month()

    assert planned.get_total_spent() == 0
    with pytest.raises(ValueError, match="no han sido congeladas"):
        planned.get_agreed_contributions()


def test_a_new_month_keeps_savings_and_debt(planned: Household) -> None:
    """El ahorro y la deuda son del hogar, no del mes: cruzan el corte.

    Vaciarlos cada mes sería perder el saldo acumulado, que es justo lo que un
    bucket de ahorro existe para llevar.
    """
    bucket_id = planned.add_saving_bucket(SavingBucket("viaje", ["amanda"]))
    planned.deposit_to_saving_bucket(bucket_id, "amanda", 5000)
    planned.freeze_planning_state()

    planned.reset_for_new_month()

    assert planned.get_bucket_by_id(bucket_id).balance == 5000


def test_a_new_month_keeps_the_budget_categories(planned: Household) -> None:
    """Las categorías y su importe siguen puestos: son el plan de partida.

    Rehacer el presupuesto entero cada mes sería el trabajo que la aplicación
    existe para ahorrar.
    """
    planned.freeze_planning_state()

    planned.reset_for_new_month()

    assert planned.get_category_planned_amount("fijos") == 100000


# ====================================================
# DEFECTOS CONOCIDOS
# ====================================================


@pytest.mark.xfail(
    strict=True,
    reason="get_agreed_contributions devuelve una copia superficial: los dicts "
    "por categoría son los mismos objetos que guarda el hogar",
)
def test_the_frozen_agreement_cannot_be_edited_from_outside(
    planned: Household,
) -> None:
    """Lo congelado tiene que ser intocable desde fuera.

    `.copy()` sobre el diccionario exterior no protege los de dentro: quien lea
    el acuerdo y toque una cifra por categoría está reescribiendo el acuerdo del
    hogar. Con los porcentajes no pasa —ese dict es plano— así que el mismo
    método protege una cosa y no la otra.

    `restore_agreement` sí copia en profundidad al entrar. La salida se quedó a
    medias.
    """
    planned.freeze_planning_state()

    leaked = planned.get_agreed_contributions()
    leaked["fijos"]["amanda"] = 999999

    assert planned.get_agreed_contributions()["fijos"]["amanda"] == 66667


@pytest.mark.xfail(
    strict=True,
    reason="get_member_owed_total indexa el acuerdo por nombre sin comprobar "
    "que el miembro esté en él",
)
def test_a_member_outside_the_agreement_owes_nothing_instead_of_crashing() -> None:
    """Un miembro que no está en el acuerdo debe cero, no revienta.

    Pasa al cargar desde BD: el acuerdo se congeló con dos miembros y el hogar ya
    tiene tres, porque alguien se dio de alta después. Al preguntar por el nuevo,
    `sum(by_member[member_name] ...)` lanza KeyError con el nombre pelado, que no
    dice nada de acuerdos ni de períodos.

    Cero es la respuesta correcta: no participó en el acuerdo de ese mes, así que
    no le corresponde nada de él.
    """
    household = _household()
    household.restore_agreement(
        contributions={"fijos": {"amanda": 30000}}, percentages={"amanda": 10000}
    )

    assert household.get_member_owed_total("heri") == 0
