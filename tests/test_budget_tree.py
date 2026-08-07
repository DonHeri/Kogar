"""El árbol de categorías: qué cuenta contra el ingreso y qué cuelga de qué.

Una categoría raíz compite por el ingreso del hogar. Una hija vive dentro del
techo de su madre. De ahí salen dos números que se pueden confundir:

- el **planificado** de una categoría es su techo entero;
- el **facturable** es lo que reparte entre los miembros, o sea su techo menos lo
  que ya ha delegado en sus hijas.

Si el facturable se calculara mal, el hogar repartiría dos veces el mismo dinero:
una en la madre y otra en la hija. Los tests de aquí vigilan esa frontera, y qué
pasa con los gastos cuando una categoría desaparece.
"""

import pytest

from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.exceptions import CeilingBelowChildrenError
from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.member import Member
from src.models.saving_bucket_tracker import SavingBucketTracker


@pytest.fixture
def budget() -> Budget:
    """Presupuesto con las tres categorías estándar."""
    budget = Budget()
    budget.set_standard_categories()
    return budget


@pytest.fixture
def household() -> Household:
    """Hogar con dos miembros, categorías estándar y reparto a partes iguales."""
    budget = Budget()
    budget.set_standard_categories()
    household = Household(
        budget=budget,
        expense_tracker=ExpenseTracker(),
        saving_bucket_tracker=SavingBucketTracker(),
        debt_bucket_tracker=DebtBucketTracker(),
        method=MetodoReparto.EQUAL,
    )
    for name, income in (("amanda", 200000), ("heri", 100000)):
        member = Member(name)
        member.monthly_income = income
        household.register_member(member)
    return household


# ====================================================
# TESTS: facturable — el techo menos lo delegado
# ====================================================


def test_a_leaf_bills_its_whole_ceiling(budget: Budget) -> None:
    """Sin hijas no hay nada delegado: el facturable es el techo."""
    budget.set_planned_amount("fijos", 100000)

    assert budget.get_category_billable("fijos") == 100000


def test_a_parent_only_bills_what_it_has_not_delegated(budget: Budget) -> None:
    """Techo de 1000 € con 800 € en la hija: la madre reparte los 200 € que quedan.

    Es la cuenta que impide cobrar dos veces el mismo dinero. Si la madre
    repartiera su techo entero, los 800 € del alquiler se cobrarían dos veces:
    una en 'fijos' y otra en 'alquiler'.
    """
    budget.add_category("alquiler", parent="fijos")
    budget.set_planned_amount("fijos", 100000)
    budget.set_planned_amount("alquiler", 80000)

    assert budget.get_category_billable("fijos") == 20000
    assert budget.get_category_billable("alquiler") == 80000


def test_several_children_all_count_against_the_same_ceiling(budget: Budget) -> None:
    """Dos hijas consumen techo a la vez, no cada una por su cuenta."""
    budget.add_category("alquiler", parent="fijos")
    budget.add_category("suministros", parent="fijos")
    budget.set_planned_amount("fijos", 100000)
    budget.set_planned_amount("alquiler", 60000)
    budget.set_planned_amount("suministros", 30000)

    assert budget.get_child_total_planned("fijos") == 90000
    assert budget.get_category_billable("fijos") == 10000


def test_only_root_categories_count_against_the_income(budget: Budget) -> None:
    """El total presupuestado suma raíces: las hijas ya están dentro de su madre."""
    budget.add_category("alquiler", parent="fijos")
    budget.set_planned_amount("fijos", 100000)
    budget.set_planned_amount("alquiler", 80000)
    budget.set_planned_amount("variables", 50000)

    assert budget.get_root_categories() == ["fijos", "variables", "reserva"]
    assert budget.get_total_budgeted() == 150000


def test_the_ceiling_cannot_drop_below_what_the_children_hold(budget: Budget) -> None:
    """Bajar el techo por debajo de sus hijas daría un facturable negativo.

    Un facturable negativo se repartiría entre los miembros como una devolución
    que nadie ha hecho, y descuadraría el mes entero.
    """
    budget.add_category("alquiler", parent="fijos")
    budget.set_planned_amount("fijos", 100000)
    budget.set_planned_amount("alquiler", 80000)

    with pytest.raises(CeilingBelowChildrenError) as error:
        budget.set_planned_amount("fijos", 70000)

    assert error.value.category == "fijos"
    assert error.value.children_total_cents == 80000


def test_the_ceiling_can_drop_to_exactly_what_the_children_hold(budget: Budget) -> None:
    """Delegar el techo entero es legítimo: la madre se queda sin facturable."""
    budget.add_category("alquiler", parent="fijos")
    budget.set_planned_amount("fijos", 100000)
    budget.set_planned_amount("alquiler", 80000)

    budget.set_planned_amount("fijos", 80000)

    assert budget.get_category_billable("fijos") == 0


# ====================================================
# TESTS: profundidad y herencia
# ====================================================


def test_a_child_cannot_have_children_of_its_own(budget: Budget) -> None:
    """Solo dos niveles. Un tercero rompería la cuenta del facturable, que resta
    un único nivel de hijas."""
    budget.add_category("alquiler", parent="fijos")

    with pytest.raises(ValueError, match="2 niveles"):
        budget.add_category("garaje", parent="alquiler")


def test_a_child_inherits_is_shared_from_its_parent(budget: Budget) -> None:
    """La hija hereda de su madre, no de la librería.

    'ocio' está en la librería como no compartida. Colgada de 'fijos', que sí lo
    es, pasa a compartida: manda el árbol que ha montado el usuario.
    """
    budget.add_category("ocio", parent="fijos")

    assert budget.categories["fijos"].is_shared is True
    assert budget.categories["ocio"].is_shared is True


def test_the_children_list_is_a_copy(budget: Budget) -> None:
    """Quien consulta las hijas no puede reescribir el árbol sin querer."""
    budget.add_category("alquiler", parent="fijos")

    children = budget.get_children("fijos")
    children.append("inventada")

    assert budget.get_children("fijos") == ["alquiler"]


# ====================================================
# TESTS: borrado
# ====================================================


def test_a_parent_with_children_cannot_be_deleted(budget: Budget) -> None:
    """Borrar la madre dejaría a las hijas colgando o las ascendería a raíz.

    Ascenderlas cambiaría el presupuesto sin que el usuario lo pida: pasarían a
    competir contra el ingreso en vez de vivir dentro de un techo.
    """
    budget.add_category("alquiler", parent="fijos")

    with pytest.raises(ValueError, match="tiene subcategorías"):
        budget.delete_budget_category("fijos")


def test_deleting_a_child_frees_its_parent_ceiling(budget: Budget) -> None:
    """Al borrar la hija, su importe deja de contar contra el techo de la madre.

    Sin desenganchar el índice de hijas, la madre seguiría creyendo que tiene
    800 € delegados y no dejaría bajar su techo nunca más.
    """
    budget.add_category("alquiler", parent="fijos")
    budget.set_planned_amount("fijos", 100000)
    budget.set_planned_amount("alquiler", 80000)

    budget.delete_budget_category("alquiler")

    assert budget.get_children("fijos") == []
    assert budget.get_category_billable("fijos") == 100000
    budget.set_planned_amount("fijos", 10000)  # ya no hay hijas que lo impidan


def test_deleting_the_auto_calculated_category_leaves_the_budget_without_reserve(
    budget: Budget,
) -> None:
    """Sin 'reserva' no hay categoría auto-calculada, y quien la pida se entera.

    Importa porque de la reserva sale la capacidad de deuda de cada miembro: si
    desaparece en silencio, la validación de deuda mide contra cero sin avisar.
    """
    budget.delete_budget_category("reserva")

    with pytest.raises(ValueError, match="No hay categoría auto-calculada"):
        budget.get_auto_calculated_category()


# ====================================================
# TESTS: qué pasa con los gastos al borrar (Household)
# ====================================================


def test_deleting_a_child_moves_its_expenses_up_to_the_parent(
    household: Household,
) -> None:
    """Los gastos de la hija suben a la madre, y el total no se mueve.

    Es neutro: ya contaban dentro del techo de la madre. Lo que no puede pasar es
    que el gasto se quede apuntando a una categoría que ya no existe, porque
    entonces desaparecería de todos los resúmenes sin haberse borrado.
    """
    household.add_category("alquiler", parent="fijos")
    household.budget.set_planned_amount("fijos", 100000)
    household.budget.set_planned_amount("alquiler", 80000)
    household.register_expense(
        Expense("amanda", household.budget.get_category("alquiler"), 30000, ["amanda"])
    )

    household.remove_category("alquiler")

    assert household.get_category_spent("fijos") == 30000
    assert household.get_total_spent() == 30000
    assert "alquiler" not in household.get_active_categories()


def test_a_root_with_expenses_cannot_be_deleted(household: Household) -> None:
    """Una raíz no tiene a quién subirle los gastos, así que se avisa."""
    household.budget.set_planned_amount("fijos", 100000)
    household.register_expense(
        Expense("amanda", household.budget.get_category("fijos"), 30000, ["amanda"])
    )

    with pytest.raises(ValueError, match="tiene gastos asociados"):
        household.remove_category("fijos")


def test_a_root_without_expenses_can_be_deleted(household: Household) -> None:
    """Sin gastos que reubicar, borrar una raíz no tiene consecuencias."""
    household.budget.set_planned_amount("variables", 50000)

    household.remove_category("variables")

    assert "variables" not in household.get_active_categories()


def test_spending_in_a_child_counts_against_the_parent_ceiling(
    household: Household,
) -> None:
    """Lo gastado en la hija consume presupuesto de la madre.

    El techo de 'fijos' es lo que el hogar se permite gastar en fijos, alquiler
    incluido. Si el gasto del alquiler no contara ahí, el resumen diría que
    quedan 1000 € libres cuando ya se han ido 800 €.
    """
    household.add_category("alquiler", parent="fijos")
    household.budget.set_planned_amount("fijos", 100000)
    household.budget.set_planned_amount("alquiler", 80000)
    household.register_expense(
        Expense("amanda", household.budget.get_category("alquiler"), 80000, ["amanda"])
    )

    assert household.get_category_spent("fijos") == 80000
    assert household.get_category_remaining("fijos") == 20000


def test_spending_in_the_parent_does_not_count_against_the_child(
    household: Household,
) -> None:
    """La cuenta va hacia arriba, no hacia abajo: la hija solo ve lo suyo."""
    household.add_category("alquiler", parent="fijos")
    household.budget.set_planned_amount("fijos", 100000)
    household.budget.set_planned_amount("alquiler", 80000)
    household.register_expense(
        Expense("amanda", household.budget.get_category("fijos"), 15000, ["amanda"])
    )

    assert household.get_category_spent("alquiler") == 0
    assert household.get_category_spent("fijos") == 15000


def test_contributions_never_charge_the_same_money_twice(household: Household) -> None:
    """Con hijas de por medio, lo repartido entre miembros sigue siendo el total.

    Es el invariante que justifica todo el concepto de facturable: la suma de lo
    que aporta cada miembro tiene que ser exactamente el presupuesto del hogar,
    ni un céntimo más por culpa del doble conteo.
    """
    household.add_category("alquiler", parent="fijos")
    household.add_category("suministros", parent="fijos")
    household.budget.set_planned_amount("fijos", 150000)
    household.budget.set_planned_amount("alquiler", 80000)
    household.budget.set_planned_amount("suministros", 40000)
    household.budget.set_planned_amount("variables", 50000)

    contributions = household.get_total_contributions_by_member()

    assert sum(contributions.values()) == household.get_total_budgeted() == 200000
