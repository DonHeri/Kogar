import psycopg2
import psycopg2.extras
from uuid import UUID
from datetime import datetime

from src.models.debt_bucket import DebtBucket


class DebtBucketRepository:
    def __init__(self, db) -> None:
        psycopg2.extras.register_uuid()
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(
        self,
        debt_bucket: DebtBucket,
        household_id: int,
        members_ids: dict[str, int],
    ) -> UUID:
        """Inserta en debt_bucket y devuelve el id del bucket insertado."""

        id = debt_bucket.id
        bucket_name: str = debt_bucket.bucket_name
        principal_cents: int | None = debt_bucket.principal_cents
        owner: str = debt_bucket.owner
        owner_id: int = members_ids[owner]
        installment_cents: int = debt_bucket.installment_cents
        start_date: datetime = debt_bucket.start_date
        term_months: int | None = debt_bucket.term_months
        description: str = debt_bucket.description

        self.cursor.execute(
            """ 
            INSERT INTO debt_buckets(id,household_id,bucket_name,principal_cents,member_id,installment_cents,term_months,start_date,description)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                id,
                household_id,
                bucket_name,
                principal_cents,
                owner_id,
                installment_cents,
                term_months,
                start_date,
                description,
            ),
        )
        return id

    def find_by_household(self, household_id: int) -> list[dict]:
        """ """
        self.cursor.execute(
            """ 
            SELECT db.* FROM debt_buckets db WHERE db.household_id = (%s)
            """,
            (household_id,),
        )
        return self.cursor.fetchall()
