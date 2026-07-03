"""add saving_entries table

Revision ID: 13439a9dd690
Revises: da8430e8a4bf
Create Date: 2026-07-03 09:29:49.209601

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "13439a9dd690"
down_revision: Union[str, Sequence[str], None] = "da8430e8a4bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
            CREATE TABLE saving_entries (
                id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                period_id INTEGER NOT NULL REFERENCES household_periods(id),
                member_id INTEGER NOT NULL REFERENCES members(id),
                amount_cents INTEGER NOT NULL,
                scope VARCHAR(255) NOT NULL, 
                description VARCHAR(255) DEFAULT '',
                saving_date TIMESTAMP NOT NULL
            );
            """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(""" DROP TABLE saving_entries; """)
