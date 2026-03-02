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
    def add_category(self, name: str):
        """Agrega categoría y la propaga a Budget"""
        self.budget.add_category(name)

    def remove_category(self, name: str):
        """Elimina categoría"""
        self.budget.delete_budget_category(name)

    def set_standard_categories(self):
        self.budget.set_standard_categories()

    def get_active_categories(self) -> list[str]:
        """Lista categorías activas"""
        return self.budget.get_categories_list()

    def get_category_budget(self, name: str) -> int:
        """Obtiene presupuesto asignado a una categoría"""
        return self.budget.get_category_budget(name)

    # ====== BUDGET ASSIGNMENT ======
    def set_budget_for_category(self, category: str, amount: float) -> None:
        """Asigna presupuesto a una categoría en fase PLANNING"""
        self.budget.set_budget(category, amount)

    # ====== DISTRIBUTION BY CATEGORY ======
    # Futuro v0.3: set_category_distribution_method() y get_category_preview()

    # ====== DISTRIBUTION BY CATEGORY ======
    # Futuro v0.3: set_category_distribution_method() y get_category_preview()
    
    # ====== DISTRIBUTION METHOD CONFIGURATION ======
    def assign_distribution_method(self, method: MetodoReparto):
        """Establece método de reparto"""
        self.method = method

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

    def get_planning_summary(self) -> dict:
        """
        Retorna resumen completo del estado en fase PLANNING
        Incluye: miembros, ingresos, categorías, presupuestos, y previsualización de contribuciones
        """
        self._validate_members_exist()
        self._validate_total_incomes_positive()

        total_incomes = self.get_total_incomes()
        categories = self.get_active_categories()
        total_budgeted = sum(
            self.budget.categories[cat].planned_amount for cat in categories
        )
        loose_money = total_incomes - total_budgeted

        percentages = self.get_percentages_by_method(self.method)
        contributions = self.get_budget_contribution_summary(self.method)

        member_incomes = {name: m.monthly_income for name, m in self.members.items()}

        return {
            "members": list(self.members.keys()),
            "member_incomes": member_incomes,
            "total_household_income": total_incomes,
            "distribution_method": self.method.value,
            "distribution_percentages": percentages,
            "categories": categories,
            "budget_by_category": {
                cat: self.budget.categories[cat].planned_amount for cat in categories
            },
            "total_budgeted": total_budgeted,
            "loose_money": loose_money,
            "contributions_preview": contributions,
        }

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

    def _validate_category_exist(self, category: str):
        """Valida que una categoría existe en el presupuesto"""
        return self.budget._validate_active_category(category)
