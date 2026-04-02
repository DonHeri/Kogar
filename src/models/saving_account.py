from src.models.constants import SavingScope
from src.models.saving_entry import SavingEntry
from datetime import datetime


class SavingAccount:
    """
    Cuenta de ahorro individual de un miembro.

    Gestiona depósitos y retiros, distinguiendo entre ahorro
    personal y ahorro compartido con el hogar.

    El balance puede consultarse en tres formas:
    - balance_total    → todo el ahorro del miembro
    - balance_personal → solo ahorro de destino PERSONAL
    - balance_shared   → solo ahorro de destino SHARED

    Los retiros validan saldo disponible por destino —
    no se puede mezclar fondos automáticamente.
    """

    def __init__(self, member_name: str) -> None:
        self._validate_non_empty_string(member_name, "member_name")
        self.member_name = member_name
        self._entries: list[SavingEntry] = []

    # ====== OPERACIONES ======

    def deposit(
        self,
        destination: SavingScope,
        amount_cents: int,
        description: str = "",
        date: datetime | None = None,
    ) -> None:
        """
        Registra un depósito en la cuenta.

        Args:
            destination: PERSONAL o SHARED
            amount_cents: Monto en céntimos, debe ser positivo
            description: Descripción opcional del movimiento
            date: Fecha del depósito. Si no se indica, usa la fecha actual
        """
        self._validate_valid_amount(amount_cents, "amount_cents")

        self._entries.append(
            SavingEntry(
                amount_cents=amount_cents,
                destination=destination,
                description=description.lower().strip(),
                date=date or datetime.now(),
            )
        )

    def withdraw(
        self,
        destination: SavingScope,
        amount_cents: int,
        description: str = "",
        date: datetime | None = None,
    ) -> None:
        """
        Registra un retiro de la cuenta si hay saldo suficiente en el destino indicado.

        Args:
            destination: PERSONAL o SHARED — el retiro se hace del fondo indicado
            amount_cents: Monto en céntimos, debe ser positivo
            description: Descripción opcional del movimiento
            date: Fecha del retiro. Si no se indica, usa la fecha actual

        Raises:
            ValueError: Si el saldo disponible en el destino es insuficiente
        """
        self._validate_valid_amount(amount_cents, "amount_cents")

        available = (
            self.balance_personal
            if destination == SavingScope.PERSONAL
            else self.balance_shared
        )
        if amount_cents > available:
            raise ValueError(
                f"Saldo insuficiente en {destination.value}. "
                f"Disponible: {available} céntimos"
            )

        self._entries.append(
            SavingEntry(
                amount_cents=-amount_cents,
                destination=destination,
                description=description.lower().strip(),
                date=date or datetime.now(),
            )
        )

    # ====== BALANCES ======

    @property
    def balance_total(self) -> int:
        """Total ahorrado sumando personal y compartido"""
        return sum(entry.amount_cents for entry in self._entries)

    @property
    def balance_shared(self) -> int:
        """Total ahorrado en el fondo compartido del hogar"""
        return sum(
            entry.amount_cents
            for entry in self._entries
            if entry.destination == SavingScope.SHARED
        )

    @property
    def balance_personal(self) -> int:
        """Total ahorrado en el fondo personal"""
        return sum(
            entry.amount_cents
            for entry in self._entries
            if entry.destination == SavingScope.PERSONAL
        )

    # ====== HISTORIAL ======

    def get_history(self) -> list[SavingEntry]:
        """Retorna copia del historial completo de movimientos"""
        return self._entries.copy()

    # ====== QUERIES ======
    
    def get_monthly_summary(self, month: int, year: int) -> dict:
        """ Resumen del usuario en el mes actual """
        entries = [
            e for e in self._entries if e.date.month == month and e.date.year == year
        ]
        return {
            "personal": sum(
                e.amount_cents
                for e in entries
                if e.destination == SavingScope.PERSONAL
            ),
            "shared": sum(
                e.amount_cents
                for e in entries
                if e.destination == SavingScope.SHARED
            ),
        }

    # ====== VALIDACIONES ======

    def _validate_non_empty_string(self, value: str, field_name: str) -> None:
        if not value or not value.strip():
            raise ValueError(f"{field_name} no puede estar vacío")

    def _validate_valid_amount(self, value: int, field_name: str) -> None:
        if isinstance(value, bool):
            raise TypeError(f"{field_name} no puede ser booleano")
        if not isinstance(value, int):
            raise TypeError(f"{field_name} debe ser entero")
        if value <= 0:
            raise ValueError(f"{field_name} debe ser distinto a 0")
