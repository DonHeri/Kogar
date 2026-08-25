"""debt buckets table

Revision ID: 4b211967916d
Revises: c41f5eb5f894
Create Date: 2026-07-29 10:11:06.590295

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b211967916d"
down_revision: Union[str, Sequence[str], None] = "c41f5eb5f894"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """ 
        CREATE TABLE debt_buckets (
            id UUID PRIMARY KEY,
            household_id INTEGER NOT NULL REFERENCES households(id),
            bucket_name VARCHAR(255) NOT NULL,
            principal_cents INTEGER NOT NULL,
            member_id INTEGER NOT NULL REFERENCES members(id),
            installment_cents INTEGER NOT NULL,
            term_months INTEGER NULL,
            start_date TIMESTAMP NOT NULL 
        );
        """
    )

    op.execute("""DROP TABLE debt_entries""")

    op.execute(""" CREATE TABLE debt_entries(
            id UUID PRIMARY KEY,
            debt_id UUID NOT NULL REFERENCES debt_buckets(id),
            period_id INTEGER NOT NULL REFERENCES household_periods(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            amount_cents INTEGER NOT NULL,
            description VARCHAR(255) DEFAULT '',
            payment_date TIMESTAMP NOT NULL
        ) """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(""" DROP TABLE debt_entries; """)

    op.execute(""" 
               DROP TABLE debt_buckets;
               """)
    op.execute(
        """
        CREATE TABLE debt_entries (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            period_id INTEGER NOT NULL REFERENCES household_periods(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            amount_cents INTEGER NOT NULL,
            description VARCHAR(255) DEFAULT '',
            payment_date TIMESTAMP NOT NULL
        );
        """
    )
