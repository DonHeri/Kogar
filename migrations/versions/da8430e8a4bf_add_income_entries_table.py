"""add income_entries table

Revision ID: da8430e8a4bf
Revises: d8558a6ed736
Create Date: 2026-07-01 10:07:22.723462

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "da8430e8a4bf"
down_revision: Union[str, Sequence[str], None] = "d8558a6ed736"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """ 
        CREATE TABLE income_entries (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            period_id INTEGER NOT NULL REFERENCES household_periods(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            amount_cents INTEGER NOT NULL ,
            entry_date TIMESTAMP NOT NULL,
            description VARCHAR(255) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(""" DROP TABLE income_entries; """)
