from src.models.participante import Participante
from src.models.calculadora import Calculator
from src.models.constants import MetodoReparto, Fase
from typing import Dict


class Household:

    def __init__(self) -> None:  # phase=Fase.REGISTRO

        self.members: Dict[str, Participante] = {}

    def register_member(self, member: Participante):
        """Crear instancias de miembros de la unidad e incorporar en dict de miembros"""
        self.members[member.name] = member

    def set_members_incomes(self, name: str, amount: float):
        """Interfaz para que usuario introduzca ingreso del mes."""
        if name not in self.members:
            raise ValueError(f"{name} no existe en el hogar")

        self.members[name].add_incomes(amount)

    def get_total_incomes(self):
        """
        Calcula el total de ingresos entre los miembros
        """
        if not self.members:
            raise ValueError("No hay miembros registrados")

        total = Calculator.sum_total_incomes(self.members)

        if total <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos > 0")

        return total

    def get_percentages(self) -> dict:
        """
        Calcula el porcentaje que representa el sueldo de cada usuario frente al total de ingresos
        """
        if not self.members:
            raise ValueError("No hay miembros registrados")

        percentages = Calculator.calculate_member_percentage(self.members)

        return percentages



# ====================================================
# HOUSEHOLD - Zona de pruebas
# ====================================================
if __name__ == "__main__": # pragma: no cover
    print("=== TESTING HOUSEHOLD ===\n")

    # 1. Crear household
    household = Household()
    print(f"Household creado: {household.members}")

    # 2. Registrar miembros
    amanda = Participante("Amanda")
    heri = Participante("Heri")
    household.register_member(amanda)
    household.register_member(heri)
    print(f"\nMiembros registrados: {list(household.members.keys())}")

    # 3. Añadir ingresos
    print(f"\n=== AÑADIENDO INGRESOS ===")
    household.set_members_incomes("Amanda", 1500)
    household.set_members_incomes("Heri", 1300)
    
    for name, member in household.members.items():
        print(f"  {name}: {member.monthly_income}€")

    # 4. Calcular total
    total = household.get_total_incomes()
    print(f"\nTotal: {total}€")

    # 5. Calcular porcentajes
    percentages = household.get_percentages()
    print(f"\nPorcentajes:")
    for name, pct in percentages.items():
        print(f"  {name}: {pct:.2f}%")

    # 6. Validaciones
    print(f"\n=== VALIDACIONES ===")

    # Household vacío
    empty = Household()
    try:
        empty.get_total_incomes()
    except ValueError as e:
        print(f"✓ Household vacío bloqueado: {e}")

    # Miembro inexistente
    try:
        household.set_members_incomes("NoExiste", 1000)
    except ValueError as e:
        print(f"✓ Miembro inexistente bloqueado: {e}")

    # Ingresos en 0
    zero_household = Household()
    zero_household.register_member(Participante("Test"))
    try:
        zero_household.get_total_incomes()
    except ValueError as e:
        print(f"✓ Ingresos 0 bloqueado: {e}")


    print(f"\n=== FIN TESTING HOUSEHOLD 11/02/2026 ===")
    
    # ====== CONTINUACIÓN ======
    