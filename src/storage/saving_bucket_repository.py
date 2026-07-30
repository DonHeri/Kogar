import psycopg2
import psycopg2.extras
from uuid import UUID
from datetime import datetime
from src.models.saving_bucket import SavingBucket


class SavingBucketRepository:
    def __init__(self, db) -> None:
        psycopg2.extras.register_uuid()
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(
        self,
        saving_bucket: SavingBucket,
        household_id: int,
        member_ids: dict[str, int],
    ) -> UUID:
        """Inserta en saving_buckets y devuelve el id del bucket insertado."""
        id = saving_bucket.id
        bucket_name: str = saving_bucket.bucket_name
        goal_cents: int | None = saving_bucket.goal
        owners: list = saving_bucket.owners
        deadline: datetime | None = saving_bucket.deadline
        description: str = saving_bucket.description
        is_default: bool = saving_bucket.is_default
        self.cursor.execute(
            """
            INSERT INTO saving_buckets (id, household_id, bucket_name, goal_cents, deadline, description, is_default)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                id,
                household_id,
                bucket_name,
                goal_cents,
                deadline,
                description,
                is_default,
            ),
        )
        bucket_id = id

        for member in owners:
            self.cursor.execute(
                """
                INSERT INTO bucket_owners (bucket_id, member_id)
                VALUES (%s,%s)
                """,
                (bucket_id, member_ids[member]),
            )
        return bucket_id

    def find_with_owners(self, household_id: int) -> list[dict]:
        """JOIN entre saving_buckets, bucket_owners y members para que cada resultado incluya la lista de owners."""
        self.cursor.execute(
            """
            SELECT b.*,
                array_agg(m.full_name) AS owners
            FROM saving_buckets b
            JOIN bucket_owners bo ON bo.bucket_id = b.id
            JOIN members m ON m.id = bo.member_id
            WHERE b.household_id = (%s)
            GROUP BY b.id
            """,
            (household_id,),
        )
        return self.cursor.fetchall()
