from src.models.participante import Participante
from typing import Dict


class Calculator:

    @staticmethod
    def sum_values(values: list[float]) -> float:
        """Suma una lista de valores numéricos de forma genérica."""
        return sum(values)

   
    @staticmethod
    def calculate_member_percentage(income_map: dict[str, float]) -> dict[str, float]:
        """
        Recibe un mapa simple {nombre: monto} y devuelve {nombre: porcentaje}.
        """
        
        total = sum(income_map.values()) # Ahora suma directamente valores

        if total <= 0:
            raise ValueError("Total de ingresos debe ser > 0")

        return {name: (income / total) * 100 for name, income in income_map.items()}




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
