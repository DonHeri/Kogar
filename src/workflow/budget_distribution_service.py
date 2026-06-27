from src.models.household import Household
from src.models.category import AutoCalculatedCategory
from src.models.finance_calculator import FinanceCalculator
from src.utils.text import normalize_name


class BudgetDistributionService:
    @staticmethod
    def set_budget_for_category(household: Household, category: str, amount_cents: int) -> None:
        """Asigna presupuesto a una categoría en PLANNING. La reserva se ajusta sola."""
        if isinstance(
            household.budget.get_category(category), AutoCalculatedCategory
        ):
            raise ValueError("Reserva se autocalcula")

        category = normalize_name(category)

        if household.budget.categories[category].parent is None:
            BudgetDistributionService._set_root_budget(household, category, amount_cents)
        else:
            BudgetDistributionService._set_child_budget(household, category, amount_cents)

    @staticmethod
    def _set_root_budget(household: Household, category: str, amount_cents: int) -> None:
        """Raíz: cuenta contra los ingresos y recalcula la reserva."""
        reserve_cat = household.budget.get_auto_calculated_category()
        total_incomes = household.get_total_incomes()
        current_amount = household.get_category_budget(category)
        current_reserve = household.get_category_budget(reserve_cat.name)

        other_budgeted = (
            household.get_total_budgeted() - current_amount - current_reserve
        )
        new_budgeted = other_budgeted + amount_cents

        if new_budgeted > total_incomes:
            raise ValueError(
                "No se puede superar el total de ingresos en los presupuestos"
            )

        household.budget.set_budget(category, amount_cents)
        household.budget.set_budget(
            reserve_cat.name,
            reserve_cat.calculate_own_budget(total_incomes, new_budgeted),
        )

    @staticmethod
    def _set_child_budget(household: Household, category: str, amount_cents: int) -> None:
        """Hija: se mueve dentro del techo de su raíz, sin tocar la reserva."""
        parent_name = household.budget.categories[category].parent
        ceiling = household.get_category_budget(parent_name)
        current_amount = household.get_category_budget(category)

        siblings_total = (
            household.budget.get_child_total_planned(parent_name) - current_amount
        )

        if siblings_total + amount_cents > ceiling:
            raise ValueError(
                f"No se puede superar el techo de la categoría raíz: {parent_name.title()}"
            )

        household.budget.set_budget(category, amount_cents)

    @staticmethod
    def set_budget_by_percentages(household: Household, percentages: dict[str, int]):
        """Asigna presupuestos desde porcentajes. Reserva se autocalcula."""
        total_incomes = household.get_total_incomes()

        budgets = FinanceCalculator.calculate_budget_from_percentages(
            total_incomes, percentages
        )

        auto_cat = household.budget.get_auto_calculated_category()
        for category, amount_cents in budgets.items():
            if category == auto_cat.name:
                continue

            household.validate_category_exist(category=category)
            BudgetDistributionService.set_budget_for_category(
                household, category=category, amount_cents=amount_cents
            )
