from src.models.constants import SavingScope
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class SavingEntry:
    """
    Registro inmutable de un movimiento en una cuenta de ahorro.

    El signo de amount_cents lo gestiona SavingAccount:
    - Depósito → amount_cents positivo
    - Retiro   → amount_cents negativo

    SavingEntry solo valida que recibe un valor válido, no decide la naturaleza del movimiento.
    """

    amount_cents: int
    destination: SavingScope
    description: str = ""
    date: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.amount_cents == 0:
            raise ValueError("amount_cents no puede ser 0")
        if self.date > datetime.now():
            raise ValueError("La fecha no puede ser futura")