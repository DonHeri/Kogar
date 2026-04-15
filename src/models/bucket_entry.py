from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BucketEntry:
    """
    Registro inmutable de un movimiento en un Bucket de ahorro.

    El signo de amount_cents lo gestiona BucketTracker:
    - Depósito → amount_cents positivo
    - Retiro   → amount_cents negativo

    BucketEntry solo valida que recibe un valor válido, no decide la naturaleza del movimiento.
    """

    amount_cents: int
    member_name:str
    date: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.amount_cents == 0:
            raise ValueError("amount_cents no puede ser 0")
        if self.date > datetime.now():
            raise ValueError("La fecha no puede ser futura")
        if not self.member_name or not self.member_name.strip():
            raise ValueError(f"Nombre no puede estar vacío")