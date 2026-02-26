from src.utils.currency import to_euros, to_cents


class Member:
    """Representa a una persona con su ingreso base mensual"""

    def __init__(self, name: str):
        self._validate_name(name)
        self.name: str = name
        self.monthly_income: int = 0

    # ====== MUTATIONS ======
    def add_incomes(self, income: float) -> None:
        """Agrega ingreso mensual (en euros, se convierte a céntimos)"""
        self._validate_income(income)
        cents = to_cents(income)
        self.monthly_income += cents

    # ====== VALIDATORS ======
    def _validate_name(self, name: str):
        """Valida que el nombre no está vacío"""
        if not name or not name.strip():
            raise ValueError("Nombre no puede estar vacío")

    def _validate_income(self, income: float):
        """Valida que el ingreso es positivo"""
        if income < 0:
            raise ValueError("Ingreso no puede ser negativo")

    def __repr__(self):  # pragma: no cover
        return f"Participante('{self.name}', {to_euros(self.monthly_income)})"
