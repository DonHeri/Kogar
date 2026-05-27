"""create households and members tables

Revision ID: 0c58b8e323b8
Revises:
Create Date: 2026-05-27 11:24:10.241123

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0c58b8e323b8"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Household
    op.execute(
        """ 
        CREATE TABLE households (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            status BOOLEAN DEFAULT TRUE
        );
        """
    )

    # Members
    op.execute(
        """ 
        CREATE TABLE members (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            monthly_income INTEGER NOT NULL, 
            status BOOLEAN DEFAULT TRUE,
            household_id INTEGER NOT NULL REFERENCES households(id)
        );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Members
    op.execute(
        """ 
        DROP TABLE members;
        """
    )

    # Household
    op.execute(
        """ 
        DROP TABLE households;
        """
    )
