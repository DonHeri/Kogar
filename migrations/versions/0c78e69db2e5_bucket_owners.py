"""bucket_owners

Revision ID: 0c78e69db2e5
Revises: f3b062fc2c00
Create Date: 2026-07-03 18:10:56.572792

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0c78e69db2e5"
down_revision: Union[str, Sequence[str], None] = "f3b062fc2c00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE bucket_owners (
            bucket_id INTEGER NOT NULL REFERENCES saving_buckets(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            PRIMARY KEY (bucket_id, member_id)
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE bucket_owners;
        """
    )
