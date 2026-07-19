"""saving_buckets: drop scope, goal_cents nullable

Todo el ahorro vive en buckets: personal/compartido se deriva de owners
(bucket_owners), no de una columna scope. Un bucket puede no tener meta
(colchón / ahorro libre) -> goal_cents pasa a nullable.

Revision ID: c41f5eb5f894
Revises: 3956286781da
Create Date: 2026-07-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c41f5eb5f894"
down_revision: Union[str, Sequence[str], None] = "3956286781da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE saving_buckets
            DROP COLUMN scope,
            ALTER COLUMN goal_cents DROP NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE saving_buckets
            ADD COLUMN scope VARCHAR(50) NOT NULL DEFAULT 'personal',
            ALTER COLUMN goal_cents SET NOT NULL;
    """)
