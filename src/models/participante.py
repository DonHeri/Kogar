class Participante:
    """Representa a una persona con su ingreso base mensual."""

    def __init__(self, name: str):

        if not name or not name.strip():
            raise ValueError("Nombre no puede estar vacío")

        # ====== Atributos ======
        self.name: str = name
        self.monthly_income: float = 0.0

    # Suma ingresos
    def add_incomes(self, income: float) -> None:
        if income < 0:
            raise ValueError("Ingreso no puede ser negativo")
        self.monthly_income += income

    def __repr__(self): # pragma: no cover
        return f"Participante('{self.name}', {self.monthly_income}€)"


