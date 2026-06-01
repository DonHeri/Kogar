"""Helpers compartidos para los tests.

Funciones de fábrica y utilidades para construir objetos de dominio en los tests
sin acoplarlos a la API pública (CategoryLibrary, WorkflowManager, etc.). Añade aquí
cualquier helper reutilizable; no es exclusivo de Category.
"""

from src.models.category import AutoCalculatedCategory, Category


def make_category(
    name: str = "fijos",
    is_shared: bool = True,
    auto_calculated: bool = False,
) -> Category:
    """Fabrica un Category para tests sin pasar por CategoryLibrary.

    auto_calculated=True → AutoCalculatedCategory (como 'reserva').
    """
    if auto_calculated:
        return AutoCalculatedCategory(name, is_shared=is_shared)
    return Category(name, is_shared=is_shared)
