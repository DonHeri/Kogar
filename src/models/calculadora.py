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
