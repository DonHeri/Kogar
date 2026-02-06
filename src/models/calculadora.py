from src.models.participante import Participante
from typing import Dict


class Calculator:

    @staticmethod
    def sum_total_incomes(members: dict[str, Participante]) -> float:
        """Calcula el total de ingresos entre los miembros"""
        return sum(m.monthly_income for m in members.values())

    @staticmethod
    def calculate_member_percentage(
        dict_members: Dict[str, Participante], total_incomes
    ):
        """
        Retorna dict con porcentaje de cada miembro.
        {"Amanda": 53.57, "Heri": 46.43}
        """
        # TODO || TEST

        # almacenar porcentajes de cada usuario
        percentages = {}

        for name, member in dict_members.items():
            percentages[name] = (member.monthly_income / total_incomes) * 100

        return percentages

    @staticmethod
    def calculate_contribution(percentages, monto):
        """
        Retorna cuánto paga cada uno de un monto.
        {"Amanda": 535.71, "Heri": 464.29}
        """
        # TODO || TEST
        # Si se eligen aporte equitativos -> 100 / total de miembros

        contribution = {}
        for name, percentage in percentages.items():
            contribution[name] = (percentage / 100) * monto

        return contribution


if __name__ == "__main__":
    """
    Zona de prueba de código
    python -m src.models.calculadora
    """
