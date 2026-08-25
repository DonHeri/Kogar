from dataclasses import dataclass
from src.models.constants import Phase, MetodoReparto


@dataclass
class Period:
    household_id: int
    year: int
    month: int
    status: Phase
    id: int | None = None
    method: MetodoReparto | None = None
