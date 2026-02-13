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

        # Extraemos solo los números (los ingresos) antes de llamar a la calculadora
        incomes = [m.monthly_income for m in self.members.values()]
        total = Calculator.sum_values(incomes)
        
        if total <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos > 0")

        return total

    def get_percentages(self) -> dict:
        """
        Calcula el porcentaje que representa el sueldo de cada usuario frente al total de ingresos
        """
        if not self.members:
            raise ValueError("No hay miembros registrados")

        # Extraemos el "mapa de ingresos" para desacoplar
        income_map = {name: m.monthly_income for name, m in self.members.items()}

        # La calculadora procesa números, no objetos Participante
        return Calculator.calculate_member_percentage(income_map)
        
        


