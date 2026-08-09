"""drop is_shared from budget_categories

Compartida deja de ser un dato guardado: se deriva de cuántos participantes
tiene la categoría (`BudgetCategory.is_shared`). La columna no la leía nadie —
solo se escribía — así que ningún flujo se queda sin dato al quitarla.

Revision ID: b7c1e94a2f30
Revises: c9e4a17b3d20
Create Date: 2026-08-07

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c1e94a2f30"
down_revision: Union[str, Sequence[str], None] = "c9e4a17b3d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE budget_categories DROP COLUMN is_shared")


def downgrade() -> None:
    """Downgrade schema.

    Vuelve con DEFAULT TRUE porque el valor original ya no se puede reconstruir:
    era una copia de un dato que ahora vive en los participantes.
    """
    op.execute(
        "ALTER TABLE budget_categories ADD COLUMN is_shared BOOLEAN NOT NULL DEFAULT TRUE"
    )