import psycopg2
import psycopg2.extras


class DebtRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(
        self,
        period_id: int,
        member_id: int,
        amount_cents: int,
        payment_date,
        description: str = "",
    ) -> int:
        self.cursor.execute(
            """
            INSERT INTO debt_entries (period_id, member_id, amount_cents, description, payment_date)
            VALUES (%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (period_id, member_id, amount_cents, description, payment_date),
        )
        return self.cursor.fetchone()["id"]

    def find_by_period(self, period_id) -> list[dict]:
        self.cursor.execute(
            """ SELECT * FROM debt_entries WHERE period_id = (%s) """,
            (period_id,),
        )
        return self.cursor.fetchall()
