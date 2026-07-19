from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class DebtEntry:
    """
    Registro de un pago de deuda.

    A diferencia de SavingEntry, no tiene scope ni signo negativo:
    la deuda siempre es personal y un pago siempre reduce el saldo.
    No hay retiro — corregir un pago erróneo es borrar la entry
    (DebtBucket.remove_payment), no añadir un movimiento contrario.

    id: identidad propia de la entry, para poder seleccionarla y borrarla.
    None = se genera al crear; un valor recibido se respeta tal cual
    (caso de rehidratación desde BD).
    """

    member_name: str
    amount_cents: int
    description: str = ""
    date: datetime = field(default_factory=datetime.now)
    id: UUID | None = None

    def __post_init__(self):
        if not self.member_name.strip():
            raise ValueError("member_name no puede estar vacío")
        if self.amount_cents <= 0:
            raise ValueError("amount_cents debe ser distinto a 0")
        if self.date > datetime.now():
            raise ValueError("La fecha no puede ser futura")
        if self.id is None:
            self.id = uuid4()
