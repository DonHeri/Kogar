"""create household_periods table

Revision ID: fb7edb359f8b
Revises: 0c58b8e323b8
Create Date: 2026-05-27 12:36:30.368604

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fb7edb359f8b"
down_revision: Union[str, Sequence[str], None] = "0c58b8e323b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE household_periods (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES households(id),
            year SMALLINT NOT NULL,
            month SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
            status VARCHAR(20) NOT NULL CHECK (status IN ('registration', 'planning', 'month', 'closed')),
            method VARCHAR(20) CHECK (method IN ('proportional', 'equal', 'custom')),

            CONSTRAINT uq_period UNIQUE (household_id, month, year)
        );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(""" DROP TABLE household_periods """)
