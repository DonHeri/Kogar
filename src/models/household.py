from src.models.member import Member
from src.models.finance_calculator import FinanceCalculator
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.expense import Expense
from src.models.constants import MetodoReparto
from src.utils.currency import to_percentage_basis
from typing import Dict


class Household:
    def __init__(
        self,
        budget: Budget,
        expense_tracker: ExpenseTracker,
        method: MetodoReparto = MetodoReparto.PROPORTIONAL,
    ) -> None:

        self.members: Dict[str, Member] = {}
        self.budget = budget
        self.expense_tracker = expense_tracker
        self.method = method
        self._custom_splits = {}
        self._registered_incomes = {}
        self._agreed_percentages = {}
        self._agreed_contributions = {}

    # ====== MEMBERS MANAGEMENT ======
    def register_member(self, member: Member):
        """Registra un nuevo miembro en el hogar"""
        if member.name in self.members:
            raise ValueError(f"{member.name} ya está registrado en el hogar")

        self.members[member.name] = member

    def set_member_income(self, name: str, amount_cents: int):
        """Establece el ingreso mensual de un miembro (en céntimos)"""
        if name not in self.members:
            raise ValueError(f"{name} no existe en el hogar")

        self.members[name].add_incomes(amount_cents)

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

    # ====== DISTRIBUTION CONFIGURATION ======
    def assign_distribution_method(self, method: MetodoReparto):
        """Establece método de reparto"""
        self.method = method

    def set_custom_splits(self, splits: dict[str, float]):
        """Define porcentajes de reparto personalizados (0-100)"""
        self._validate_has_members()
        self._validate_all_members_have_split(splits)

        self._custom_splits = {
            name: to_percentage_basis(pct) for name, pct in splits.items()
        }

    # ====== REGISTRATION STATE (freeze/unfreeze) ======
    def freeze_registration_state(self):
        """Congela los ingresos registrados al pasar a fase PLANNING"""
        self._registered_incomes = {
            name: member.monthly_income for name, member in self.members.items()
        }

    # ====== PLANNING STATE (freeze/unfreeze) ======
    def freeze_planning_state(self):
        """Congela el estado de planificación al pasar a fase MONTH"""
        self._agreed_percentages = self.get_percentages_by_method(self.method)
        self._agreed_contributions = self.get_current_contributions()

    def get_registered_incomes(self) -> dict[str, int]:
        """Obtiene ingresos congelados (disponible en PLANNING/MONTH)"""
        if not self._registered_incomes:
            raise ValueError(
                "Los ingresos no han sido congelados. Llama a finish_registration() primero."
            )
        return self._registered_incomes.copy()

    def get_agreed_percentages(self) -> dict[str, int]:
        """Obtiene porcentajes acordados congelados (disponible en MONTH)"""
        if not self._agreed_percentages:
            raise ValueError(
                "Los porcentajes no han sido congelados. Llama a finish_planning() primero."
            )
        return self._agreed_percentages.copy()

    def get_agreed_contributions(self):
        """Obtiene contribuciones acordadas congeladas (disponible en MONTH)"""
        if not self._agreed_contributions:
            raise ValueError(
                "Las contribuciones no han sido congeladas. Llama a finish_planning() primero."
            )
        return self._agreed_contributions.copy()

    # ====== EXPENSES (MONTH phase) ======
    def register_expense(self, expense: Expense):
        """Registra un gasto (almacena solo en ExpenseTracker)"""
        self._validate_member_exist(expense.member)
        self._validate_category_exist(expense.category)
        self.expense_tracker.add_expense(expense)

    # ====== QUERIES - REGISTRATION ======
    def get_registration_summary(self):
        """Resumen de fase REGISTRATION: miembros e ingresos"""
        self._validate_has_members()
        self._validate_total_incomes_positive()
        member_incomes = {name: m.monthly_income for name, m in self.members.items()}
        total_incomes = self.get_total_incomes()
        return {
            "members": list(self.members.keys()),
            "member_incomes": member_incomes,
            "total_household_income": total_incomes,
        }

    # ====== QUERIES - PLANNING ======

    def preview_budget_contribution_summary(self, method: MetodoReparto):
        """
        Calcula contribuciones por categoría con método de reparto inyectado.

        Returns:
            dict: Por cada categoría:
                - planned: presupuesto planificado (céntimos)
                - contributions: {nombre_miembro: contribución (céntimos)}
                - total_assigned: suma de contributions
        """
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

    def get_current_contributions(self):
        """Obtiene contribuciones usando el método ya configurado (self.method)"""
        return self.preview_budget_contribution_summary(self.method)

    def get_total_budgeted(self):
        """Obtiene total presupuestado (cents)"""
        return self.budget.get_total_budgeted()

    def get_loose_money(self):
        """Calcula dinero no presupuestado (ingresos - total_budgeted)"""
        categories = self.get_active_categories()
        total_incomes = self.get_total_incomes()
        total_budgeted = sum(
            self.budget.categories[cat].planned_amount for cat in categories
        )
        return total_incomes - total_budgeted

    def get_planning_summary(self) -> dict:
        """
        Resumen completo de fase PLANNING con el método ya configurado.
        Incluye: miembros, ingresos, método, porcentajes, categorías, presupuestos, loose_money, preview de contribuciones.
        """
        self._validate_has_members()
        self._validate_total_incomes_positive()

        total_incomes = self.get_total_incomes()
        categories = self.get_active_categories()
        total_budgeted = self.get_total_budgeted()

        loose_money = total_incomes - total_budgeted

        percentages = self.get_percentages_by_method(self.method)  # FIXME

        contributions = self.get_current_contributions()

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

    # ====== QUERIES - MONTH ======
    def get_member_owed_total(self, member_name: str) -> int:
        """Cuánto acordó pagar el miembro"""
        self._validate_member_exist(member_name)
        contributions = self.get_agreed_contributions()
        total = sum(
            cat_data["contributions"][member_name]
            for cat_data in contributions.values()
        )
        return total

    def get_member_paid_total(self, member_name: str) -> int:
        """Total gastado por un miembro"""
        return self.expense_tracker.get_total_spent_by_member(member_name)

    def get_member_balance(self, member_name: str) -> int:
        """Balance: pagado - acordado (negativo = debe, positivo = pagó de más)"""
        self._validate_member_exist(member_name)
        owed = self.get_member_owed_total(member_name)
        paid = self.get_member_paid_total(member_name)

        return paid - owed

    def get_member_status(self, member_name: str) -> dict:
        """Retorna dict: {income, owed, paid, balance, contributions_by_category}"""
        self._validate_member_exist(member_name)
        # Totales
        income = self.get_registered_incomes()
        owed = self.get_member_owed_total(member_name)
        paid = self.get_member_paid_total(member_name)
        balance = self.get_member_balance(member_name)

        # Acordado vs pagado
        agreed_contributions = self.get_agreed_contributions()
        by_category = {}

        for cat_name, cat_data in agreed_contributions.items():
            contribution = cat_data["contribution"][member_name]
            paid = self.expense_tracker.get_total_spent_by_member_and_category(
                member=member_name, category=cat_name
            )

            by_category[cat_name] = {
                "contribution": contribution,
                "paid": paid,
                "remaining": contribution - paid,
            }

        return {
            "income": income,
            "owed": owed,
            "paid": paid,
            "balance": balance,
            "by_category": by_category,  # ← Desglose completo
        }

    def get_category_spent(self, category: str) -> int:
        """Obtiene total gastado en una categoría (consulta ExpenseTracker)"""
        return self.expense_tracker.get_total_spent_by_category(category)

    def get_total_spent(self) -> int:
        """Obtiene total gastado (consulta ExpenseTracker)"""
        return self.expense_tracker.get_total_spent()

    def get_category_remaining(self, category: str) -> int:
        """Calcula presupuesto restante de una categoría: planificado - gastado"""
        budgeted = self.budget.get_category_budget(category)
        spent = self.get_category_spent(category)
        return budgeted - spent

    def get_total_remaining(self) -> int:
        """Calcula total restante: presupuesto total - total gastado"""
        budgeted = self.get_total_budgeted()
        spent = self.get_total_spent()
        return budgeted - spent

    def get_month_summary(self):
        """Resumen de ejecución en fase MONTH: planned vs spent"""
        categories = self.get_active_categories()

        total_budgeted = self.get_total_budgeted()
        loose_money = self.get_loose_money()
        total_spent = self.get_total_spent()
        total_remaining = self.get_total_remaining()

        # Total presupuestado + total gastado + total restante
        total = {
            "total_budgeted": total_budgeted,
            "total_spent": total_spent,
            "total_remaining": total_remaining,
        }

        # Categoría {Presupuestado + Gastado + faltante por pagar} + {loose money}
        by_category = {}
        for cat in categories:
            by_category[cat] = {
                "budget": self.budget.get_category_budget(cat),
                "spent": self.get_category_spent(cat),
                "remaining": self.get_category_remaining(cat),
            }
        by_category["loose_money"] = loose_money

        # TODO: Member{category{contribution,spent,remaining}}
        # TODO: Loose_money{total,members:{loose_money by member}}

        return {"total": total, "by_category": by_category}

    # ====== INTERNAL HELPERS ======
    def get_total_incomes(self):
        """Calcula el ingreso total mensual (usa datos congelados si están disponibles)"""
        self._validate_has_members()
        self._validate_total_incomes_positive()

        # Usar datos congelados si están disponibles (PLANNING/MONTH)
        if self._registered_incomes:
            incomes = list(self._registered_incomes.values())
        else:
            # Usar datos mutables solo en REGISTRATION
            incomes = [m.monthly_income for m in self.members.values()]

        total = FinanceCalculator.sum_values(incomes)
        return total

    def get_percentages_by_method(self, method: MetodoReparto):
        """Calcula el porcentaje de reparto (usa datos congelados si están disponibles)"""
        self._validate_has_members()
        self._validate_total_incomes_positive()

        # Usar datos congelados si están disponibles (PLANNING/MONTH)
        if self._registered_incomes:
            income_map = self._registered_incomes
        else:
            # Usar datos mutables solo en REGISTRATION
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

    def calculate_member_contribution_for_category(self, percentages, budget_amount):
        """Calcula la contribución de cada miembro para una categoría específica"""
        return FinanceCalculator.calculate_contribution(percentages, budget_amount)

    # ====== VALIDATORS ======
    def _validate_has_members(self):
        """Valida que hay miembros registrados"""
        if not self.members:
            raise ValueError("No hay miembros registrados")

    def _validate_total_incomes_positive(self):
        """Valida que el ingreso total es mayor a 0 (usa datos congelados si están disponibles)"""
        # Usar datos congelados si están disponibles (PLANNING/MONTH)
        if self._registered_incomes:
            incomes = list(self._registered_incomes.values())
        else:
            # Usar datos mutables solo en REGISTRATION
            incomes = [m.monthly_income for m in self.members.values()]

        total = FinanceCalculator.sum_values(incomes)
        if total <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos > 0")

    def _validate_all_members_have_split(self, splits: dict[str, float]):
        """Valida que todos los miembros tienen asignado un porcentaje"""
        for name in self.members:
            if name not in splits:
                raise ValueError(f"Falta el porcentaje para el miembro: {name}")

    def _validate_category_exist(self, category: str):
        """Valida que una categoría existe en el presupuesto"""
        return self.budget._validate_category_exists(category)

    def _validate_member_exist(self, member: str):
        """Valida que un miembro existe en el hogar"""
        if member not in self.members:
            raise ValueError(f"{member} no existe en el hogar")
