"""Errores del dominio.

Todos heredan de `ValueError` a propósito: el dominio ya lanzaba `ValueError`
por todas partes, y quien lo captura hoy sigue capturándolos sin cambiar nada.
Lo que añaden es tipo y datos — el borde puede distinguir qué regla se ha roto
y formatear el importe en euros sin tener que leer el texto del mensaje.
"""


class DomainError(ValueError):
    """Raíz de los errores de dominio. Nada la lanza directamente."""


class CeilingBelowChildrenError(DomainError):
    """El techo de una categoría no puede bajar de lo repartido en sus hijas."""

    def __init__(self, category: str, children_total_cents: int) -> None:
        self.category = category
        self.children_total_cents = children_total_cents
        super().__init__(
            f"La categoría {category} ya tiene {children_total_cents}¢ repartidos "
            "entre sus subcategorías: no puede bajar de ahí."
        )
