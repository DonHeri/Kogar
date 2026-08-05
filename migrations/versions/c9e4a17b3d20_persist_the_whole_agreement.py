"""persist the whole agreement

El acuerdo del período son dos cosas y hasta ahora se guardaba media:

- Las contribuciones se guardaban ya sumadas por miembro, y las consultas
  necesitan el desglose por categoría. De un total no se puede volver al detalle,
  así que la tabla gana category_name en la clave.

- Los porcentajes aplicados no se guardaban en ninguna parte. No hace falta tabla
  nueva: period_custom_splits ya tiene la forma exacta, solo que su nombre decía
  "lo que el usuario definió". Pasa a ser "el porcentaje del período", que es lo
  mismo cuando el método es CUSTOM y además cubre PROPORTIONAL y EQUAL.

Revision ID: c9e4a17b3d20
Revises: b7c1d94e2af5
Create Date: 2026-08-05

"""

from typing import Sequence, Union

from alembic import op


revision: str = "c9e4a17b3d20"
down_revision: Union[str, Sequence[str], None] = "b7c1d94e2af5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE period_custom_splits RENAME TO period_percentages;
        """
    )

    # Las filas viejas guardan un total por miembro que ya no se puede repartir
    # entre categorías: se descartan en vez de inventarles una categoría.
    op.execute(""" DELETE FROM period_agreed_contributions; """)

    op.execute(
        """
        ALTER TABLE period_agreed_contributions
            DROP CONSTRAINT period_agreed_contributions_pkey;

        ALTER TABLE period_agreed_contributions
            ADD COLUMN category_name VARCHAR(100) NOT NULL;

        ALTER TABLE period_agreed_contributions
            ADD PRIMARY KEY (period_id, member_id, category_name);
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(""" DELETE FROM period_agreed_contributions; """)

    op.execute(
        """
        ALTER TABLE period_agreed_contributions
            DROP CONSTRAINT period_agreed_contributions_pkey;

        ALTER TABLE period_agreed_contributions
            DROP COLUMN category_name;

        ALTER TABLE period_agreed_contributions
            ADD PRIMARY KEY (period_id, member_id);
        """
    )

    op.execute(
        """
        ALTER TABLE period_percentages RENAME TO period_custom_splits;
        """
    )
