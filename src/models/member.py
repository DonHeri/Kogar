from src.utils.currency import to_cents, to_euros
from src.utils.text import normalize_name


class Member:
    """Representa a una persona con su ingreso base mensual"""

    def __init__(self, name: str):
        # Storage: lowercase (interno consistente)
        # Display: usar format_name() en UI cuando sea necesario
        normalized = normalize_name(name)
        if not normalized:
            raise ValueError("El nombre del miembro no puede estar vacío")
        self.name: str = normalized
        self.monthly_income: int = 0

    # ====== MUTATIONS ======
    def set_income(self, income_cents: int) -> None:
        """Fija el ingreso mensual (en céntimos), sustituyendo el anterior.

        Es lo que se necesita mientras el período se planifica: el ingreso puede
        corregirse las veces que haga falta sin que se acumule.
        """
        self._validate_income(income_cents)
        self.monthly_income = income_cents

    def add_incomes(self, income_cents: int) -> None:
        """Suma al ingreso mensual (en céntimos)"""
        self._validate_income(income_cents)
        self.monthly_income += income_cents

    # ====== VALIDATORS ======
    def _validate_income(self, income_cents: int):
        """Valida que el ingreso es positivo"""
        if income_cents < 0:
            raise ValueError("Ingreso no puede ser negativo")

    def __repr__(self):  # pragma: no cover
        return f"Participante('{self.name}', {to_euros(self.monthly_income)})"
