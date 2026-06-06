"""add expense_participants table

Revision ID: fcf1ba762222
Revises: e2abf4cbdcb8
Create Date: 2026-06-06 15:57:39.449150

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fcf1ba762222"
down_revision: Union[str, Sequence[str], None] = "e2abf4cbdcb8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """ 
        CREATE TABLE expense_participants (
            expense_id INTEGER NOT NULL REFERENCES expenses(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            weight SMALLINT,
            PRIMARY KEY (expense_id, member_id)
        );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(""" DROP TABLE expense_participants; """)
