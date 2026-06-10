from datetime import date

import psycopg2.extras

from src.models.constants import Phase, MetodoReparto
from src.models.period import Period


class PeriodRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = self.db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(self, period: Period) -> int:
        self.cursor.execute(
            """
            INSERT INTO household_periods (household_id, start_date, status, method)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                period.household_id,
                period.start_date,
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
            ORDER BY start_date DESC
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

    def update_end_date(self, period_id: int, end_date: date) -> None:
        self.cursor.execute(
            "UPDATE household_periods SET end_date = %s WHERE id = %s",
            (end_date, period_id),
        )

    def _to_period(self, row: dict) -> Period:
        return Period(
            id=row["id"],
            household_id=row["household_id"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            status=Phase(row["status"]),
            method=MetodoReparto(row["method"]) if row["method"] else None,
        )

    def save_agreed_contributions(
        self, period_id: int, contributions: dict[str, int]
    ) -> None:
        "Guarda los acuerdos de planning para un período. Si ya existen, sobreescribe los importes."

        for full_name, amount_cents in contributions.items():
            self.cursor.execute(
                " SELECT id FROM members WHERE full_name = %s ", (full_name,)
            )
            row = self.cursor.fetchone()
            if row is None:
                raise ValueError(f"Miembro {full_name} no está en la base de datos ")
            self.cursor.execute(
                """ 
                INSERT INTO period_agreed_contributions(period_id,member_id,amount_cents)
                VALUES (%s,%s,%s)
                ON CONFLICT (period_id,member_id)
                DO UPDATE SET amount_cents = EXCLUDED.amount_cents
                """,
                (period_id, row["id"], amount_cents),
            )

    def get_agreed_contributions(self, period_id: int) -> dict[str, int]:
        "Lee los acuerdos guardados de un período. Devuelve {nombre: amount_cents}."
        self.cursor.execute(
            """ 
            SELECT m.full_name, pac.amount_cents
            FROM period_agreed_contributions pac
            INNER JOIN members m ON m.id = pac.member_id
            WHERE pac.period_id = %s
            """,
            (period_id,),
        )
        return {row["full_name"]: row["amount_cents"] for row in self.cursor.fetchall()}
