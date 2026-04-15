from datetime import datetime

from src.utils.currency import to_euros
from src.utils.text import normalize_name


class Expense:
    """Representa un gasto realizado por un miembro en una categoría específica"""

    def __init__(
        self,
        member: str,
        category: str,
        amount_cents: int,
        description: str = "",
        is_shared: bool = True,
    ) -> None:
        """
        Crea un gasto con validaciones básicas

        Args:
            member: Nombre del miembro que pagó
            category: Categoría del gasto
            amount_cents: Monto en céntimos (int)
            description: Descripción opcional del gasto

        Raises:
            ValueError: Si member o category están vacíos, o amount no es positivo
        """
        self._validate_non_empty_string(member, "member")
        self._validate_non_empty_string(category, "category")
        self._validate_positive_amount(amount_cents, "amount")

        self._date: datetime = datetime.now()
        self.member = normalize_name(member)  # stored as lowercase
        self.category = category
        self._amount_cents: int = amount_cents
        self._is_shared = is_shared
        self.description = description

    @property
    def is_shared(self):
        return self._is_shared

    def change_is_shared(self, status: bool):
        self._is_shared = status

    @property
    def amount(self) -> int:
        """Retorna el monto del gasto en céntimos (solo lectura)"""
        return self._amount_cents

    @property
    def date(self) -> datetime:
        """Retorna la fecha del gasto como objeto datetime (solo lectura)"""
        return self._date

    def is_same_month(self, other_date: datetime = None) -> bool:
        """
        Verifica si el gasto es del mismo mes/año que otra fecha

        Args:
            other_date: Fecha a comparar (default: fecha actual)

        Returns:
            True si el gasto es del mismo mes y año
        """
        if other_date is None:
            other_date = datetime.now()
        return (
            self._date.year == other_date.year and self._date.month == other_date.month
        )

    def is_same_year(self, other_date: datetime = None) -> bool:
        """
        Verifica si el gasto es del mismo año que otra fecha

        Args:
            other_date: Fecha a comparar (default: fecha actual)

        Returns:
            True si el gasto es del mismo año
        """
        if other_date is None:
            other_date = datetime.now()
        return self._date.year == other_date.year

    def __repr__(self) -> str:
        """Representación técnica del gasto para debugging"""
        formatted_date = self._date.strftime("%d/%m/%Y")
        return f"Expense({self.member}, {self.category}, {to_euros(self.amount)}, {formatted_date})"

    # ====== VALIDACIONES ======
    def _validate_non_empty_string(self, value: str, field_name: str) -> None:
        """Valida que un string no esté vacío"""
        if not value or not value.strip():
            raise ValueError(f"{field_name} no puede estar vacío")

    def _validate_positive_amount(self, value: int, field_name: str) -> None:
        """Valida que un monto sea positivo"""
        if value <= 0:
            raise ValueError(f"{field_name} debe ser positivo")
