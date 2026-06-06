"""add expenses table

Revision ID: e2abf4cbdcb8
Revises: cc90477bede4
Create Date: 2026-06-06 15:44:00.899231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2abf4cbdcb8'
down_revision: Union[str, Sequence[str], None] = 'cc90477bede4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """ 
        CREATE TABLE expenses (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            period_id INTEGER NOT NULL REFERENCES household_periods(id),
            payer_id INTEGER NOT NULL REFERENCES members(id),
            amount_cents INTEGER NOT NULL,
            category VARCHAR(100) NOT NULL,
            description VARCHAR(255) DEFAULT '',
            expense_date TIMESTAMP NOT NULL
        );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """ DROP TABLE expenses; """
    )
