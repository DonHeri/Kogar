"""
Utilidades para manejo de texto (normalización, formateo)
"""


def normalize_name(name: str) -> str:
    """
    Normaliza nombres para almacenamiento interno (lowercase).

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
    """
    
    return name.title()
