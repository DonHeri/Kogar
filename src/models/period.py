from dataclasses import dataclass
from datetime import date

from src.models.constants import Phase, MetodoReparto


@dataclass
class Period:
    household_id: int
    start_date: date
    status: Phase
    id: int | None = None
    end_date: date | None = None
    method: MetodoReparto | None = None
