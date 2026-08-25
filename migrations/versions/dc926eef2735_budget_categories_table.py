"""budget_categories table

Revision ID: dc926eef2735
Revises: 98f73f0ffae2
Create Date: 2026-07-06 18:19:43.636745

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "dc926eef2735"
down_revision: Union[str, Sequence[str], None] = "98f73f0ffae2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(#FIXME Quitar is_shared
        """
        CREATE TABLE budget_categories (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            household_period_id INTEGER NOT NULL REFERENCES household_periods(id),
            name VARCHAR(255) NOT NULL,
            is_shared BOOLEAN NOT NULL, 
            planned_amount INTEGER NOT NULL,
            parent_name VARCHAR(255) NULL,
            UNIQUE (household_period_id, name)
        );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE budget_categories;")
