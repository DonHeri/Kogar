from src.models.participante import Participante
from src.models.calculator import Calculator
from src.models.budget import Budget
from typing import Dict


class Household:

    def __init__(self, budget: Budget) -> None:  # phase=Fase.REGISTRO

        self.members: Dict[str, Participante] = {}
        self.budget = budget

    def register_member(self, member: Participante):
        """
        Registrar miembros.
        """

        self.members[member.name] = member

    def set_members_incomes(self, name: str, amount: float):
        """Introducir ingresos de usuarios."""
        if name not in self.members:
            raise ValueError(f"{name} no existe en el hogar")

        self.members[name].add_incomes(amount)

    def get_total_incomes(self):
        """
        Calcula el total de ingresos entre los miembros.
        """
        if not self.members:
            raise ValueError("No hay miembros registrados")

        # Extraemos solo los números (los ingresos) antes de llamar a la calculadora
        incomes = [m.monthly_income for m in self.members.values()]
        total = Calculator.sum_values(incomes)

        if total <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos > 0")

        return total

    # En Household
    def get_percentages(self):
        """Calcula el porcentaje que representa el sueldo de cada usuario (×100)"""
        if not self.members:
            raise ValueError("No hay miembros registrados")

        income_map = {name: m.monthly_income for name, m in self.members.items()}
        return Calculator.calculate_member_percentage(income_map)
