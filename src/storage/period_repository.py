import psycopg2.extras

from src.models.constants import Phase, MetodoReparto
from src.models.period import Period


class PeriodRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = self.db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def create(self, period: Period) -> int:
        self.cursor.execute(
            """
            INSERT INTO household_periods (household_id, year, month, status, method)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                period.household_id,
                period.year,
                period.month,
                period.status.value,
                period.method.value if period.method else None,
            ),
        )
        return self.cursor.fetchone()["id"]

    def get_by_id(self, period_id: int) -> Period | None:
        self.cursor.execute(
            "SELECT * FROM household_periods WHERE id = %s", (period_id,)
        )
        row = self.cursor.fetchone()
        return self._to_period(row) if row else None

    def get_current(self, household_id: int) -> Period | None:
        self.cursor.execute(
            """
            SELECT * FROM household_periods
            WHERE household_id = %s AND status != 'closed'
            ORDER BY year DESC, month DESC
            LIMIT 1
            """,
            (household_id,),
        )
        row = self.cursor.fetchone()
        return self._to_period(row) if row else None

    def update_status(self, period_id: int, status: Phase) -> None:
        self.cursor.execute(
            "UPDATE household_periods SET status = %s WHERE id = %s",
            (status.value, period_id),
        )

    def update_method(self, period_id: int, method: MetodoReparto) -> None:
        self.cursor.execute(
            "UPDATE household_periods SET method = %s WHERE id = %s",
            (method.value, period_id),
        )

    def _to_period(self, row: dict) -> Period:
        return Period(
            id=row["id"],
            household_id=row["household_id"],
            year=row["year"],
            month=row["month"],
            status=Phase(row["status"]),
            method=MetodoReparto(row["method"]) if row["method"] else None,
        )
