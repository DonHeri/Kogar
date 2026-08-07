from datetime import datetime, date
from math import ceil
from uuid import uuid4, UUID

from src.models.debt_entry import DebtEntry


class DebtBucket:
    """
    Deuda personal: principal + cuota real de la financiación del usuario. Sin interés (v1).

    La cuota la fija el usuario (fuente de verdad = su papel del banco). El número de cuotas
    restantes NO se almacena: se deriva del saldo y la cuota. El cálculo del programa solo
    sirve como estimación de la próxima cuota, nunca sustituye a lo que declara el usuario.

    FUTURO (aparcado): deuda compartida entre varios owners → reparto en settlement. Hoy la deuda es estrictamente personal: un único owner.
    """

    def __init__(
        self,
        debt_bucket_name: str,
        principal_cents: int,
        owner: str,
        installment_cents: int,
        id: UUID | None = None,
        start_date: datetime | None = None,
        term_months: int | None = None,  # Meses de cuota
        description: str = "",
    ):
        self._validate_non_empty_string(debt_bucket_name, "bucket_name")
        self._validate_valid_amount(principal_cents, "principal_cents")
        self._validate_non_empty_string(owner, "owner")
        self._validate_valid_amount(installment_cents, "installment_cents")
        if id is None:
            id = uuid4()

        self._id = id
        self.bucket_name = debt_bucket_name
        self.principal_cents = principal_cents
        self._owner = owner
        self._installment_cents = installment_cents
        self.start_date = start_date if start_date else datetime.today()
        self._entries: list[DebtEntry] = []
        self.term_months = term_months
        self.description = description

    @property
    def id(self):
        return self._id

    @property
    def owner(self) -> str:
        """Responsable de la deuda (personal → un único owner)."""
        return self._owner

    @property
    def installment_cents(self) -> int:
        """Cuota mensual fija que declaró el usuario (fuente de verdad)."""
        return self._installment_cents

    @property
    def entries(self) -> list[DebtEntry]:
        """Copia del historial de pagos del bucket."""
        return list(self._entries)

    @property
    def total_paid(self) -> int:
        """Pagado de la deuda (Σ pagos)."""
        return sum(entry.amount_cents for entry in self._entries)

    @property
    def remaining_balance(self) -> int:
        """Restante por pagar."""
        return self.principal_cents - self.total_paid

    @property
    def is_closed(self) -> bool:
        return self.total_paid >= self.principal_cents

    @property
    def next_installment(self) -> int:
        """Estimación de la próxima cuota: la cuota del usuario, salvo el último pago,
        que se ajusta al saldo si es menor. Es lo que se espera pagar, no una obligación."""
        return min(self._installment_cents, self.remaining_balance)

    @property
    def remaining_installments(self) -> int:
        """Nº de cuotas que faltan (derivado, para mostrar). ceil: un resto menor que la
        cuota exige un pago extra final más pequeño."""
        if self.remaining_balance <= 0:
            return 0
        return ceil(self.remaining_balance / self._installment_cents)

    def get_period_balance(self, start_date: date, end_date: date) -> dict[str, int]:
        """Balance del bucket en el período [start_date, end_date): cuota, pagado y restante.

        `remaining` sale negativo cuando se paga por encima de la cuota del mes, y su
        magnitud es cuánto se ha adelantado. No se corta en 0 a propósito: el sobrepago
        está permitido y ese número es la única forma de verlo.
        """
        entries = [e for e in self._entries if start_date <= e.date.date() < end_date]
        committed = self.next_installment
        paid = sum(e.amount_cents for e in entries)
        remaining = committed - paid
        return {"committed": committed, "paid": paid, "remaining": remaining}

    def set_installment(self, amount_cents: int) -> None:
        """Fija la cuota mensual real del usuario (fuente de verdad)."""
        self._validate_valid_amount(amount_cents, "amount_cents")
        self._installment_cents = amount_cents

    def set_term_months(self, months: int):
        """
        Permite settear meses de cuota.
        Se asumirá que son meses restantes.
        """
        self._validate_valid_amount(months, "months")
        self.term_months = months

    def pay(
        self,
        amount_cents: int,
        member_name: str,
        description: str | None = None,
        date: datetime | None = None,
        id: UUID | None = None,
    ):
        """
        Registra dinero contra la deuda. Un pago normal y adelantar dinero son lo mismo:
        cualquier importe positivo reduce el saldo (y con él las cuotas restantes). No hay
        tope; pagar de más se permite (decisión T1).

        Args:
            amount_cents: Monto en céntimos, debe ser positivo
            member_name: Nombre del miembro que paga (debe ser el owner)
            date: Fecha del pago. Si no se indica, usa la fecha actual
        """
        self._validate_valid_amount(amount_cents, "amount_cents")
        self._validate_member_is_owner(member_name)

        self._entries.append(
            DebtEntry(
                member_name=member_name,
                amount_cents=amount_cents,
                date=date or datetime.now(),
                id=id,
            )
        )

    def remove_payment(self, entry_id) -> None:
        """Elimina un pago erróneo por id. Única forma de deshacer un pago:
        no existe retiro simétrico, se corrige borrando el registro."""
        before_total = len(self._entries)
        self._entries = [e for e in self._entries if e.id != entry_id]
        after_total = len(self._entries)

        if before_total == after_total:
            raise ValueError("No se ha encontrado el id")

    # ====== Validadores ======

    def _validate_member_is_owner(self, member_name: str):
        """Valida que quien paga es el owner de la deuda."""
        if member_name != self._owner:
            raise ValueError("Miembro no pertenece a este Bucket")

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
