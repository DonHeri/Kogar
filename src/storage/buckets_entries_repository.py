import psycopg2
import psycopg2.extras

from datetime import datetime
from src.models.saving_bucket import SavingBucket
from src.models.constants import SavingScope


class BucketsEntryRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(
        self,
        bucket_id: int,
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
