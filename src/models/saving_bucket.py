from uuid import uuid4
from datetime import datetime
from src.models.constants import SavingScope
from src.models.bucket_entry import BucketEntry


class SavingBucket:
    def __init__(
        self,
        bucket_name: str,
        goal_cents: int,
        scope: SavingScope,
        owners: list,
        deadline: datetime | None = None,
        description: str = "",
    ) -> None:

        self._validate_valid_amount(goal_cents, "goal_cents")

        self._id = uuid4()
        self.bucket_name = bucket_name
        self._goal_cents = goal_cents
        self.scope = scope

        if scope == SavingScope.PERSONAL and len(owners) != 1:
            raise ValueError("Bucket Personal no puede tener más de 1 miembro")
        elif scope == SavingScope.SHARED and len(owners) < 2:
            raise ValueError("Bucket compartido no puede tener 1 miembro")

        self._owners = owners
        self.deadline = deadline
        self._entries: list[BucketEntry] = []
        self.description = description

    @property
    def goal(self) -> int:
        return self._goal_cents

    def deposit(self, amount_cents: int, member_name: str, date: datetime | None = None):
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
            BucketEntry(amount_cents=amount_cents, member_name=member_name, date=date or datetime.now())
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
            self.balance
            if self.scope == SavingScope.PERSONAL
            else self.balance_by_member.get(member_name, 0)
        )

        if amount_cents > available:
            raise ValueError(
                f"Saldo insuficiente. Disponible: {available} céntimos"
            )

        self._entries.append(
            BucketEntry(amount_cents=-amount_cents, member_name=member_name, date=date or datetime.now())
        )

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

    # ====== Validadores ======

    def _validate_member_in_bucket(self, member_name: str):
        """Valida que un miembro pertenezca al bucket"""
        if member_name not in self._owners:
            raise ValueError("Miembro no pertenece a este Bucket")

    def _validate_non_empty_string(self, value: str, field_name: str) -> None:
        if not value or not value.strip():
            raise ValueError(f"{field_name} no puede estar vacío")

    def _validate_valid_amount(self, value: int, field_name: str) -> None:
        if not isinstance(value, int):
            raise ValueError(f"{field_name} debe ser entero")
        if value <= 0:
            raise ValueError(f"{field_name} debe ser distinto a 0")
