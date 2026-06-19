from src.models.category import Category
from src.utils.currency import to_cents, to_euros


class BudgetCategory:
    """Gestiona presupuesto planificado de una categoría (solo planificación)"""

    def __init__(
        self, category: Category, planned_amount: float, parent: str | None = None
    ) -> None:

        self._validate_amount(planned_amount)

        self.category = category
        self.planned_amount: int = to_cents(planned_amount)
        self.parent = parent

    @property
    def name(self) -> str:
        return self.category.name

    @property
    def is_shared(self) -> bool:
        return self.category.is_shared

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"BudgetCategory(name={self.name}, planned={to_euros(self.planned_amount)})"
        )

    # ====== VALIDATORS ======
    def _validate_amount(self, amount: float):
        """Valida que el monto presupuestado no sea negativo"""
        if isinstance(amount, bool):
            raise TypeError("El monto presupuestado no puede ser booleano")
        if amount < 0:
            raise ValueError("El monto presupuestado no puede ser negativo")
