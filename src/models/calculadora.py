from src.models.participante import Participante
from typing import Dict


class Calculator:

    @staticmethod
    def sum_total_incomes(members: dict[str, Participante]) -> float:
        """Calcula el total de ingresos entre los miembros"""
        return sum(m.monthly_income for m in members.values())

    @staticmethod
    def calculate_member_percentage(dict_members: Dict[str, Participante]) -> dict:
        """
        Parámetros:
        members: Miembros registrados
        """
        total = Calculator.sum_total_incomes(dict_members)

        if total <= 0:
            raise ValueError("Total de ingresos debe ser > 0")

        # almacenar porcentajes de cada usuario
        percentages = {}

        for name, member in dict_members.items():
            percentages[name] = (member.monthly_income / total) * 100

        return percentages


# ====================================================
# Sin integrar
# ====================================================

    """ @staticmethod
    def calculate_contribution(percentages, monto):

        # TODO || TEST
        # Si se eligen aporte equitativos -> 100 / total de miembros

        contribution = {}
        for name, percentage in percentages.items():
            contribution[name] = (percentage / 100) * monto

        return contribution
 """

# ====================================================
# CALCULATOR - Zona de pruebas
# ====================================================
if __name__ == "__main__": # pragma: no cover
    print("=== TESTING CALCULATOR ===\n")

    # 1. Crear miembros
    m1 = Participante("Amanda")
    m2 = Participante("Heri")
    m1.monthly_income = 1500.0
    m2.monthly_income = 1300.0
    
    members = {m1.name: m1, m2.name: m2}
    print(f"Miembros: {list(members.keys())}")

    # 2. Suma total
    total = Calculator.sum_total_incomes(members)
    print(f"\nTotal ingresos: {total}€")

    # 3. Porcentajes
    percentages = Calculator.calculate_member_percentage(members)
    print(f"\nPorcentajes:")
    for name, pct in percentages.items():
        print(f"  {name}: {pct:.2f}%")
    print(f"Suma: {sum(percentages.values()):.2f}%")

    # 4. Validaciones
    print(f"\n=== VALIDACIONES ===")
    
    # Diccionario vacío
    try:
        Calculator.sum_total_incomes({})
        print(f"✓ Diccionario vacío devuelve 0: OK")
    except Exception as e:
        print(f"✗ Error inesperado: {e}")

    # Total en 0
    m_zero = Participante("Zero")
    try:
        Calculator.calculate_member_percentage({m_zero.name: m_zero})
    except ValueError as e:
        print(f"✓ Total 0 bloqueado: {e}")

    print(f"\n=== FIN TESTING HOUSEHOLD 11/02/2026 ===")
    
    # ====== CONTINUACIÓN ======
