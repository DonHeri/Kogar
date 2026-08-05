from src.models.household import Household

from src.models.income_entry import IncomeEntry


class IncomeEntryService:
    """DESCONECTADO A PROPÓSITO. No lo llama ninguna ruta pública.

    Los ingresos extra se retiraron porque no tienen un comportamiento correcto
    posible mientras el presupuesto trabaje en núcleo y no por miembro: el extra
    que cobra uno se reparte hoy entre todos.

    El daño lo hacían dos piezas juntas: `Household.get_total_incomes` sumaba los
    extras, y el `recalculate_reserve()` de abajo llevaba esa suma al
    planned_amount de reserva. Como el planned_amount es una de las tres entradas
    del reparto, registrar un extra en MONTH cambiaba lo que debía cada miembro y
    rompía el acuerdo congelado en finish_planning.

    Hoy `get_total_incomes` ya no los suma, así que la llamada de abajo recalcula
    al mismo valor y es inofensiva. Volver a sumarlos allí sin resolver antes el
    presupuesto por miembro revive el bug entero.
    """

    @staticmethod
    def add_income_entry(income_entry: IncomeEntry, household: Household):

        household._income_entries.append(income_entry)

        household.recalculate_reserve()
