"""create perior_agreed_contributions

Revision ID: cc90477bede4
Revises: fb7edb359f8b
Create Date: 2026-06-04 16:07:27.202462

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cc90477bede4"
down_revision: Union[str, Sequence[str], None] = "fb7edb359f8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """ 
        CREATE TABLE period_agreed_contributions (
            period_id INTEGER NOT NULL REFERENCES household_periods(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            amount_cents INTEGER NOT NULL,
            PRIMARY KEY (period_id,member_id)
        );
        """
    )
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(""" DROP TABLE period_agreed_contributions; """)
