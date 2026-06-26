from src.models.household import Household
from src.models.category import AutoCalculatedCategory
from src.models.finance_calculator import FinanceCalculator
from src.utils.text import normalize_name


class BudgetDistributionService:
    def __init__(self, household: Household) -> None:
        self.household = household

    def set_budget_for_category(self, category: str, amount_cents: int) -> None:
        """Asigna presupuesto a una categoría en PLANNING. La reserva se ajusta sola."""
        if isinstance(
            self.household.budget.get_category(category), AutoCalculatedCategory
        ):
            raise ValueError("Reserva se autocalcula")

        category = normalize_name(category)

        if self.household.budget.categories[category].parent is None:
            self._set_root_budget(category, amount_cents)
        else:
            self._set_child_budget(category, amount_cents)

    def _set_root_budget(self, category: str, amount_cents: int) -> None:
        """Raíz: cuenta contra los ingresos y recalcula la reserva."""
        reserve_cat = self.household.budget.get_auto_calculated_category()
        total_incomes = self.household.get_total_incomes()
        current_amount = self.household.get_category_budget(category)
        current_reserve = self.household.get_category_budget(reserve_cat.name)

        other_budgeted = (
            self.household.get_total_budgeted() - current_amount - current_reserve
        )
        new_budgeted = other_budgeted + amount_cents

        if new_budgeted > total_incomes:
            raise ValueError(
                "No se puede superar el total de ingresos en los presupuestos"
            )

        self.household.budget.set_budget(category, amount_cents)
        self.household.budget.set_budget(
            reserve_cat.name,
            reserve_cat.calculate_own_budget(total_incomes, new_budgeted),
        )

    def _set_child_budget(self, category: str, amount_cents: int) -> None:
        """Hija: se mueve dentro del techo de su raíz, sin tocar la reserva."""
        parent_name = self.household.budget.categories[category].parent
        ceiling = self.household.get_category_budget(parent_name)
        current_amount = self.household.get_category_budget(category)

        siblings_total = (
            self.household.budget.get_child_total_planned(parent_name) - current_amount
        )

        if siblings_total + amount_cents > ceiling:
            raise ValueError(
                f"No se puede superar el techo de la categoría raíz: {parent_name.title()}"
            )

        self.household.budget.set_budget(category, amount_cents)

    def set_budget_by_percentages(self, percentages: dict[str, int]):
        """Asigna presupuestos desde porcentajes. Reserva se autocalcula."""
        total_incomes = self.household.get_total_incomes()

        budgets = FinanceCalculator.calculate_budget_from_percentages(
            total_incomes, percentages
        )

        auto_cat = self.household.budget.get_auto_calculated_category()
        for category, amount_cents in budgets.items():
            # La categoría auto-calculada se ajusta sola en set_budget_for_category
            if category == auto_cat.name:
                continue

            self.household.validate_category_exist(category=category)
            self.set_budget_for_category(category=category, amount_cents=amount_cents)
