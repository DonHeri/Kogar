from datetime import datetime
from uuid import UUID, uuid4

from src.models.category import Category
from src.models.finance_calculator import FinanceCalculator
from src.utils.currency import to_euros
from src.utils.text import normalize_name


class Expense:
    """Representa un gasto realizado por un miembro en una categoría específica"""

    def __init__(
        self,
        member: str,
        category: Category,
        amount_cents: int,
        participants: list[str],
        description: str = "",
        weights: dict[str, int] | None = None,
        date: datetime | None = None,
        id: UUID | None = None,
    ) -> None:
        """
        Crea un gasto con validaciones básicas

        Args:
            member: Nombre del miembro que pagó
            category: Objeto Category del gasto (ya resuelto por WorkflowManager)
            amount_cents: Monto en céntimos (int)
            participants: quiénes cargan con el gasto. Nunca vacío: un gasto sin
                participantes no tiene reparto posible, así que declararlo así es
                un error de quien llama, no un caso a interpretar. Quien decide
                la lista es el borde (CLI, API), nunca el dominio.
            description: Descripción opcional del gasto
            weights: cuánto carga cada participante, en basis points ×100
                (100% = 10000). Un peso por participante y ni uno más. None
                significa a partes iguales, que es lo único que se deduce de la
                lista de participantes sin mirar nada más. El método de reparto
                (EQUAL, PROPORTIONAL, CUSTOM) NO vive aquí: es un concepto del
                borde, que lo traduce a pesos antes de construir el gasto.
            id: identidad propia del gasto, para poder seleccionarlo, corregirlo
                o borrarlo. None = se genera al crear; un valor recibido se
                respeta tal cual (caso de rehidratación desde BD).

        Raises:
            ValueError: Si member está vacío, amount no es positivo,
                participants viene vacío, o los pesos no cubren exactamente a
                los participantes sumando 10000
        """
        self._validate_non_empty_string(member, "member")
        self._validate_positive_amount(amount_cents, "amount")
        self._validate_non_empty_list(participants, "participants")

        self.id: UUID = id if id is not None else uuid4()
        self._date: datetime = date or datetime.now()
        self.member = normalize_name(member)  # stored as lowercase
        self.category = category
        self._amount_cents: int = amount_cents
        self.participants = participants
        self.weights = self._resolve_weights(participants, weights)
        self.description = description

    # ====== PROPERTIES ======

    @property
    def is_shared(self):
        return len(self.participants) > 1

    @property
    def is_personal(self):
        return len(self.participants) == 1 and self.participants[0] == self.member

    @property
    def amount(self) -> int:
        return self._amount_cents

    @property
    def date(self) -> datetime:
        return self._date

    # ====== API PÚBLICA ======

    def add_participant(self, name):
        name = normalize_name(name)
        self.participants.append(name)

    def is_same_month(self, other_date: datetime | None = None) -> bool:
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

    def is_same_year(self, other_date: datetime | None = None) -> bool:
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
        return f"Expense({self.member}, {self.category.name}, {to_euros(self.amount)}, {formatted_date})"

    # ====== VALIDACIONES ======
    def _validate_non_empty_string(self, value: str, field_name: str) -> None:
        """Valida que un string no esté vacío"""
        if not value or not value.strip():
            raise ValueError(f"{field_name} no puede estar vacío")

    def _validate_positive_amount(self, value: int, field_name: str) -> None:
        """Valida que un monto sea positivo"""
        if value <= 0:
            raise ValueError(f"{field_name} debe ser positivo")

    def _validate_non_empty_list(self, value: list, field_name: str) -> None:
        """Valida que una lista tenga al menos un elemento"""
        if not value:
            raise ValueError(f"{field_name} no puede estar vacío")

    def _resolve_weights(
        self, participants: list[str], weights: dict[str, int] | None
    ) -> dict[str, int]:
        """Devuelve el peso de cada participante, validado.

        Sin pesos, el reparto es a partes iguales: es lo único que la lista de
        participantes dice por sí sola. Con pesos, tienen que cubrir a esos
        participantes exactamente y sumar 10000 — si no, el reparto dejaría
        dinero sin asignar y el settlement descuadraría en silencio.
        """
        if weights is None:
            return FinanceCalculator.calculate_equal_percentage(
                {name: 1 for name in participants}
            )

        if set(weights) != set(participants):
            raise ValueError(
                "weights debe tener un peso por participante: "
                f"participantes {sorted(participants)}, pesos {sorted(weights)}"
            )

        total = sum(weights.values())
        if total != 10000:
            raise ValueError(
                f"Los pesos deben sumar 100% (10000 basis points), suman {total}"
            )

        return weights
