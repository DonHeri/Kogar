"""add debt_entries table

Revision ID: d8558a6ed736
Revises: a1b2c3d4e5f6
Create Date: 2026-06-18 09:59:18.985486

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8558a6ed736"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE debt_entries (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            period_id INTEGER NOT NULL REFERENCES household_periods(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            amount_cents INTEGER NOT NULL,
            description VARCHAR(255) DEFAULT '',
            payment_date TIMESTAMP NOT NULL
        );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(""" DROP TABLE debt_entries; """)
