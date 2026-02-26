from src.utils.currency import to_euros, to_cents


class BudgetCategory:
    """Gestiona presupuesto y pagos en una categoría específica (en céntimos internamente)"""

    def __init__(self, name: str, planned_amount: float) -> None:
        self._validate_amount(planned_amount)
        
        self.name = name
        self.planned_amount: int = to_cents(planned_amount)
        self.spent: int = 0
        self.member_contributions: dict[str, int] = {}

    # ====== MUTATIONS ======
    def register_payment(self, member_name: str, amount: float):
        """Registra un pago realizado por un miembro (en euros)"""
        self._validate_payment(amount)

        cents = to_cents(amount)

        if member_name not in self.member_contributions:
            self.member_contributions[member_name] = 0

        self.member_contributions[member_name] += cents
        self.spent += cents

    # ====== QUERIES ======
    def remaining(self) -> int:
        """Retorna lo que falta pagar de esta categoría (en céntimos)"""
        return self.planned_amount - self.spent

    def member_pending(self, member_name: str, owed_amount: int) -> int:
        """Calcula cuánto le falta pagar a un miembro de lo que debe (en céntimos)"""
        paid = self.member_contributions.get(member_name, 0)
        return owed_amount - paid

    def get_report(self) -> str:  # pragma: no cover
        """Retorna información formateada para mostrar al usuario"""
        return f"- Categoría: {self.name.title()} | Restante: {to_euros(self.remaining())} €"

    # ====== VALIDATORS ======
    def _validate_amount(self, amount: float):
        """Valida que el monto presupuestado no sea negativo"""
        if amount < 0:
            raise ValueError("El monto presupuestado no puede ser negativo")

    def _validate_payment(self, amount: float):
        """Valida que el pago sea positivo"""
        if amount <= 0:
            raise ValueError(f"El pago debe ser superior a 0")

    def __repr__(self) -> str:  # pragma: no cover
        """Información técnica para debugging"""
        return f"BudgetCategory(name={self.name}, planned={to_euros(self.planned_amount)}, spent={to_euros(self.spent)})"
