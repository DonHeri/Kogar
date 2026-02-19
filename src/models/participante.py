from src.utils.change_eur_cent import to_euros, to_cents


class Participante:
    """Representa a una persona con su ingreso base mensual."""

    def __init__(self, name: str):

        if not name or not name.strip():
            raise ValueError("Nombre no puede estar vacío")

        # ====== Atributos ======
        self.name: str = name
        self.monthly_income: int = 0

    def add_incomes(self, income: float) -> None:
        """Recibe euros, convierte a céntimos internamente"""
        if income < 0:
            raise ValueError("Ingreso no puede ser negativo")
        cents = to_cents(income)
        self.monthly_income += cents

    def __repr__(self):  # pragma: no cover
        return f"Participante('{self.name}', {to_euros(self.monthly_income)})"

