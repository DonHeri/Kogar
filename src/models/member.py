from src.utils.currency import to_euros, to_cents
from src.utils.text import normalize_name


class Member:
    """Representa a una persona con su ingreso base mensual"""

    def __init__(self, name: str):
        # Storage: lowercase (interno consistente)
        # Display: usar format_name() en UI cuando sea necesario
        self.name: str = normalize_name(name)
        self.monthly_income: int = 0

    # ====== MUTATIONS ======
    def add_incomes(self, income_cents: int) -> None:
        """Agrega ingreso mensual (en céntimos)"""
        self._validate_income(income_cents)
        self.monthly_income += income_cents

    
    # ====== VALIDATORS ======
    def _validate_income(self, income_cents: int):
        """Valida que el ingreso es positivo"""
        if income_cents < 0:
            raise ValueError("Ingreso no puede ser negativo")

    def __repr__(self):  # pragma: no cover
        return f"Participante('{self.name}', {to_euros(self.monthly_income)})"
