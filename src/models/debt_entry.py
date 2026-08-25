from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DebtEntry:
    """
    Registro inmutable de un pago de deuda.

    A diferencia de SavingEntry, no tiene destination:
    la deuda siempre es personal y el dinero sale del hogar
    hacia un acreedor externo.

    El signo de amount_cents lo gestiona DebtAccount:
    - Pago → amount_cents positivo
    """

    amount_cents: int
    description: str = ""
    date: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.amount_cents == 0:
            raise ValueError("amount_cents no puede ser 0")
        if self.date > datetime.now():
            raise ValueError("La fecha no puede ser futura")
