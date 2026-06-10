"""replace year/month with start_date/end_date on household_periods

Revision ID: a1b2c3d4e5f6
Revises: fcf1ba762222
Create Date: 2026-06-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "fcf1ba762222"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE household_periods
            ADD COLUMN start_date DATE,
            ADD COLUMN end_date DATE;

        UPDATE household_periods
            SET start_date = make_date(year, month, 1)
            WHERE start_date IS NULL;

        ALTER TABLE household_periods
            ALTER COLUMN start_date SET NOT NULL;

        ALTER TABLE household_periods
            DROP CONSTRAINT uq_period,
            DROP COLUMN year,
            DROP COLUMN month;

        ALTER TABLE household_periods
            ADD CONSTRAINT uq_period_start UNIQUE (household_id, start_date);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE household_periods
            ADD COLUMN year SMALLINT,
            ADD COLUMN month SMALLINT;

        UPDATE household_periods
            SET year  = EXTRACT(YEAR  FROM start_date)::SMALLINT,
                month = EXTRACT(MONTH FROM start_date)::SMALLINT;

        ALTER TABLE household_periods
            ALTER COLUMN year  SET NOT NULL,
            ALTER COLUMN month SET NOT NULL,
            ADD CONSTRAINT uq_period UNIQUE (household_id, month, year);

        ALTER TABLE household_periods
            DROP CONSTRAINT uq_period_start,
            DROP COLUMN start_date,
            DROP COLUMN end_date;
        """
    )
