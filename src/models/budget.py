class BudgetCategory:

    def __init__(self, name: str, planned_amount: float) -> None:

        # Evitar monto negativo
        if planned_amount <= 0:
            raise ValueError("El monto presupuestado no puede ser negativo")

        self.name = name  # Categoría ("fijos", "variable")
        self.planned_amount = planned_amount  # Dinero presupuestado
        self.spent = 0.0  # Dinero que se ha pagado ya
        self.member_contributions = (
            {}
        )  # {"Amanda": 0, "Heri": 0} -> Heri paga 60 -> {"Amanda": 0, "Heri": 60} - [spent = 60]

    def register_payment(self, name: str, amount: float):
        """Registra que un miembro pagó algo de esta categoría"""

        if amount <= 0:
            raise ValueError(f"El pago debe ser superior a 0")

        if name not in self.member_contributions:
            self.member_contributions[name] = 0

        self.member_contributions[name] += amount
        self.spent += amount

    def remaining(self):
        """Devolver el restante por pagar"""
        return self.planned_amount - self.spent

    def member_pending(
        self, member_name: str, owed_amount: float
    ):  # owed_amount lo conoce Household, budget no debe saber que debe pagar cada usuario, salvo que lo necesite temporal
        """Cuánto le falta pagar a un miembro de lo que debe"""
        paid = self.member_contributions.get(member_name, 0)
        return owed_amount - paid

    def __repr__(self) -> str:
        return f"- Categoría: {self.name.title()} - Presupuestado: {self.planned_amount} - Se han pagado {self.spent}$ - {self.member_contributions}"
