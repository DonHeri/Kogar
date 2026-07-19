"""create period custom splits table

Revision ID: 3956286781da
Revises: dc926eef2735
Create Date: 2026-07-12 16:37:00.764319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3956286781da'
down_revision: Union[str, Sequence[str], None] = 'dc926eef2735'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE period_custom_splits (
            period_id INTEGER NOT NULL REFERENCES household_periods(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            percentage_basis_points INTEGER NOT NULL,
            PRIMARY KEY (period_id, member_id)
        );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(""" DROP TABLE period_custom_splits; """)
