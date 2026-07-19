import psycopg2
import psycopg2.extras

from datetime import datetime
from uuid import UUID


class SavingBucketEntryRepository:
    def __init__(self, db) -> None:
        psycopg2.extras.register_uuid()
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(
        self,
        bucket_id: UUID,
        period_id: int,
        member_id: int,
        amount_cents: int,
        entry_date: datetime,
    ) -> int:
        self.cursor.execute(
            """
            INSERT INTO bucket_entries (bucket_id, period_id, member_id, amount_cents, entry_date)
            VALUES (%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (bucket_id, period_id, member_id, amount_cents, entry_date),
        )
        return self.cursor.fetchone()["id"]

    def find_by_period(self, period_id) -> list[dict]:
        self.cursor.execute(
            """ SELECT * FROM bucket_entries WHERE period_id = (%s) """,
            (period_id,),
        )
        return self.cursor.fetchall()

    def find_by_bucket(self, bucket_id: UUID) -> list[dict]:
        """Historial completo de movimientos de un bucket, para reconstruir su balance."""
        self.cursor.execute(
            """ SELECT * FROM bucket_entries WHERE bucket_id = (%s) """,
            (bucket_id,),
        )
        return self.cursor.fetchall()
