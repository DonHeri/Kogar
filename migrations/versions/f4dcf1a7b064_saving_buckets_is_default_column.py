"""saving buckets is_default column

Revision ID: f4dcf1a7b064
Revises: 4b211967916d
Create Date: 2026-07-29 19:59:36.543007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4dcf1a7b064'
down_revision: Union[str, Sequence[str], None] = '4b211967916d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE saving_buckets
            ADD COLUMN is_default BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE saving_buckets
            DROP COLUMN is_default;
        """
    )
