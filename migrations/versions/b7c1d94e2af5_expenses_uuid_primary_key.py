"""expenses uuid primary key

Revision ID: b7c1d94e2af5
Revises: f4dcf1a7b064
Create Date: 2026-07-31 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c1d94e2af5"
down_revision: Union[str, Sequence[str], None] = "f4dcf1a7b064"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    expenses.id pasa de INTEGER IDENTITY a UUID, para que el gasto tenga
    identidad propia desde el dominio (igual que debt_entries y bucket_entries)
    y se pueda seleccionar, corregir o borrar uno concreto.

    expense_participants.expense_id lo sigue por la FK. Las filas existentes
    conservan su relación: se genera un UUID por gasto y se propaga antes de
    tirar las columnas viejas.
    """
    op.execute("""ALTER TABLE expenses ADD COLUMN new_id UUID""")
    op.execute("""UPDATE expenses SET new_id = gen_random_uuid()""")
    op.execute("""ALTER TABLE expenses ALTER COLUMN new_id SET NOT NULL""")

    op.execute("""ALTER TABLE expense_participants ADD COLUMN new_expense_id UUID""")
    op.execute(
        """
        UPDATE expense_participants ep
        SET new_expense_id = e.new_id
        FROM expenses e
        WHERE ep.expense_id = e.id
        """
    )

    op.execute("""ALTER TABLE expense_participants DROP CONSTRAINT expense_participants_pkey""")
    op.execute("""ALTER TABLE expense_participants DROP COLUMN expense_id""")
    op.execute(
        """ALTER TABLE expense_participants RENAME COLUMN new_expense_id TO expense_id"""
    )
    op.execute("""ALTER TABLE expense_participants ALTER COLUMN expense_id SET NOT NULL""")

    op.execute("""ALTER TABLE expenses DROP CONSTRAINT expenses_pkey""")
    op.execute("""ALTER TABLE expenses DROP COLUMN id""")
    op.execute("""ALTER TABLE expenses RENAME COLUMN new_id TO id""")
    op.execute("""ALTER TABLE expenses ADD PRIMARY KEY (id)""")

    op.execute(
        """
        ALTER TABLE expense_participants
            ADD PRIMARY KEY (expense_id, member_id),
            ADD FOREIGN KEY (expense_id) REFERENCES expenses(id)
        """
    )


def downgrade() -> None:
    """Downgrade schema. Los id vuelven a ser enteros nuevos: los UUID se pierden."""
    op.execute("""ALTER TABLE expenses ADD COLUMN old_id INTEGER GENERATED ALWAYS AS IDENTITY""")

    op.execute("""ALTER TABLE expense_participants ADD COLUMN old_expense_id INTEGER""")
    op.execute(
        """
        UPDATE expense_participants ep
        SET old_expense_id = e.old_id
        FROM expenses e
        WHERE ep.expense_id = e.id
        """
    )

    op.execute("""ALTER TABLE expense_participants DROP CONSTRAINT expense_participants_pkey""")
    op.execute("""ALTER TABLE expense_participants DROP COLUMN expense_id""")
    op.execute(
        """ALTER TABLE expense_participants RENAME COLUMN old_expense_id TO expense_id"""
    )
    op.execute("""ALTER TABLE expense_participants ALTER COLUMN expense_id SET NOT NULL""")

    op.execute("""ALTER TABLE expenses DROP CONSTRAINT expenses_pkey""")
    op.execute("""ALTER TABLE expenses DROP COLUMN id""")
    op.execute("""ALTER TABLE expenses RENAME COLUMN old_id TO id""")
    op.execute("""ALTER TABLE expenses ADD PRIMARY KEY (id)""")

    op.execute(
        """
        ALTER TABLE expense_participants
            ADD PRIMARY KEY (expense_id, member_id),
            ADD FOREIGN KEY (expense_id) REFERENCES expenses(id)
        """
    )
