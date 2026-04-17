from datetime import datetime

from src.models.debt_entry import DebtEntry


class DebtAccount:
    """
    Cuenta de deuda individual de un miembro.

    Gestiona pagos de deuda personal. A diferencia de SavingAccount:
    - No tiene destination (PERSONAL/SHARED) — la deuda siempre es personal
    - No tiene retiros — un pago de deuda no se "deshace"
    - El balance representa lo pagado, no lo que queda por pagar

    El compromiso (cuánto se comprometió a pagar este mes) vive fuera,
    en Household._member_debts. DebtAccount solo registra la ejecución.
    """

    def __init__(self, member_name: str) -> None:
        self._validate_non_empty_string(member_name, "member_name")
        self.member_name = member_name
        self._entries: list[DebtEntry] = []

    # ====== OPERACIONES ======

    def pay(
        self,
        amount_cents: int,
        description: str = "",
        date: datetime | None = None,
    ) -> None:
        """
        Registra un pago de deuda.

        Args:
            amount_cents: Monto en céntimos, debe ser positivo
            description: Descripción opcional del pago
            date: Fecha del pago. Si no se indica, usa la fecha actual
        """
        self._validate_valid_amount(amount_cents, "amount_cents")

        self._entries.append(
            DebtEntry(
                amount_cents=amount_cents,
                description=description.lower().strip(),
                date=date or datetime.now(),
            )
        )

    # ====== BALANCES ======

    @property
    def total_paid(self) -> int:
        """Total pagado de deuda"""
        return sum(entry.amount_cents for entry in self._entries)

    # ====== HISTORIAL ======

    def get_history(self) -> list[DebtEntry]:
        """Retorna copia del historial completo de pagos"""
        return self._entries.copy()

    # ====== QUERIES ======

    def get_monthly_summary(self, month: int, year: int) -> dict:
        """Resumen de pagos de deuda del mes"""
        entries = [
            e for e in self._entries if e.date.month == month and e.date.year == year
        ]
        return {
            "paid": sum(e.amount_cents for e in entries),
            "payments_count": len(entries),
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
