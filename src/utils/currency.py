# ====== CURRENCY CONVERSIONS ======
def to_cents(euros: float) -> int:
    """Convierte euros a céntimos (entrada del usuario → almacenamiento interno)"""
    return round(euros * 100)


def to_euros(cents: int) -> str:
    """Convierte céntimos a string formateado (almacenamiento interno → salida usuario)"""
    return f"{cents / 100:.2f}€"


# ====== PERCENTAGE CONVERSIONS ======
def to_percentage_basis(decimal_percentage: float) -> int:
    """
    Convierte porcentaje decimal a centésimas enteras

    Entrada: 53.57 (decimal) → Salida: 5357 (centésimas)
    Usado para almacenar porcentajes exactos sin pérdida de precisión
    """
    return round(decimal_percentage * 100)


def format_percentage(basis_points: int) -> str:
    """
    Convierte centésimas de porcentaje a string formateado

    Entrada: 5357 (centésimas) → Salida: "53.57%"
    Usado para mostrar porcentajes al usuario
    """
    return f"{basis_points / 100:.2f}%"


def format_percentage_float(basis_points: int) -> float:
    """
    devuelve pct en float
    """
    return basis_points / 100
