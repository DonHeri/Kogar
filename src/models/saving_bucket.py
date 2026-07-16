from datetime import datetime, date
from math import ceil
from uuid import uuid4

from src.models.saving_bucket_entry import SavingBucketEntry


class SavingBucket:
    """
    Representa un Bucket de ahorro, que puede ser personal o compartido.
    Un Bucket tiene un objetivo de ahorro, un conjunto de miembros (owners) y un historial de movimientos (entries).
    Cada bucket tiene un identificador único (UUID) que lo distingue de otros buckets.

    deadline: fecha límite opcional; None = sin plazo fijo
    """

    def __init__(
        self,
        saving_bucket_name: str,
        owners: list,
        goal_cents: int | None = None,
        deadline: datetime | None = None,
        description: str = "",
    ) -> None:

        if goal_cents is not None:
            self._validate_valid_amount(goal_cents, "goal_cents")
        self._validate_non_empty_string(saving_bucket_name, "bucket_name")

        self._id = uuid4()
        self.bucket_name = saving_bucket_name
        self._goal_cents = goal_cents  # Un bucket puede ser de meta indefinida.

        self._owners = owners
        self.deadline = deadline
        self._entries: list[SavingBucketEntry] = []
        self.description = description

    @property
    def id(self):
        return self._id

    @property
    def owners(self):
        return self._owners

    @property
    def is_shared(self):
        return len(self.owners) > 1

    @property
    def goal(self) -> int | None:
        if self._goal_cents:
            return self._goal_cents

    @property
    def entries(self) -> list[SavingBucketEntry]:
        """Copia del historial de movimientos del bucket."""
        return list(self._entries)

    @property
    def balance(self) -> int:
        """Saldo total del bucket (suma de todas las entries)"""
        return sum(e.amount_cents for e in self._entries)

    @property
    def balance_by_member(self) -> dict[str, int]:
        """Saldo del bucket desglosado por miembro"""
        result = {owner: 0 for owner in self._owners}
        for entry in self._entries:
            result[entry.member_name] += entry.amount_cents
        return result

    @property
    def remaining_goal(self) -> int | None:
        """Cuánto falta para la meta. None si no hay meta. 0 si ya se alcanzó/superó."""
        if self.goal is None:
            return None

        return max(self.goal - self.balance, 0)

    @property
    def months_until_deadline(self) -> int | None:
        """Meses desde hoy hasta el deadline. None si no hay deadline.
        Si el deadline ya pasó, devuelve 1 (hace falta ya) — mismo patrón que
        DebtBucket.remaining_term_months + el max(...,1) de next_installment."""
        if self.deadline is None:
            return None

        now = datetime.now()
        months = (self.deadline.year - now.year) * 12 + (
            self.deadline.month - now.month
        )
        return max(months, 1)

    @property
    def required_monthly_contribution(self) -> int | None:
        """Cuánto haría falta aportar ESTE MES para llegar a la meta en el deadline.
        None si falta meta o deadline (sin los dos no hay "ritmo" que calcular)."""
        if self.goal is None or self.deadline is None:
            return None

        return ceil(self.remaining_goal / self.months_until_deadline)

    # ====== API PÚBLICA ======

    def deposit(
        self, amount_cents: int, member_name: str, date: datetime | None = None
    ):
        """
        Registra un depósito en el bucket. BucketEntry positiva.

        Args:
            amount_cents: Monto en céntimos, debe ser positivo
            member_name: Nombre del miembro que hace el depósito
            date: Fecha del depósito. Si no se indica, usa la fecha actual
        """
        self._validate_valid_amount(amount_cents, "amount_cents")
        self._validate_member_in_bucket(member_name)

        self._entries.append(
            SavingBucketEntry(
                amount_cents=amount_cents,
                member_name=member_name,
                date=date or datetime.now(),
            )
        )

    def withdraw(
        self, amount_cents: int, member_name: str, date: datetime | None = None
    ):
        """
        Registra un retiro del bucket. BucketEntry negativa.

        Args:
            amount_cents: Monto en céntimos, debe ser positivo
            member_name: Nombre del miembro que hace el retiro
            date: Fecha del retiro. Si no se indica, usa la fecha actual

        Raises:
            ValueError: Si el saldo disponible es insuficiente
        """
        self._validate_valid_amount(amount_cents, "amount_cents")
        self._validate_member_in_bucket(member_name)

        available = (
            self.balance_by_member.get(member_name, 0)
            if self.is_shared
            else self.balance
        )

        if amount_cents > available:
            raise ValueError(f"Saldo insuficiente. Disponible: {available} céntimos")

        self._entries.append(
            SavingBucketEntry(
                amount_cents=-amount_cents,
                member_name=member_name,
                date=date or datetime.now(),
            )
        )

    def get_period_deposits(self, start_date: date, end_date: date) -> int:
        """Neto depositado (o retirado, en negativo) en este bucket dentro del rango."""
        return sum(
            e.amount_cents
            for e in self._entries
            if start_date <= e.date.date() <= end_date
        )

    # ============================================================
    # Queries
    # ============================================================

    def __repr__(self):  # pragma: no cover
        return (
            f"SavingBucket(id={self._id}, name={self.bucket_name!r}, "
            f"shared={self.is_shared}, goal={self.goal}, balance={self.balance})"
        )

    def __str__(self):
        owners = ", ".join(o.title() for o in self._owners)
        tipo = "Compartido" if self.is_shared else "Personal"
        balance_eur = self.balance / 100

        if self.goal is not None:
            goal_eur = self.goal / 100
            pct = int(balance_eur / goal_eur * 100) if goal_eur else 0
            progreso = f"{balance_eur:.2f}€ / {goal_eur:.2f}€ ({pct}%)"
        else:
            progreso = f"{balance_eur:.2f}€ (sin meta)"

        lines = [
            f"[{tipo}] {self.bucket_name} — {owners}",
            f"  Progreso : {progreso}",
        ]
        if self.description:
            lines.append(f"  Desc.    : {self.description.capitalize()}")
        if self.deadline:
            lines.append(f"  Deadline : {self.deadline.strftime('%d/%m/%Y')}")

        return "\n".join(lines)

    # ====== Validadores ======

    def _validate_member_in_bucket(self, member_name: str):
        """Valida que un miembro pertenezca al bucket"""
        if member_name not in self._owners:
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
