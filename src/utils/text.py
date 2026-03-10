"""
Utilidades para manejo de texto (normalización, formateo)
"""


def normalize_name(name: str) -> str:
    """
    Normaliza nombres para almacenamiento interno (lowercase).

    Similar a to_cents() para currency: formato interno consistente.

    Args:
        name: Nombre de entrada (puede tener espacios, mayúsculas)

    Returns:
        str: Nombre normalizado en minúsculas

    Raises:
        ValueError: Si el nombre está vacío o no es string

    Examples:
        >>> normalize_name("Amanda")
        'amanda'
        >>> normalize_name("  HERI  ")
        'heri'
    """
    if not isinstance(name, str):
        raise ValueError("El nombre debe ser texto")

    normalized = name.strip().lower()

    if not normalized:
        raise ValueError("Nombre no puede estar vacío")

    return normalized


def format_name(name: str) -> str:
    """
    Formatea nombre para presentación (Title Case).

    Similar a to_euros() para currency: formato de display.

    Args:
        name: Nombre normalizado (lowercase)

    Returns:
        str: Nombre formateado para display

    Examples:
        >>> format_name("amanda")
        'Amanda'
        >>> format_name("juan carlos")
        'Juan Carlos'
    """
    return name.title()
