from src.models.participante import Participante
from src.models.calculator import Calculator
from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.utils.change_eur_cent import to_percentage_basis
from typing import Dict


class Household:
    def __init__(
        self, budget: Budget, method: MetodoReparto = MetodoReparto.PROPORTIONAL
    ) -> None:  # phase=Fase.REGISTRO

        self.members: Dict[str, Participante] = {}
        self.budget = budget
        self.method = method
        self._custom_splits = {}

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

    def set_custom_splits(self, splits: dict[str, float]):
        """
        Define splits custom (ya validados desde fuera).
        Convierte de float (55.55) a basis points (5555).
        """
        if not self.members:
            raise ValueError("Registra a los miembros antes de asignar porcentajes")

        # Validación de seguridad: asegurar que todos los miembros tienen un split asignado
        for name in self.members:
            if name not in splits:
                raise ValueError(f"Falta el porcentaje para el miembro: {name}")

        self._custom_splits = {
            name: to_percentage_basis(pct) for name, pct in splits.items()
        }

    def get_percentages_by_method(self, method: MetodoReparto):
        """Calcula el porcentaje de reparto según método elegido"""
        if not self.members:
            raise ValueError("No hay miembros registrados")

        income_map = {name: m.monthly_income for name, m in self.members.items()}
        percentages = {}

        match method:
            case MetodoReparto.PROPORTIONAL:
                percentages = Calculator.calculate_percentage_based_on_weight_of_income(
                    income_map
                )

            case MetodoReparto.EQUAL:
                percentages = Calculator.calculate_equal_percentage(income_map)

            case MetodoReparto.CUSTOM:
                if not hasattr(self, "_custom_splits"):
                    raise ValueError(
                        "Método CUSTOM requiere llamar a set_custom_splits() primero"
                    )
                return self._custom_splits

        return percentages

    def calculate_member_contribution_for_category(self, percentages, budget_amount):
        """Calcula contribución de UNA categoría"""
        return Calculator.calculate_contribution(percentages, budget_amount)

    def get_budget_contribution_summary(self, method: MetodoReparto):
        """
        Retorna resumen completo por categoría
        {
            'fijos': {
                'planned': 90000 céntimos,
                'contributions': {'Amanda': 48200, 'Heri': 41800},
                'total_assigned': 90000
            },
            ...
        }
        """
        percentages = self.get_percentages_by_method(method)
        summary = {}

        for cat_name, category in self.budget.categories.items():
            contributions = Calculator.calculate_contribution(
                percentages, category.planned_amount
            )
            summary[cat_name] = {
                "planned": category.planned_amount,
                "contributions": contributions,
                "total_assigned": sum(contributions.values()),
            }

        return summary

 