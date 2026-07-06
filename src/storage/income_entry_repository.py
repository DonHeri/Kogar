import psycopg2
import psycopg2.extras

from src.models.income_entry import IncomeEntry


class IncomeEntryRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(self, income_entry: IncomeEntry, period_id: int, member_id: int) -> int:
        self.cursor.execute(
            """
            INSERT INTO income_entries
                (period_id, member_id, amount_cents, entry_date, description)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                period_id,
                member_id,
                income_entry.amount_cents,
                income_entry.date,
                income_entry.description,
            ),
        )
        return self.cursor.fetchone()["id"]
