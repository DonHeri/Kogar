class Participante:
    """Representa a una persona con su ingreso base mensual."""

    def __init__(self, name: str):

        if not name or not name.strip():
            raise ValueError("Nombre no puede estar vacío")

        # ====== Atributos ======
        self.name: str = name
        self.monthly_income: float = 0.0

    # Suma ingresos
    def add_incomes(self, income: float) -> None:
        if income < 0:
            raise ValueError("Ingreso no puede ser negativo")
        self.monthly_income += income

    def __repr__(self):
        return f"Participante('{self.name}', {self.monthly_income}€)"


# ====================================================
# PARTICIPANTE - Zona de pruebas
# ====================================================
if __name__ == "__main__": # pragma: no cover
    print("=== TESTING PARTICIPANTE ===\n")

    # 1. Crear miembro
    member1 = Participante("Member1")
    print(f"Miembro creado: {member1}")

    # 2. Agregar ingresos
    member1.add_incomes(1500)
    member1.add_incomes(200)
    print(f"Ingresos acumulados: {member1}")

    # 3. Validaciones
    print(f"\n=== VALIDACIONES ===")
    
    try:
        Participante(" ")
    except ValueError as e:
        print(f"✓ Nombre vacío bloqueado: {e}")

    try:
        member1.add_incomes(-500)
    except ValueError as e:
        print(f"✓ Ingreso negativo bloqueado: {e}")
    
    print(f"\n=== FIN TESTING HOUSEHOLD 11/02/2026 ===")
    
    # ====== CONTINUACIÓN ======