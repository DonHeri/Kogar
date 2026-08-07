"""Precisión del dinero: los dos sitios donde se puede perder un céntimo.

Kogar guarda dinero en céntimos enteros justamente para que no se pierda nada.
Quedan dos puntos donde todavía puede pasar:

1. La frontera. `to_cents` recibe un float del usuario y lo redondea. Un float no
   representa exactamente 1,005, así que el redondeo puede caer al lado que no es.
2. El reparto. Dividir 100 ¢ entre tres da 33,33 y sobra un céntimo. El
   largest-remainder decide a quién se lo da, y su promesa es que la suma cuadre
   siempre.

Lo primero se documenta; lo segundo se somete a un barrido con miles de casos,
porque una promesa de "siempre" no se comprueba con tres ejemplos.
"""

import random

import pytest

from src.models.finance_calculator import FinanceCalculator
from src.utils.currency import (
    format_percentage,
    to_cents,
    to_euros,
    to_euros_float,
    to_percentage_basis,
)


# ====================================================
# TESTS: la frontera euros → céntimos
# ====================================================


@pytest.mark.parametrize(
    "euros, cents",
    [
        (0.0, 0),
        (0.01, 1),
        (19.99, 1999),
        (1234.56, 123456),
        (900.0, 90000),
        (0.1 + 0.2, 30),  # el 0.30000000000000004 clásico no se cuela
    ],
    ids=["cero", "un-centimo", "precio", "importe-largo", "redondo", "suma-de-floats"],
)
def test_to_cents_converts_the_amounts_a_user_actually_types(
    euros: float, cents: int
) -> None:
    """Los importes normales entran sin perder nada."""
    assert to_cents(euros) == cents


def test_cents_to_euros_and_back_is_stable() -> None:
    """Ida y vuelta por el borde no mueve el importe.

    Es la garantía que necesita cualquier pantalla de edición: abrir un gasto de
    123,45 €, no tocarlo y guardarlo tiene que dejar los mismos 12345 ¢.
    """
    for cents in (0, 1, 999, 12345, 123456789):
        assert to_cents(to_euros_float(cents)) == cents


def test_to_euros_formats_with_two_decimals_and_symbol() -> None:
    """Salida al usuario: siempre dos decimales, aunque el importe sea redondo."""
    assert to_euros(90000) == "900.00€"
    assert to_euros(1) == "0.01€"
    assert to_euros(0) == "0.00€"


def test_to_euros_keeps_the_sign_of_a_negative_balance() -> None:
    """Un balance negativo se muestra en negativo: es información, no un error."""
    assert to_euros(-13000) == "-130.00€"


def test_percentage_basis_round_trip_is_stable() -> None:
    """52,99 % entra como 5299 y vuelve a salir como '52.99%'."""
    assert to_percentage_basis(52.99) == 5299
    assert format_percentage(5299) == "52.99%"


@pytest.mark.xfail(
    strict=True,
    reason="to_cents usa round() sobre un float: 0.005 no es exactamente 0,005 "
    "y el redondeo cae hacia abajo",
)
def test_a_half_cent_rounds_up_instead_of_disappearing() -> None:
    """Medio céntimo tiene que subir a uno, no evaporarse.

    `round(0.005 * 100)` da 0 por dos motivos que se suman: el float más cercano a
    0,005 está por debajo, y round() desempata al par. Lo mismo con 1,005 → 100 ¢
    (un céntimo menos de la cuenta) y 0,145 → 14 ¢.

    Importa poco en un gasto suelto y mucho en un precio partido: repartir 0,29 €
    entre dos da 0,145 cada uno, y por este camino el hogar registra 0,28 €.
    La solución habitual es Decimal en el borde, o redondear sobre la cadena.
    """
    assert to_cents(0.005) == 1
    assert to_cents(1.005) == 101
    assert to_cents(0.145) == 15


@pytest.mark.xfail(
    strict=True,
    reason="to_percentage_basis arrastra el mismo redondeo de float que to_cents",
)
def test_a_percentage_with_three_decimals_rounds_up() -> None:
    """12,345 % son 1234,5 basis points y deberían subir a 1235.

    Hoy da 1234. En un reparto CUSTOM eso desplaza dinero real: sobre un
    presupuesto de 3.000 €, un basis point son 30 céntimos.
    """
    assert to_percentage_basis(12.345) == 1235


# ====================================================
# TESTS: el reparto no pierde céntimos — barrido
# ====================================================

_RANDOM_CASES = 2000


def test_contributions_always_add_up_to_the_budget() -> None:
    """Barrido: 2000 repartos aleatorios y la suma cuadra en todos.

    Ingresos y presupuestos al azar, entre dos y cinco miembros. La semilla es
    fija para que un fallo sea reproducible: si algún día salta, el caso concreto
    aparece en el mensaje y se puede convertir en un test suelto.
    """
    rng = random.Random(20260806)

    for _ in range(_RANDOM_CASES):
        incomes = {
            chr(97 + i): rng.randint(1, 500000) for i in range(rng.randint(2, 5))
        }
        budget = rng.randint(0, 1000000)

        contributions = FinanceCalculator.calculate_contribution_from_incomes(
            incomes, budget
        )

        assert sum(contributions.values()) == budget, (
            f"ingresos {incomes} y presupuesto {budget} dan {contributions}"
        )


def test_nobody_pays_more_than_their_share_plus_one_cent() -> None:
    """Barrido: el redondeo puede costar un céntimo, nunca más.

    Es la otra mitad de la promesa. Que la suma cuadre no basta: podría cuadrar
    cargándole 500 € de más a uno y de menos a otro. El techo de cada miembro es
    su parte exacta más el céntimo del desempate.
    """
    rng = random.Random(20260806)

    for _ in range(_RANDOM_CASES):
        incomes = {
            chr(97 + i): rng.randint(1, 500000) for i in range(rng.randint(2, 5))
        }
        budget = rng.randint(0, 1000000)
        total_income = sum(incomes.values())

        contributions = FinanceCalculator.calculate_contribution_from_incomes(
            incomes, budget
        )

        for member, income in incomes.items():
            exact_share = budget * income / total_income
            assert contributions[member] <= exact_share + 1, (
                f"{member} paga {contributions[member]}¢ y le tocaban {exact_share:.2f}¢"
            )


def test_proportional_percentages_always_add_up_to_100_percent() -> None:
    """Barrido: los porcentajes de reparto suman 10000 basis points siempre."""
    rng = random.Random(20260806)

    for _ in range(_RANDOM_CASES):
        incomes = {
            chr(97 + i): rng.randint(1, 500000) for i in range(rng.randint(2, 5))
        }

        percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
            incomes
        )

        assert sum(percentages.values()) == 10000, f"{incomes} da {percentages}"


@pytest.mark.parametrize("members", range(1, 30))
def test_equal_percentages_add_up_for_any_number_of_members(members: int) -> None:
    """3 miembros dan 33,33 % y sobra un basis point; 7 dan 14,28 y sobran 4.

    Se recorre de 1 a 29 porque el resto que hay que repartir cambia con cada
    número, y con él la posibilidad de que el largest-remainder falle.
    """
    percentages = FinanceCalculator.calculate_equal_percentage(
        {f"m{i}": 1 for i in range(members)}
    )

    assert sum(percentages.values()) == 10000
    assert len(percentages) == members


# ====================================================
# TESTS: repartos que no dan para todos
# ====================================================


def test_a_budget_smaller_than_the_number_of_members_gives_the_cents_to_the_top() -> None:
    """1 ¢ entre cinco: se lo lleva uno y los demás pagan 0.

    No hay forma de partir un céntimo, así que la única salida correcta es que
    alguien lo cargue entero. Lo que no vale es devolver cinco ceros y perderlo.
    """
    incomes = {f"m{i}": 1 for i in range(5)}

    one_cent = FinanceCalculator.calculate_contribution_from_incomes(incomes, 1)
    two_cents = FinanceCalculator.calculate_contribution_from_incomes(incomes, 2)

    assert sum(one_cent.values()) == 1
    assert sorted(one_cent.values()) == [0, 0, 0, 0, 1]
    assert sorted(two_cents.values()) == [0, 0, 0, 1, 1]


def test_a_zero_budget_charges_nobody() -> None:
    """Una categoría sin presupuesto no reparte nada, y no es un error."""
    contributions = FinanceCalculator.calculate_contribution_from_incomes(
        {"a": 100000, "b": 200000}, 0
    )

    assert contributions == {"a": 0, "b": 0}


def test_splitting_without_income_is_rejected() -> None:
    """Sin ingresos no hay proporción que calcular: se avisa en vez de dividir."""
    with pytest.raises(ValueError, match="Total de ingresos debe ser superior a 0"):
        FinanceCalculator.calculate_contribution_from_incomes({"a": 0, "b": 0}, 10000)


def test_percentages_that_dont_add_up_to_100_are_rejected() -> None:
    """Un presupuesto por porcentajes que no suman 100 % dejaría dinero sin asignar."""
    with pytest.raises(ValueError, match="10000"):
        FinanceCalculator.calculate_budget_from_percentages(
            total_incomes=100000, percentages={"fijos": 5000, "variables": 3000}
        )


@pytest.mark.xfail(
    strict=True,
    reason="calculate_equal_percentage divide entre len(members) sin comprobar "
    "que haya alguien",
)
def test_an_empty_household_gets_an_explanation_not_a_division_by_zero() -> None:
    """Repartir entre cero miembros tiene que decir qué falta.

    Hoy lanza ZeroDivisionError, que no menciona miembros ni reparto. Las otras
    dos funciones de reparto sí lanzan ValueError con su motivo; esta se quedó
    sin la comprobación.
    """
    with pytest.raises(ValueError):
        FinanceCalculator.calculate_equal_percentage({})
