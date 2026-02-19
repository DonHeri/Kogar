from src.utils.change_eur_cent import to_euros,to_cents


class BudgetCategory:
    """Gestiona el presupuesto en una categoría (en céntimos internamente)"""

    def __init__(self, name: str, planned_amount: float) -> None:

        # Evitar monto negativo
        if planned_amount < 0:
            raise ValueError("El monto presupuestado no puede ser negativo")

        self.name = name  # Categoría ("fijos", "variable")
        self.planned_amount: int = to_cents(
            planned_amount
        )  # Dinero presupuestado en céntimos
        self.spent: int = 0  # Dinero que se ha pagado ya en céntimos
        self.member_contributions: dict[str, int] = (
            {}
        )  # {"Amanda": 0, "Heri": 0} -> céntimos

    def register_payment(self, member_name: str, amount: float):
        """Registra que un miembro pagó algo de esta categoría (en euros)"""

        if amount <= 0:
            raise ValueError(f"El pago debe ser superior a 0")

        cents = to_cents(amount)

        if member_name not in self.member_contributions:
            self.member_contributions[member_name] = 0

        self.member_contributions[member_name] += cents
        self.spent += cents

    def remaining(self) -> int:
        """Devolver el restante por pagar (en céntimos)"""
        return self.planned_amount - self.spent

    def member_pending(self, member_name: str, owed_amount: int) -> int:
        """Cuánto le falta pagar a un miembro de lo que debe (en céntimos)"""
        paid = self.member_contributions.get(member_name, 0)
        return owed_amount - paid

    def get_report(self) -> str:  # pragma: no cover
        """Información formateada para el usuario final"""
        return f"- Categoría: {self.name.title()} | Restante: {to_euros(self.remaining())} €"

    def __repr__(self) -> str:  # pragma: no cover
        """Información técnica para debugging"""
        return f"BudgetCategory(name={self.name}, planned={to_euros(self.planned_amount)}, spent={to_euros(self.spent)})"


class Budget:
    """Orquesta las diferentes categoría presupuestadas"""

    def __init__(self) -> None:
        self.categories = {
            "fijos": BudgetCategory("fijos", 0),
            "variables": BudgetCategory("variables", 0),
            "deuda": BudgetCategory("deuda", 0),
            "ahorro": BudgetCategory("ahorro", 0),
        }

    def set_budget(self, category: str, amount: float) -> None:
        """Establece un presupuesto para una categoría"""
        if category not in self.categories:
            raise ValueError("La categoría debe estar creada")
        if amount < 0:
            raise ValueError("Monto del presupuesto debe ser superior a 0")

        self.categories[category].planned_amount = to_cents(amount)
