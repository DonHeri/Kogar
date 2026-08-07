"""Invariantes del settlement: las propiedades que deben cumplirse siempre.

`tests/test_settlement_calculator.py` comprueba casos concretos — dos miembros,
importes redondos, la transferencia que sale. Este archivo comprueba lo otro:
que el resultado cuadre pase lo que pase.

La propiedad central es la conservación. Cada miembro tiene un balance: lo que
puso menos lo que le tocaba. Tras aplicar las transferencias que devuelve el
settlement, ese balance tiene que quedar en cero para todos. Si no queda en
cero, alguien se ha comido dinero de otro y el reparto es incorrecto, aunque
cada transferencia suelta parezca razonable.
"""

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
from src.workflow.settlement_calculator import SettlementCalculator
from tests.helpers import make_category


def _household(method: MetodoReparto, incomes: dict[str, int]) -> Household:
    """Hogar con categorías estándar y los miembros indicados, con su ingreso."""
    budget = Budget()
    budget.set_standard_categories(list(incomes))
    household = Household(
        budget=budget,
        expense_tracker=ExpenseTracker(),
        saving_bucket_tracker=SavingBucketTracker(),
        debt_bucket_tracker=DebtBucketTracker(),
        method=method,
    )
    for name, income in incomes.items():
        member = Member(name)
        member.monthly_income = income
        household.register_member(member)
    return household


def _spend(
    household: Household,
    payer: str,
    amount: int,
    participants: list[str],
    category: str = "fijos",
) -> None:
    """Registra un gasto con los pesos que dicta el método del hogar."""
    household.expense_tracker.add_expense(
        Expense(
            payer,
            make_category(category),
            amount,
            participants,
            weights=household.get_weights_for(participants, household.method),
        )
    )


def _balances(household: Household) -> dict[str, int]:
    """Lo que cada miembro puso de más (positivo) o de menos (negativo).

    Se recalcula aquí en vez de leerlo del settlement: si el test usara el mismo
    cálculo que el código bajo prueba, un error en ese cálculo pasaría los dos
    lados a la vez y el test no vería nada.
    """
    balances = {name: 0 for name in household.members}
    for expense in household.expense_tracker.expenses:
        if expense.is_personal:
            continue
        owed = FinanceCalculator.calculate_contribution_from_custom_splits(
            expense.weights, expense.amount
        )
        for member, amount in owed.items():
            balances[member] -= amount
        balances[expense.member] += expense.amount
    return balances


def _apply(balances: dict[str, int], transfers: list[dict]) -> dict[str, int]:
    """Balances después de que cada deudor pague lo que dice el settlement."""
    settled = dict(balances)
    for transfer in transfers:
        settled[transfer["from"]] += transfer["amount"]
        settled[transfer["to"]] -= transfer["amount"]
    return settled


def _assert_settles_everyone(household: Household) -> list[dict]:
    """El invariante central: tras las transferencias nadie queda a deber."""
    balances = _balances(household)
    transfers = SettlementCalculator.calculate(household)

    assert _apply(balances, transfers) == {name: 0 for name in balances}, (
        f"balances {balances} no quedan a cero con {transfers}"
    )
    return transfers


# ====================================================
# TESTS: conservación
# ====================================================


def test_transfers_leave_every_member_at_zero_with_equal_split() -> None:
    """Cuatro miembros, dos pagadores: nadie queda descuadrado."""
    household = _household(
        MetodoReparto.EQUAL, {"a": 100000, "b": 100000, "c": 100000, "d": 100000}
    )
    members = household.get_member_names()

    _spend(household, "a", 40000, members)
    _spend(household, "b", 40000, members)

    _assert_settles_everyone(household)


def test_transfers_leave_every_member_at_zero_with_proportional_split() -> None:
    """Importes que no dividen exacto y tres ingresos distintos.

    9999 ¢ entre 1:2:3 y 5001 ¢ entre 1:2 obligan al largest-remainder a repartir
    céntimos sueltos en las dos direcciones. Es donde un descuadre aparecería.
    """
    household = _household(
        MetodoReparto.PROPORTIONAL, {"a": 100000, "b": 200000, "c": 300000}
    )

    _spend(household, "a", 9999, ["a", "b", "c"])
    _spend(household, "c", 5001, ["a", "b"])

    _assert_settles_everyone(household)


def test_transfers_leave_every_member_at_zero_with_custom_split() -> None:
    """CUSTOM 50/30/20 con gastos que comparten subconjuntos distintos."""
    household = _household(
        MetodoReparto.EQUAL, {"a": 100000, "b": 100000, "c": 100000}
    )
    household.set_custom_splits({"a": 5000, "b": 3000, "c": 2000})

    _spend(household, "a", 10000, ["a", "c"])
    _spend(household, "b", 7777, ["a", "b", "c"])
    _spend(household, "c", 3333, ["b", "c"])

    _assert_settles_everyone(household)


def test_a_one_cent_expense_is_absorbed_by_whoever_paid_it() -> None:
    """1 ¢ entre tres no se puede partir: lo carga entero el que lo puso.

    El largest-remainder le da el céntimo al de mayor resto, y con EQUAL ese es
    el primer miembro registrado — aquí, el propio pagador. Resultado: nadie debe
    nada y el settlement sale vacío. Reclamar 0 ¢ a los otros dos sería peor.
    """
    household = _household(
        MetodoReparto.EQUAL, {"a": 100000, "b": 100000, "c": 100000}
    )

    _spend(household, "a", 1, ["a", "b", "c"])

    assert _assert_settles_everyone(household) == []


# ====================================================
# TESTS: forma del resultado
# ====================================================


def test_no_transfer_is_zero_or_negative() -> None:
    """Una transferencia de 0 ¢ es ruido, y una negativa es una deuda al revés."""
    household = _household(
        MetodoReparto.PROPORTIONAL, {"a": 100000, "b": 200000, "c": 300000}
    )

    _spend(household, "a", 9999, ["a", "b", "c"])
    _spend(household, "c", 5001, ["a", "b"])

    transfers = SettlementCalculator.calculate(household)

    assert transfers, "el escenario tiene deuda pendiente: debe haber transferencias"
    assert all(t["amount"] > 0 for t in transfers)


def test_nobody_pays_and_receives_at_the_same_time() -> None:
    """Un miembro es deudor o acreedor, nunca las dos cosas.

    Aparecer en los dos lados significa que su deuda se compensó dando y
    recibiendo la misma cantidad: dos transferencias que se anulan.
    """
    household = _household(
        MetodoReparto.EQUAL, {"a": 100000, "b": 100000, "c": 100000, "d": 100000}
    )
    members = household.get_member_names()

    _spend(household, "a", 60000, members)
    _spend(household, "b", 20000, members)

    transfers = SettlementCalculator.calculate(household)

    senders = {t["from"] for t in transfers}
    receivers = {t["to"] for t in transfers}
    assert senders & receivers == set()


def test_the_settlement_does_not_consume_the_expenses() -> None:
    """Calcularlo dos veces da lo mismo: es una consulta, no un cierre."""
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 100000})

    _spend(household, "a", 10000, ["a", "b"])

    assert SettlementCalculator.calculate(household) == SettlementCalculator.calculate(
        household
    )


# ====================================================
# TESTS: qué gasto entra y cuál no
# ====================================================


def test_a_personal_expense_never_reaches_the_settlement() -> None:
    """Lo que uno paga para sí mismo no es asunto de nadie más."""
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 100000})

    _spend(household, "a", 99999, ["a"], category="variables")

    assert SettlementCalculator.calculate(household) == []


def test_an_expense_paid_for_another_member_reaches_the_settlement_whole() -> None:
    """a paga algo que consume b entero: b le debe el importe completo.

    No es un gasto compartido —solo participa b— pero tampoco es personal, y esa
    es la distinción que decide si entra.
    """
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 100000})

    _spend(household, "a", 10000, ["b"])

    assert SettlementCalculator.calculate(household) == [
        {"from": "b", "to": "a", "amount": 10000}
    ]


def test_two_even_expenses_paid_one_by_each_member_cancel_out() -> None:
    """Dos gastos gemelos de importe par pagados uno por cada uno se anulan."""
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 100000})

    _spend(household, "a", 12344, ["a", "b"])
    _spend(household, "b", 12344, ["a", "b"])

    assert SettlementCalculator.calculate(household) == []


def test_the_odd_cent_always_lands_on_the_same_member() -> None:
    """Dos gastos gemelos de importe impar NO se anulan: 'a' acaba debiendo 1 ¢.

    12345 ¢ al 50 % da 6172,5 a cada uno. El céntimo suelto se desempata por el
    orden en que aparecen los pesos, y ese orden sale de la lista de
    participantes. Como la lista se construye igual en los dos gastos, el mismo
    miembro carga con el céntimo las dos veces en vez de alternar.

    Cuadra —nadie pierde dinero— pero el sesgo es sistemático: en un hogar cuyos
    gastos caen en importe impar, el primero de la lista paga un céntimo de más
    cada vez. Este test fija el comportamiento actual; si algún día el desempate
    pasa a alternar, saltará aquí y no en la liquidación de un usuario.
    """
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 100000})

    _spend(household, "a", 12345, ["a", "b"])
    _spend(household, "b", 12345, ["a", "b"])

    assert SettlementCalculator.calculate(household) == [
        {"from": "a", "to": "b", "amount": 1}
    ]


def test_who_absorbs_the_odd_cent_depends_on_the_participants_order() -> None:
    """El mismo gasto entre los mismos dos cambia según cómo se listen.

    Es la otra cara del test anterior, y señala dónde está el desempate: en el
    orden de la lista de participantes, que es la que fija el orden de los pesos.
    Nada en el dominio dice que ese orden signifique nada, así que hoy la
    liquidación depende de un detalle que quien llama no sabe que está eligiendo.
    """
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 100000})

    a_first = Expense(
        "a", make_category("fijos"), 12345, ["a", "b"],
        weights=household.get_weights_for(["a", "b"], household.method),
    )
    b_first = Expense(
        "a", make_category("fijos"), 12345, ["b", "a"],
        weights=household.get_weights_for(["b", "a"], household.method),
    )

    split = FinanceCalculator.calculate_contribution_from_custom_splits
    assert split(a_first.weights, a_first.amount) == {"a": 6173, "b": 6172}
    assert split(b_first.weights, b_first.amount) == {"b": 6173, "a": 6172}


def test_the_category_does_not_decide_whether_an_expense_settles() -> None:
    """Lo que decide es la lista de participantes, no is_shared de la categoría.

    'variables' viene marcada como no compartida en la librería. Un gasto de
    variables que comparten dos personas se liquida igual: la categoría describe
    el presupuesto, no quién consume el gasto.
    """
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 100000})

    _spend(household, "a", 10000, ["a", "b"], category="variables")

    assert SettlementCalculator.calculate(household) == [
        {"from": "b", "to": "a", "amount": 5000}
    ]


# ====================================================
# TESTS: pesos y renormalización
# ====================================================


def test_proportional_weights_ignore_members_outside_the_expense() -> None:
    """Un gasto que comparten dos de tres se reparte solo entre esos dos.

    Ingresos 100/200/300. Un gasto de a y c se reparte 25/75 entre ellos, que es
    su proporción renormalizada — no 1/6 y 3/6, que dejaría la mitad sin pagar.
    """
    household = _household(
        MetodoReparto.PROPORTIONAL, {"a": 100000, "b": 200000, "c": 300000}
    )

    _spend(household, "a", 10000, ["a", "c"])

    assert SettlementCalculator.calculate(household) == [
        {"from": "c", "to": "a", "amount": 7500}
    ]


def test_a_member_with_no_income_pays_nothing_of_a_proportional_expense() -> None:
    """Con reparto por ingresos, quien no ingresa no carga con nada.

    Es la consecuencia lógica del método, y conviene tenerla fijada: quien mire
    el settlement de ese mes verá al de ingreso cero sin deuda, y no es un fallo.
    """
    household = _household(MetodoReparto.PROPORTIONAL, {"rico": 300000, "pobre": 0})

    _spend(household, "rico", 10000, ["rico", "pobre"])

    assert SettlementCalculator.calculate(household) == []


def test_an_expense_keeps_the_weights_it_was_created_with() -> None:
    """Cambiar el método después no reescribe los gastos ya registrados.

    El gasto congela su reparto al nacer. Si el settlement volviera a preguntarle
    al hogar, cambiar de método a mitad de mes recalcularía deudas ya cerradas.
    """
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 300000})

    _spend(household, "a", 10000, ["a", "b"])
    household.assign_distribution_method(MetodoReparto.PROPORTIONAL)

    assert SettlementCalculator.calculate(household) == [
        {"from": "b", "to": "a", "amount": 5000}
    ]


# ====================================================
# TESTS: entradas que el settlement no sabe manejar
# ====================================================


def test_the_household_rejects_a_participant_who_is_not_a_member() -> None:
    """La única defensa del settlement es que el gasto no llegue a registrarse.

    SettlementCalculator arranca un balance por miembro del hogar y le resta a
    cada participante lo suyo. Un participante que no es miembro no tiene balance
    donde restar, así que revienta con KeyError. Quien lo impide es
    Household.register_expense, y por eso este test lo fija: si esa validación
    se relajara, el fallo saldría lejos de aquí y con un error que no explica nada.
    """
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 100000})

    with pytest.raises(ValueError, match="no existe en el hogar"):
        household.register_expense(
            Expense("a", make_category("fijos"), 10000, ["a", "fantasma"])
        )


def test_a_ghost_participant_that_bypasses_the_household_breaks_the_settlement() -> None:
    """Documenta el fallo real cuando el gasto entra sin pasar por el hogar.

    El tracker acepta cualquier Expense: es una colección, no valida nada. Se deja
    fijado porque el KeyError no dice qué ha pasado, y quien lo vea en producción
    necesita saber que el culpable es un participante que no es miembro.
    """
    household = _household(MetodoReparto.EQUAL, {"a": 100000, "b": 100000})
    household.expense_tracker.add_expense(
        Expense("a", make_category("fijos"), 10000, ["a", "fantasma"])
    )

    with pytest.raises(KeyError):
        SettlementCalculator.calculate(household)
