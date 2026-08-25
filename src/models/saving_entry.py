from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class SavingEntry:
    """
    Registro inmutable de un movimiento en una cuenta de ahorro.

    El signo de amount_cents lo gestiona SavingAccount:
    - Depósito → amount_cents positivo
    - Retiro   → amount_cents negativo

    SavingEntry solo valida que recibe un valor válido, no decide la naturaleza del movimiento.
    """

    member_name: str
    amount_cents: int

    description: str = ""
    date: datetime = field(default_factory=datetime.now)
    id: UUID | None = None

    def __post_init__(self):
        if not self.member_name.strip():
            raise ValueError("member_name no puede estar vacío")
        if self.amount_cents == 0:
            raise ValueError("amount_cents no puede ser 0")
        if self.date > datetime.now():
            raise ValueError("La fecha no puede ser futura")
        if self.id is None:
            self.id = uuid4()
