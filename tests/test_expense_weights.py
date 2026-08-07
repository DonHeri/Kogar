"""Reparto interno de un gasto: quién carga con cuánto.

Un `Expense` guarda un peso por participante, en basis points ×100. El settlement
parte el importe con esos pesos. Por eso un peso mal construido no salta como
error: sale como un número equivocado en la liquidación, y nadie se entera.

Los tests marcados `xfail` describen el comportamiento que debería tener el
dominio, no el que tiene hoy. Fallan a propósito. Cuando se arregle el defecto
pasarán, y `strict=True` avisará de que hay que quitar la marca.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.models.finance_calculator import FinanceCalculator
from src.models.household import Household
from src.models.member import Member
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.workflow.expense_weights import resolve_expense_weights
from tests.helpers import make_category


def _split(expense: Expense) -> dict[str, int]:
    """Lo que cada participante carga de este gasto, en céntimos.

    Es exactamente la cuenta que hace SettlementCalculator, aislada: así el test
    mide el reparto sin arrastrar un Household entero.
    """
    return FinanceCalculator.calculate_contribution_from_custom_splits(
        expense.weights, expense.amount
    )


# ====================================================
# TESTS: pesos por defecto — a partes iguales
# ====================================================


def test_without_weights_two_participants_split_in_half() -> None:
    """Sin pesos, dos participantes cargan 50/50."""
    expense = Expense("amanda", make_category("fijos"), 10000, ["amanda", "heri"])

    assert expense.weights == {"amanda": 5000, "heri": 5000}
    assert _split(expense) == {"amanda": 5000, "heri": 5000}


def test_without_weights_three_participants_still_sum_the_whole_expense() -> None:
    """Tres participantes con un importe indivisible: no se pierde ni un céntimo.

    100 ¢ entre tres da 33,33 ¢ cada uno. El céntimo suelto tiene que caer en
    alguien; lo que no puede es evaporarse y dejar el settlement descuadrado.
    """
    expense = Expense("a", make_category("fijos"), 100, ["a", "b", "c"])

    assert sum(expense.weights.values()) == 10000
    assert sum(_split(expense).values()) == 100


def test_the_payer_can_be_outside_the_participants() -> None:
    """Uno paga y otro consume: el pagador no tiene por qué cargar con nada.

    Es el caso de "te lo pago yo y ya me lo devuelves". El gasto es de heri
    entero aunque lo abone amanda.
    """
    expense = Expense("amanda", make_category("fijos"), 10000, ["heri"])

    assert expense.weights == {"heri": 10000}
    assert _split(expense) == {"heri": 10000}


# ====================================================
# TESTS: pesos explícitos
# ====================================================


def test_explicit_weights_are_kept_untouched() -> None:
    """Los pesos que llegan de fuera se respetan tal cual, sin recalcular."""
    expense = Expense(
        "amanda",
        make_category("fijos"),
        10000,
        ["amanda", "heri"],
        weights={"amanda": 7000, "heri": 3000},
    )

    assert expense.weights == {"amanda": 7000, "heri": 3000}
    assert _split(expense) == {"amanda": 7000, "heri": 3000}


def test_explicit_weights_survive_an_indivisible_amount() -> None:
    """70/30 sobre 3333 ¢: el reparto sigue sumando el importe exacto."""
    expense = Expense(
        "amanda",
        make_category("fijos"),
        3333,
        ["amanda", "heri"],
        weights={"amanda": 7000, "heri": 3000},
    )

    split = _split(expense)

    assert sum(split.values()) == 3333
    assert split == {"amanda": 2333, "heri": 1000}


def test_weights_that_miss_a_participant_are_rejected() -> None:
    """Un peso de menos dejaría dinero sin asignar, así que no se admite."""
    with pytest.raises(ValueError, match="un peso por participante"):
        Expense(
            "amanda",
            make_category("fijos"),
            10000,
            ["amanda", "heri"],
            weights={"amanda": 10000},
        )


def test_weights_for_someone_who_is_not_a_participant_are_rejected() -> None:
    """Sobra un peso: quien no participa no puede cargar con el gasto."""
    with pytest.raises(ValueError, match="un peso por participante"):
        Expense(
            "amanda",
            make_category("fijos"),
            10000,
            ["amanda"],
            weights={"amanda": 5000, "heri": 5000},
        )


def test_weights_that_dont_add_up_to_100_percent_are_rejected() -> None:
    """9999 basis points repartirían 99,99 % del gasto y el céntimo restante se
    perdería en silencio."""
    with pytest.raises(ValueError, match="deben sumar 100%"):
        Expense(
            "amanda",
            make_category("fijos"),
            10000,
            ["amanda", "heri"],
            weights={"amanda": 5000, "heri": 4999},
        )


def test_weights_over_100_percent_are_rejected() -> None:
    """Pasarse del 100 % cobraría de más entre todos los participantes."""
    with pytest.raises(ValueError, match="deben sumar 100%"):
        Expense(
            "amanda",
            make_category("fijos"),
            10000,
            ["amanda", "heri"],
            weights={"amanda": 6000, "heri": 5000},
        )


# ====================================================
# TESTS: identidad y fecha
# ====================================================


def test_an_expense_keeps_the_id_it_receives() -> None:
    """Rehidratar desde BD no puede cambiarle el id al gasto: dejaría de ser
    el mismo movimiento y se duplicaría al volver a guardar."""
    known_id = uuid4()

    expense = Expense(
        "amanda", make_category("fijos"), 10000, ["amanda"], id=known_id
    )

    assert expense.id == known_id


def test_two_expenses_created_the_same_way_are_still_distinct() -> None:
    """Dos gastos idénticos son dos movimientos: mismo importe, distinto id."""
    first = Expense("amanda", make_category("fijos"), 10000, ["amanda"])
    second = Expense("amanda", make_category("fijos"), 10000, ["amanda"])

    assert first.id != second.id


def test_an_expense_keeps_the_date_it_receives() -> None:
    """La fecha decide a qué período pertenece el gasto: se respeta la que llega."""
    when = datetime(2026, 2, 14, 20, 30)

    expense = Expense(
        "amanda", make_category("fijos"), 10000, ["amanda"], date=when
    )

    assert expense.date == when


# ====================================================
# TESTS: is_personal / is_shared
# ====================================================


def test_an_expense_paid_and_consumed_by_one_member_is_personal() -> None:
    """Personal significa: lo paga y lo consume el mismo, él solo."""
    expense = Expense("amanda", make_category("variables"), 10000, ["amanda"])

    assert expense.is_personal is True
    assert expense.is_shared is False


def test_an_expense_paid_for_someone_else_is_not_personal() -> None:
    """Un solo participante no basta para ser personal: tiene que ser el pagador.

    Si no, un gasto de heri pagado por amanda saldría del settlement y amanda
    nunca recuperaría su dinero.
    """
    expense = Expense("amanda", make_category("variables"), 10000, ["heri"])

    assert expense.is_personal is False


# ====================================================
# DEFECTOS CONOCIDOS
# ====================================================


@pytest.mark.xfail(
    strict=True,
    reason="Expense normaliza member pero deja participants tal cual: "
    "'Amanda' y 'amanda' quedan como dos personas distintas",
)
def test_participants_are_normalized_like_the_payer() -> None:
    """Un gasto personal escrito con mayúsculas tiene que seguir siendo personal.

    Hoy `member` pasa por normalize_name y `participants` no. El gasto queda con
    member='amanda' y participants=['Amanda'], así que is_personal da False y el
    gasto entra en el settlement: amanda acaba reclamándose dinero a sí misma.
    Los bordes (WorkflowManager, ExpenseService) normalizan antes de construir,
    y por eso no se ve — pero la validación está prometida en este constructor.
    """
    expense = Expense("Amanda", make_category("variables"), 10000, ["Amanda"])

    assert expense.participants == ["amanda"]
    assert expense.is_personal is True


@pytest.mark.xfail(
    strict=True,
    reason="Expense guarda la lista de participantes por referencia",
)
def test_mutating_the_original_list_does_not_change_the_expense() -> None:
    """El gasto tiene que quedarse con una copia de sus participantes.

    Hoy guarda la misma lista que recibe. Quien la reutilice fuera —un bucle que
    va montando gastos, por ejemplo— le añade participantes a un gasto ya creado.
    Y los pesos no se recalculan: el gasto queda con dos participantes y un solo
    peso, que es justo el estado que _resolve_weights existe para impedir.
    """
    participants = ["amanda"]
    expense = Expense("amanda", make_category("fijos"), 10000, participants)

    participants.append("heri")

    assert expense.participants == ["amanda"]
    assert set(expense.weights) == set(expense.participants)


@pytest.mark.xfail(
    strict=True,
    reason="add_participant no recalcula weights: deja al nuevo sin peso",
)
def test_adding_a_participant_keeps_weights_covering_everyone() -> None:
    """Sumar a alguien a un gasto tiene que repartirle también su parte.

    Hoy `add_participant` mete el nombre en la lista y no toca los pesos. El
    gasto queda con dos participantes y un peso del 100 % para el primero: el
    recién llegado no paga nada y el settlement no lo refleja.
    """
    expense = Expense("amanda", make_category("fijos"), 10000, ["amanda"])

    expense.add_participant("Heri")

    assert set(expense.weights) == {"amanda", "heri"}
    assert sum(expense.weights.values()) == 10000


@pytest.mark.xfail(
    strict=True,
    reason="_validate_non_empty_list solo mira si la lista está vacía, "
    "no si sus elementos lo están",
)
def test_an_empty_participant_name_is_rejected() -> None:
    """Un participante sin nombre no identifica a nadie.

    Hoy `[""]` pasa la validación —la lista no está vacía— y el gasto se
    construye con un peso del 100 % asignado a la cadena vacía. Ese "miembro"
    no existe en el hogar, así que el settlement revienta con KeyError al
    intentar apuntarle su parte.
    """
    with pytest.raises(ValueError):
        Expense("amanda", make_category("fijos"), 10000, [""])


@pytest.mark.xfail(
    strict=True,
    reason="_resolve_weights valida la suma pero no el signo de cada peso",
)
def test_negative_weights_are_rejected() -> None:
    """Un peso negativo suma 100 % con otro inflado y pasa la validación.

    12000 y -2000 suman 10000, así que hoy se aceptan. El resultado es que un
    participante carga con el 120 % del gasto y el otro con un -20 %: cobra por
    haber participado. Ningún reparto real tiene esa forma.
    """
    with pytest.raises(ValueError):
        Expense(
            "amanda",
            make_category("fijos"),
            10000,
            ["amanda", "heri"],
            weights={"amanda": 12000, "heri": -2000},
        )


# ====================================================
# TESTS: resolve_expense_weights — quién decide el reparto de un gasto
# ====================================================


def _household(method: MetodoReparto = MetodoReparto.EQUAL) -> Household:
    """Hogar con amanda (200.000 ¢) y heri (100.000 ¢), o sea 2:1."""
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


def test_explicit_weights_win_over_any_method() -> None:
    """Si quien llama da los porcentajes, no se traduce nada: mandan ellos."""
    household = _household(MetodoReparto.EQUAL)

    weights = resolve_expense_weights(
        household,
        ["amanda", "heri"],
        method=MetodoReparto.PROPORTIONAL,
        weights={"amanda": 8000, "heri": 2000},
    )

    assert weights == {"amanda": 8000, "heri": 2000}


def test_explicit_weights_are_normalized_by_name() -> None:
    """'Amanda' y 'amanda' son la misma persona también en los pesos.

    Los participantes ya llegan normalizados desde el borde. Si los pesos no se
    normalizaran igual, Expense vería dos conjuntos de nombres distintos y
    rechazaría un gasto perfectamente válido.
    """
    household = _household()

    weights = resolve_expense_weights(
        household, ["amanda", "heri"], weights={"Amanda": 5000, "HERI": 5000}
    )

    assert weights == {"amanda": 5000, "heri": 5000}


def test_an_explicit_method_overrides_the_household_one() -> None:
    """Un gasto puede repartirse distinto del acuerdo general sin cambiarlo.

    El hogar reparte a partes iguales; este gasto concreto va por ingresos, 2:1.
    Lo importante es que el hogar sigue en EQUAL después: elegir el reparto de un
    gasto no reconfigura nada.
    """
    household = _household(MetodoReparto.EQUAL)

    weights = resolve_expense_weights(
        household, ["amanda", "heri"], method=MetodoReparto.PROPORTIONAL
    )

    assert weights == {"amanda": 6667, "heri": 3333}
    assert household.method == MetodoReparto.EQUAL


def test_without_method_the_household_agreement_applies() -> None:
    """Sin decir nada, se usa el método acordado: es el valor por defecto."""
    household = _household(MetodoReparto.PROPORTIONAL)

    weights = resolve_expense_weights(household, ["amanda", "heri"])

    assert weights == {"amanda": 6667, "heri": 3333}


def test_weights_only_cover_the_participants_of_the_expense() -> None:
    """Un gasto de dos de tres se renormaliza entre esos dos.

    Sin renormalizar, la parte del ausente no la pagaría nadie y el pagador se
    quedaría con un crédito que el settlement no reclama a nadie.
    """
    household = _household(MetodoReparto.PROPORTIONAL)
    third = Member("carol")
    third.monthly_income = 300000
    household.register_member(third)

    weights = resolve_expense_weights(household, ["amanda", "carol"])

    assert weights == {"amanda": 4000, "carol": 6000}
    assert sum(weights.values()) == 10000


def test_custom_without_splits_says_what_is_missing() -> None:
    """Pedir CUSTOM sin haber definido porcentajes explica qué falta."""
    household = _household(MetodoReparto.CUSTOM)

    with pytest.raises(ValueError, match="set_custom_splits"):
        resolve_expense_weights(household, ["amanda", "heri"])


def test_resolve_does_not_validate_the_weights_it_passes_through() -> None:
    """Los pesos a mano los valida Expense, no el resolvedor.

    Se fija a propósito: `resolve_expense_weights` deja pasar {1, 2}, que no suma
    100 %. La validación existe una sola vez y está en el constructor de Expense,
    que es por donde pasan todos los caminos. Si algún día se moviera de sitio,
    este test avisa de que hay dos sitios donde mirar.
    """
    household = _household()

    passed_through = resolve_expense_weights(
        household, ["amanda", "heri"], weights={"amanda": 1, "heri": 2}
    )
    assert passed_through == {"amanda": 1, "heri": 2}

    with pytest.raises(ValueError, match="deben sumar 100%"):
        Expense(
            "amanda",
            make_category("fijos"),
            10000,
            ["amanda", "heri"],
            weights=passed_through,
        )


@pytest.mark.xfail(
    strict=True,
    reason="get_weights_for devuelve pronto en EQUAL, antes de comprobar que "
    "los participantes sean miembros del hogar",
)
def test_equal_split_also_rejects_someone_outside_the_household() -> None:
    """Repartir a partes iguales con un desconocido tiene que fallar igual.

    `get_weights_for` documenta que lanza si algún participante no es miembro, y
    con PROPORTIONAL y CUSTOM lo hace. Con EQUAL no: sale por el atajo de arriba
    y le da un peso al fantasma como si nada.

    Hoy lo tapa Household.register_expense, que valida participantes justo
    después. Pero el contrato de este método dice otra cosa, y quien lo llame
    directo —el resolvedor lo hace— se lo cree.
    """
    household = _household(MetodoReparto.EQUAL)

    with pytest.raises(ValueError, match="no son miembros del hogar"):
        household.get_weights_for(["amanda", "fantasma"], MetodoReparto.EQUAL)
