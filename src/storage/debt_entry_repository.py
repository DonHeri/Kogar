import psycopg2
import psycopg2.extras
from uuid import UUID
from src.models.debt_entry import DebtEntry


class DebtEntryRepository:
    def __init__(self, db) -> None:
        psycopg2.extras.register_uuid()
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(
        self,
        debt_entry: DebtEntry,
        debt_bucket_id: UUID,
        period_id: int,
        members_ids: dict[str, int],
    ) -> UUID:
        id = debt_entry.id
        member_id = members_ids[debt_entry.member_name]
        amount_cents = debt_entry.amount_cents
        description = debt_entry.description
        payment_date = debt_entry.date

        self.cursor.execute(
            """
            INSERT INTO debt_entries (id,debt_id,period_id, member_id, amount_cents, description, payment_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                id,
                debt_bucket_id,
                period_id,
                member_id,
                amount_cents,
                description,
                payment_date,
            ),
        )
        return id

    def find_by_bucket(self, debt_bucket_id: UUID):
        self.cursor.execute(
            """ 
            SELECT de.* FROM debt_entries de WHERE debt_id = (%s)
            """,
            (debt_bucket_id,),
        )
        return self.cursor.fetchall()
