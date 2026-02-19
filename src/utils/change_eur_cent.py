def to_cents(euros: float) -> int:
    """Convierte entrada del usuario a céntimos"""
    return round(euros * 100)

def to_euros(cents: int) -> str:
    """Convierte céntimos a string para mostrar"""
    return f"{cents / 100:.2f}€"