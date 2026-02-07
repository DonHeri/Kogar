from src.models.participante import Participante
from src.models.calculadora import Calculator
from typing import Dict


class Household:

    def __init__(self) -> None:

        self.members: Dict[str, Participante] = (
            {}
        )  

    def register_member(self, member: Participante):
        """Crear instancias de miembros de la unidad e incorporar en dict de miembros"""
        self.members[member.name] = member

    def set_members_incomes(self, name: str, amount: float): #TODO || Validador de ingresos correctos
        """Interfaz para que usuario introduzca ingreso del mes."""
        if name not in self.members:
            raise ValueError(f"{name} no existe en el hogar")

        self.members[name].add_incomes(amount)

    def obtain_total_incomes(self): #TODO || Comprobar que los miembros tienen ingresos
        """Calcula el total de ingresos entre los miembros"""

        return Calculator.sum_total_incomes(self.members)

    def obtain_percentages(self):
        """Calcula el porcentaje para cada usuario"""
        # TODO: TEST
        total = self.obtain_total_incomes()

        if total <= 0:
            raise ValueError("Total de ingresos debe ser > 0")
        return Calculator.calculate_member_percentage(self.members, total)

    def obtain_contribution_member(
        self,
    ):  # IDEA:Inyectar porcentajes, parametro del monto también
        # TODO || TEST
        total = self.obtain_total_incomes()

        if total <= 0:
            raise ValueError("Total de ingresos debe ser > 0")

        percentages = self.obtain_percentages()
        aportes = Calculator.calculate_contribution(
            percentages, total
        )  # dict con montos definidos,y sacar a pagar por cada uno
        return aportes

    # ====================================================
    # FUNCIONES DE TESTS
    # ====================================================
    def test_register_member(self):
        """Datos de usuarios para probar el software"""
        # Datos de TEST
        self.register_member(Participante("Amanda"))
        self.register_member(Participante("Heri"))

    def test_incomes(self):
        """Simula ingresos para testear sistema"""
        self.set_members_incomes("Amanda", 1500.0)
        self.set_members_incomes("Heri", 1300.0)



# ====================================================
# Zona de pruebas
# ====================================================
if __name__ == "__main__":

