"""El balance de deuda de un mes: cuánto tocaba, cuánto se pagó, cuánto falta.

`DebtBucket.get_period_balance` es lo que alimenta el resumen de deuda del mes, y
no tenía ni un test. Devuelve tres números:

- **committed**: la cuota que toca este mes;
- **paid**: lo pagado dentro de la ventana del período;
- **remaining**: lo que falta para cubrir la cuota.

El bucket, en cambio, es histórico: `total_paid` y `remaining_balance` cuentan
desde el principio de la deuda. Mezclar las dos escalas —la del mes y la de toda
la deuda— es de donde salen los descuadres que se fijan más abajo.
"""

from datetime import date, datetime

import pytest

from src.models.debt_bucket import DebtBucket
from src.models.debt_bucket_tracker import DebtBucketTracker

# Ventana de marzo de 2026, semiabierta: [1-mar, 1-abr)
_MARCH = (date(2026, 3, 1), date(2026, 4, 1))


@pytest.fixture
def loan() -> DebtBucket:
    """Préstamo de 1.000 € con cuota mensual de 300 €."""
    return DebtBucket(
        debt_bucket_name="prestamo",
        principal_cents=100000,
        owner="heri",
        installment_cents=30000,
    )


# ====================================================
# TESTS: el mes sin sorpresas
# ====================================================


def test_a_month_without_payments_owes_the_whole_installment(loan: DebtBucket) -> None:
    """Mes recién abierto: debes la cuota entera."""
    assert loan.get_period_balance(*_MARCH) == {
        "committed": 30000,
        "paid": 0,
        "remaining": 30000,
    }


def test_a_partial_payment_leaves_the_rest_pending(loan: DebtBucket) -> None:
    """Pagas 100 € de los 300 €: quedan 200 € por cubrir este mes."""
    loan.pay(10000, "heri", date=datetime(2026, 3, 10))

    assert loan.get_period_balance(*_MARCH) == {
        "committed": 30000,
        "paid": 10000,
        "remaining": 20000,
    }


def test_paying_the_installment_closes_the_month(loan: DebtBucket) -> None:
    """Cubierta la cuota, no queda nada pendiente del mes."""
    loan.pay(30000, "heri", date=datetime(2026, 3, 10))

    assert loan.get_period_balance(*_MARCH)["remaining"] == 0


def test_several_payments_in_the_month_add_up(loan: DebtBucket) -> None:
    """Tres pagos sueltos cuentan como uno solo del total."""
    for day in (2, 10, 25):
        loan.pay(10000, "heri", date=datetime(2026, 3, day))

    assert loan.get_period_balance(*_MARCH)["paid"] == 30000


# ====================================================
# TESTS: la ventana del período
# ====================================================


def test_a_payment_from_another_month_does_not_count(loan: DebtBucket) -> None:
    """Lo pagado en febrero se queda en febrero.

    El bucket guarda la deuda entera, que cruza meses; el balance del período
    solo mira su ventana. Sin este filtro, la cuota de un mes parecería pagada
    con el dinero del anterior.
    """
    loan.pay(30000, "heri", date=datetime(2026, 2, 15))

    assert loan.get_period_balance(*_MARCH)["paid"] == 0
    assert loan.total_paid == 30000  # en el histórico sí está


def test_the_first_day_of_the_period_belongs_to_it(loan: DebtBucket) -> None:
    """El rango es [inicio, fin): el día de apertura cuenta."""
    loan.pay(10000, "heri", date=datetime(2026, 3, 1))

    assert loan.get_period_balance(*_MARCH)["paid"] == 10000


def test_the_last_day_of_the_period_belongs_to_the_next_one(loan: DebtBucket) -> None:
    """El día de corte pertenece al mes que empieza, no a los dos.

    Es lo que impide que un pago hecho justo el 1 de abril se cuente en marzo y
    en abril a la vez.
    """
    loan.pay(10000, "heri", date=datetime(2026, 4, 1))

    assert loan.get_period_balance(*_MARCH)["paid"] == 0


def test_removing_a_payment_takes_it_out_of_the_month(loan: DebtBucket) -> None:
    """Corregir un pago mal metido devuelve el mes a como estaba."""
    loan.pay(10000, "heri", date=datetime(2026, 3, 10))
    entry_id = loan.entries[0].id

    loan.remove_payment(entry_id)

    assert loan.get_period_balance(*_MARCH) == {
        "committed": 30000,
        "paid": 0,
        "remaining": 30000,
    }


# ====================================================
# TESTS: la última cuota
# ====================================================


def test_the_last_installment_shrinks_to_what_is_left(loan: DebtBucket) -> None:
    """Quedan 100 € de una cuota de 300 €: solo se compromete lo que queda.

    Pedir la cuota entera en el último mes cobraría de más y dejaría la deuda en
    negativo.
    """
    loan.pay(90000, "heri", date=datetime(2026, 2, 1))

    assert loan.get_period_balance(*_MARCH)["committed"] == 10000


# ====================================================
# TESTS: el compromiso mensual del miembro
# ====================================================


def test_the_monthly_commitment_adds_up_every_loan() -> None:
    """Dos préstamos comprometen la suma de sus cuotas."""
    tracker = DebtBucketTracker()
    tracker.add_bucket(DebtBucket("coche", 100000, "heri", 30000))
    tracker.add_bucket(DebtBucket("movil", 60000, "heri", 20000))

    assert tracker.total_expected_installment_by_member("heri") == 50000


def test_a_paid_off_loan_stops_committing_money() -> None:
    """Una deuda saldada no consume capacidad del mes siguiente.

    Importa porque de este número sale la validación que compara deuda contra la
    parte de reserva del miembro: una deuda cerrada que siguiera pesando le
    bloquearía la planificación.
    """
    tracker = DebtBucketTracker()
    loan = DebtBucket("coche", 100000, "heri", 30000)
    tracker.add_bucket(loan)
    loan.pay(100000, "heri")

    assert tracker.total_expected_installment_by_member("heri") == 0


def test_another_members_loan_is_not_your_commitment() -> None:
    """La deuda es personal: la de uno no aparece en el compromiso del otro."""
    tracker = DebtBucketTracker()
    tracker.add_bucket(DebtBucket("coche", 100000, "heri", 30000))
    tracker.add_bucket(DebtBucket("master", 200000, "amanda", 50000))

    assert tracker.total_expected_installment_by_member("heri") == 30000
    assert tracker.total_expected_installment_by_member("amanda") == 50000


def test_the_member_summary_separates_the_month_from_the_whole_debt() -> None:
    """El resumen lleva las dos escalas y no las mezcla.

    'total_paid' es de toda la vida de la deuda; 'period.paid' es solo del mes.
    Confundirlas es el error clásico al leer este resumen, así que se fija aquí
    con números que no se parecen entre sí.
    """
    tracker = DebtBucketTracker()
    loan = DebtBucket("coche", 100000, "heri", 30000)
    bucket_id = tracker.add_bucket(loan)
    loan.pay(40000, "heri", date=datetime(2026, 2, 1))  # meses anteriores
    loan.pay(10000, "heri", date=datetime(2026, 3, 5))  # este mes

    summary = tracker.member_debt_summary("heri", *_MARCH)
    detail = summary["buckets"][bucket_id]

    assert detail["total_paid"] == 50000
    assert detail["remaining_balance"] == 50000
    assert detail["period"]["paid"] == 10000
    assert summary["totals"]["paid"] == 10000


# ====================================================
# DEFECTOS CONOCIDOS
# ====================================================


@pytest.mark.xfail(
    strict=True,
    reason="committed se recalcula con next_installment, que ya descuenta los "
    "pagos del propio mes: pagar la cuota reduce la cuota",
)
def test_paying_the_last_installment_leaves_the_month_square() -> None:
    """Pagar justo la última cuota tiene que dejar el mes a cero.

    Deuda de 1.000 €, cuota de 300 €, con 700 € ya pagados. Este mes toca cubrir
    los 300 € que quedan, se pagan, y el mes debería cerrar con remaining 0.

    Lo que sale es committed 0 y remaining -30000. El motivo: `committed` se
    calcula como min(cuota, saldo restante), y el saldo restante ya tiene
    descontado el pago que se acaba de hacer. O sea que el compromiso del mes se
    encoge según lo vas pagando, y el informe acaba diciendo que has pagado
    300 € de más cuando has pagado exactamente lo que tocaba.
    """
    loan = DebtBucket("prestamo", 100000, "heri", 30000)
    loan.pay(70000, "heri", date=datetime(2026, 2, 1))

    loan.pay(30000, "heri", date=datetime(2026, 3, 10))

    assert loan.get_period_balance(*_MARCH) == {
        "committed": 30000,
        "paid": 30000,
        "remaining": 0,
    }


@pytest.mark.xfail(
    strict=True,
    reason="DebtBucket.pay acepta description y no se la pasa a DebtEntry",
)
def test_a_payment_keeps_its_description() -> None:
    """La nota de un pago tiene que sobrevivir al pago.

    `pay()` declara el parámetro `description` y lo descarta: construye la
    DebtEntry sin él. El daño concreto está en la recarga — HouseholdLoader lee
    la descripción de la BD y se la pasa a pay(), así que la nota que el usuario
    escribió desaparece en cuanto se vuelve a cargar el hogar.
    """
    loan = DebtBucket("prestamo", 100000, "heri", 30000)

    loan.pay(10000, "heri", description="cuota de marzo")

    assert loan.entries[0].description == "cuota de marzo"
