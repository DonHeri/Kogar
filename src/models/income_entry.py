from datetime import datetime
from dataclasses import dataclass, field
from src.models.constants import IncomeDestination, SavingScope


@dataclass
class IncomeEntry:
    member_name: str
    amount_cents: int
    date: datetime = field(default_factory=datetime.now)
    destination: IncomeDestination
    description: str = ""
    category_name: str | None = None
    scope: SavingScope | None = None

    def __post_init__(self):
        if self.amount_cents == 0:
            raise ValueError("amount_cents no puede ser 0")

        if (self.destination == IncomeDestination.SAVING) and self.scope is None:
            raise ValueError("scope no puede ser None si el destino es Ahorro")
        if (
            self.destination == IncomeDestination.CATEGORY
        ) and self.category_name is None:
            raise ValueError(
                "category_name no puede estar vacío si el destino es Category"
            )
