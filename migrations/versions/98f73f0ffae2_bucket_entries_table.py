"""bucket_entries table

Revision ID: 98f73f0ffae2
Revises: 0c78e69db2e5
Create Date: 2026-07-03 18:19:31.504471

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "98f73f0ffae2"
down_revision: Union[str, Sequence[str], None] = "0c78e69db2e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE bucket_entries (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            bucket_id UUID NOT NULL REFERENCES saving_buckets(id),
            period_id INTEGER NOT NULL REFERENCES household_periods(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            amount_cents INTEGER NOT NULL,
            entry_date TIMESTAMP NOT NULL
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE bucket_entries;
        """
    )
