from src.utils.currency import to_euros, to_cents


class BudgetCategory:
    """Gestiona presupuesto planificado de una categoría (solo planificación)"""

    def __init__(self, name: str, planned_amount: float) -> None:
        self._validate_amount(planned_amount)

        self.name = name
        self.planned_amount: int = to_cents(planned_amount)

    # ====== VALIDATORS ======
    def _validate_amount(self, amount: float):
        """Valida que el monto presupuestado no sea negativo"""
        if amount < 0:
            raise ValueError("El monto presupuestado no puede ser negativo")

    def __repr__(self) -> str:  # pragma: no cover
        """Información técnica para debugging"""
        return (
            f"BudgetCategory(name={self.name}, planned={to_euros(self.planned_amount)})"
        )
