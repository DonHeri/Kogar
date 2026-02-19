def to_cents(euros: float) -> int:
    """Convierte entrada del usuario a céntimos"""
    return round(euros * 100)

def to_euros(cents: int) -> str:
    """Convierte céntimos a string para mostrar"""
    return f"{cents / 100:.2f}€"

def format_percentage(basis_points: int) -> str:
    """
    Formatea para mostrar al usuario
    5357 → "53.57%"
    """
    return f"{basis_points / 100:.2f}%"