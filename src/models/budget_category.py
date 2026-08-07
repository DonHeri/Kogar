from src.models.category import Category
from src.utils.currency import to_euros
from src.utils.text import normalize_name


class BudgetCategory:
    """Gestiona presupuesto planificado de una categoría (solo planificación)"""

    def __init__(
        self,
        category: Category,
        planned_amount: int,
        participants: list[str],
        parent: str | None = None,
    ) -> None:
        """
        Args:
            planned_amount: techo de la categoría, en céntimos ya convertidos
                por el borde.
            participants: quiénes cargan con esta categoría. Nunca vacío: su
                facturable se reparte entre ellos, así que una lista sin nadie
                deja dinero que no se le puede pedir a ningún miembro.
        """

        self._validate_amount(planned_amount)
        self._validate_non_empty_list(participants, "participants")

        self.category = category
        self.planned_amount: int = planned_amount
        self.participants = [normalize_name(name) for name in participants]
        self.parent = parent

    @property
    def name(self) -> str:
        return self.category.name

    @property
    def is_shared(self) -> bool:
        return len(self.participants) > 1

    def add_participant(self, member_name: str) -> None:
        """Añade un participante. Repetir uno que ya está no hace nada."""
        member_name = normalize_name(member_name)
        if not self.has_participant(member_name):
            self.participants.append(member_name)

    def has_participant(self, member_name: str) -> bool:
        """True si el miembro participa en esta categoría"""
        return normalize_name(member_name) in self.participants

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"BudgetCategory(name={self.name}, planned={to_euros(self.planned_amount)})"
        )

    # ====== VALIDATORS ======
    def _validate_amount(self, amount: int):
        """Valida que el monto presupuestado no sea negativo"""
        if isinstance(amount, bool):
            raise TypeError("El monto presupuestado no puede ser booleano")
        if amount < 0:
            raise ValueError("El monto presupuestado no puede ser negativo")

    def _validate_non_empty_list(self, value: list, field_name: str) -> None:
        """Valida que una lista tenga al menos un elemento"""
        if not value:
            raise ValueError(f"{field_name} no puede estar vacío")
