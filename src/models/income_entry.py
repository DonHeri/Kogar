from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class IncomeEntry:
    member_name: str
    amount_cents: int
    date: datetime = field(default_factory=datetime.now)
    description: str = ""

    def __post_init__(self):
        if self.amount_cents <= 0:
            raise ValueError("amount_cents no puede ser 0")
