from src.models.category import Category
from src.utils.currency import to_euros
from src.utils.text import normalize_name
from src.models.constants import MetodoReparto


class BudgetCategory:
    """Gestiona presupuesto planificado de una categoría (solo planificación)"""

    def __init__(
        self,
        category: Category,
        planned_amount: int,
        participants: list[str],
        method: MetodoReparto | None = None,
        custom_splits: dict[str, int] | None = None,
        parent: str | None = None,
    ) -> None:
        """
        Args:
            planned_amount: techo de la categoría, en céntimos ya convertidos
                por el borde.
            participants: quiénes cargan con esta categoría. Nunca vacío: su
                facturable se reparte entre ellos, así que una lista sin nadie
                deja dinero que no se le puede pedir a ningún miembro.
            method: Método de reparto del presupuesto entre los participants.
                None significa que no declara el suyo y hereda el del hogar.
        """
        # ================== Validadores ==================

        self._validate_amount(planned_amount)
        self._validate_non_empty_list(participants, "participants")
        self._validate_custom_method(
            method=method, custom_splits=custom_splits, participants=participants
        )

        # ================== Atributos ==================
        self.category = category
        self.planned_amount: int = planned_amount
        self.participants = [normalize_name(name) for name in participants]
        self._method = method
        self._custom_splits = custom_splits
        self._parent = parent

    @property
    def parent(self) -> str | None:
        return self._parent

    @property
    def method(self) -> MetodoReparto | None:
        return self._method

    @property
    def custom_splits(self) -> dict[str, int] | None:
        return self._custom_splits

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

    def set_split_method(self, method: MetodoReparto) -> None:
        """Cambia el método de reparto de la categoría.

        Si pasa a CUSTOM, exige que ya haya splits guardados: aquí no hay
        lectura diferida como en Household, se valida al vuelo.
        """
        self._validate_custom_method(
            method=method, custom_splits=self._custom_splits, participants=self.participants
        )
        self._method = method

    def set_custom_splits(self, custom_splits: dict[str, int]) -> None:
        """Declara los splits personalizados y deja el método en CUSTOM.

        Mismo patrón que Household.set_custom_splits: definirlos es la única
        razón para definirlos, así que fijan el método de una sola vez.
        """
        self._validate_custom_method(
            method=MetodoReparto.CUSTOM,
            custom_splits=custom_splits,
            participants=self.participants,
        )
        self._custom_splits = dict(custom_splits)
        self._method = MetodoReparto.CUSTOM

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

    def _validate_custom_method(
        self,
        method: MetodoReparto,
        custom_splits: dict[str, int] | None,
        participants: list[str],
    ):
        if method is MetodoReparto.CUSTOM:
            if not custom_splits:
                raise ValueError(
                    "Debe enviar el peso de cada miembro para este presupuesto si elige método CUSTOM"
                )

            if set(custom_splits) != set(participants):
                raise ValueError(
                    "weights debe tener un peso por participante: "
                    f"participantes {sorted(participants)}, pesos {sorted(custom_splits)}"
                )

            total = sum(custom_splits.values())
            if total != 10000:
                raise ValueError(
                    f"Los pesos deben sumar 100% (10000 basis points), suman {total}"
                )
        return
