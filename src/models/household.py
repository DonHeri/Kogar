from src.models.member import Member
from src.models.finance_calculator import FinanceCalculator
from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.utils.currency import to_percentage_basis
from typing import Dict


class Household:
    def __init__(
        self, budget: Budget, method: MetodoReparto = MetodoReparto.PROPORTIONAL
    ) -> None:

        self.members: Dict[str, Member] = {}
        self.budget = budget
        self.method = method
        self._custom_splits = {}

    # ====== MEMBERS MANAGEMENT ======
    def register_member(self, member: Member):
        """Registra un nuevo miembro en el hogar"""
        if member.name in self.members:
            raise ValueError(f"{member.name} ya está registrado en el hogar")

        self.members[member.name] = member

    def set_member_income(self, name: str, amount: float):
        """Establece el ingreso mensual de un miembro"""
        if name not in self.members:
            raise ValueError(f"{name} no existe en el hogar")

        self.members[name].add_incomes(amount)

    # ====== INCOME CALCULATIONS ======
    def get_total_incomes(self):
        """Calcula el ingreso total mensual de todos los miembros"""
        self._validate_members_exist()
        self._validate_total_incomes_positive()

        incomes = [m.monthly_income for m in self.members.values()]
        total = FinanceCalculator.sum_values(incomes)

        return total

    # ====== CATEGORY MANAGEMENT ======

    # ====== BUDGET ASSIGNMENT ======

    # ====== DISTRIBUTION METHOD CONFIGURATION ======
    def set_custom_splits(self, splits: dict[str, float]):
        """Define porcentajes de reparto personalizados (0-100)"""
        self._validate_members_exist()
        self._validate_all_members_have_split(splits)

        self._custom_splits = {
            name: to_percentage_basis(pct) for name, pct in splits.items()
        }

    def get_percentages_by_method(self, method: MetodoReparto):
        """Calcula el porcentaje de reparto según método elegido"""
        self._validate_members_exist()
        self._validate_total_incomes_positive()

        income_map = {name: m.monthly_income for name, m in self.members.items()}
        percentages = {}

        match method:
            case MetodoReparto.PROPORTIONAL:
                percentages = (
                    FinanceCalculator.calculate_percentage_based_on_weight_of_income(
                        income_map
                    )
                )

            case MetodoReparto.EQUAL:
                percentages = FinanceCalculator.calculate_equal_percentage(income_map)

            case MetodoReparto.CUSTOM:
                if not hasattr(self, "_custom_splits"):
                    raise ValueError(
                        "Método CUSTOM requiere llamar a set_custom_splits() primero"
                    )
                return self._custom_splits

        return percentages

    # ====== CONTRIBUTION CALCULATIONS ======
    def calculate_member_contribution_for_category(self, percentages, budget_amount):
        """Calcula la contribución de cada miembro para una categoría específica"""
        return FinanceCalculator.calculate_contribution(percentages, budget_amount)

    # ====== QUERIES ======
    def get_budget_contribution_summary(self, method: MetodoReparto):
        """Retorna resumen completo de contribuciones por categoría"""
        percentages = self.get_percentages_by_method(method)
        summary = {}

        for cat_name, category in self.budget.categories.items():
            contributions = FinanceCalculator.calculate_contribution(
                percentages, category.planned_amount
            )
            summary[cat_name] = {
                "planned": category.planned_amount,
                "contributions": contributions,
                "total_assigned": sum(contributions.values()),
            }

        return summary

    # ====== VALIDATORS ======
    def _validate_members_exist(self):
        """Valida que hay miembros registrados"""
        if not self.members:
            raise ValueError("No hay miembros registrados")

    def _validate_total_incomes_positive(self):
        """Valida que el ingreso total es mayor a 0"""
        total = FinanceCalculator.sum_values(
            [m.monthly_income for m in self.members.values()]
        )
        if total <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos > 0")

    def _validate_all_members_have_split(self, splits: dict[str, float]):
        """Valida que todos los miembros tienen asignado un porcentaje"""
        for name in self.members:
            if name not in splits:
                raise ValueError(f"Falta el porcentaje para el miembro: {name}")
