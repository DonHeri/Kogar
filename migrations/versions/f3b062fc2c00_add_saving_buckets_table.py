"""add saving_buckets table

Revision ID: f3b062fc2c00
Revises: 13439a9dd690
Create Date: 2026-07-03 10:47:45.103875

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3b062fc2c00"
down_revision: Union[str, Sequence[str], None] = "13439a9dd690"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE saving_buckets (
            id UUID PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES households(id),
            bucket_name VARCHAR(255) NOT NULL,
            goal_cents INT NOT NULL,
            scope VARCHAR(50) NOT NULL,
            deadline TIMESTAMP,
            description TEXT
        );
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE saving_buckets;
    """)
