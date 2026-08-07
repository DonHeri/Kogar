"""Cómo se decide el reparto de UN gasto concreto.

Vive fuera de las dos fachadas, y no dentro de cada una, porque las dos rutas
—la stateful de `WorkflowManager` y la stateless de `ExpenseService`— tienen que
repartir igual. Cuando esta misma regla estuvo escrita dos veces, las dos copias
acabaron divergiendo.
"""

from src.models.constants import MetodoReparto
from src.models.household import Household
from src.utils.text import normalize_name


def resolve_expense_weights(
    household: Household,
    participants: list[str],
    method: MetodoReparto | None = None,
    weights: dict[str, int] | None = None,
) -> dict[str, int]:
    """Devuelve el peso de cada participante para este gasto.

    Tres formas de decirlo, de la más concreta a la más general:

    - `weights` → los porcentajes exactos. Se usan tal cual; `Expense` los valida.
    - `method` → se traducen desde ese método para estos participantes.
    - ninguno → el método que el hogar tiene acordado, como valor por defecto.

    Ese último caso es el acuerdo del hogar aplicándose, no el hogar decidiendo
    por su cuenta: quien llama puede saltárselo en cualquier gasto sin tocar la
    configuración del hogar.
    """
    if weights is not None:
        return {normalize_name(name): pct for name, pct in weights.items()}

    return household.get_weights_for(participants, method or household.method)
