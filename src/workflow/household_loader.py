from datetime import datetime
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.expense_repository import ExpenseRepository
from src.storage.budget_categories_repository import BudgetCategoryRepository

from src.models.budget import Budget
from src.models.household import Household
from src.models.expense import Expense
from src.models.member import Member
from src.models.expense_tracker import ExpenseTracker
from src.models.saving_tracker import SavingTracker
from src.models.debt_tracker import DebtTracker
from src.models.period import Period
from src.models.category import Category
from src.models.constants import MetodoReparto, Phase


class HouseholdLoader:
    def __init__(
        self,
        household_repo: HouseholdRepository,
        member_repo: MemberRepository,
        period_repo: PeriodRepository,
        budget_categories_repo: BudgetCategoryRepository,
        expense_repository: ExpenseRepository,
    ):
        self._household_repo = household_repo
        self._member_repo = member_repo
        self._period_repo = period_repo
        self._budget_categories_repo = budget_categories_repo
        self._expense_repository = expense_repository

    # ============================================================
    # # recetas públicas (composiciones por PROFUNDIDAD, no por servicio)
    # ============================================================

    def load_members_only(self, household_id: int) -> tuple[Household, dict[str, int]]:
        """

        Args:
            param: descripcion

        Returns:
            descripcion
        """

        # crear household
        household = self._build_base(period=None)

        # Hidratar miembros
        member_rows = self._member_repo.list_members(household_id)

        member_ids = self._hydrate_members(household=household, members=member_rows)

        return (household, member_ids)

    def load_base(
        self, household_id: int, period_id: int
    ) -> tuple[Household, dict[str, int], Phase]:
        """

        Args:
            param: descripcion

        Returns:
            descripcion
        """

        # 1. Leer filas
        member_rows = self._member_repo.list_members(household_id)
        period = self._period_repo.find_by_id(period_id)
        phase = period.status
        category_rows = sorted(
            self._budget_categories_repo.find_by_period(period_id),
            key=lambda row: row["parent_name"] is not None,
        )

        # 2. Construir Household base (trackers vacíos)
        household = self._build_base(period=period)

        # 3. Repoblar lo que el gasto necesita
        member_ids = self._hydrate_members(household, member_rows)
        self._hydrate_budget(household, category_rows)

        return (household, member_ids, phase)

    def load_for_queries(self, household_id: int, period_id: int):
        """load_base + histórico de gastos del período (para lecturas)"""
        household, member_ids, phase = self.load_base(
            household_id=household_id, period_id=period_id
        )

        expense_rows = self._expense_repository.find_with_participants(period_id)
        self._hydrate_expenses(
            household, expense_rows=expense_rows, member_ids=member_ids
        )

        return (household, member_ids, phase)

    def load_with_budget():
        pass

    def load_with_debts():
        pass

    # ============================================================
    # helpers privados (las piezas)
    # ============================================================

    def _build_base(self, period: Period | None) -> Household:
        budget = Budget()
        debt_tracker = DebtTracker()
        saving_tracker = SavingTracker()
        expense_tracker = ExpenseTracker()
        method = period.method if period else MetodoReparto.PROPORTIONAL

        household = Household(
            budget=budget,
            debt_tracker=debt_tracker,
            expense_tracker=expense_tracker,
            saving_tracker=saving_tracker,
            method=method,
        )
        return household

    def _hydrate_members(self, household: Household, members: list) -> dict[str, int]:
        """Hidratar household con los miembros"""
        member_ids: dict[str, int] = {}

        for row in members:
            full_name = row["full_name"]
            # id
            member_ids[full_name] = row["id"]
            monthly_income = row["monthly_income"]

            member = Member(name=full_name)
            # Hidratar
            household.register_member(member=member)
            household.set_member_income(name=full_name, amount_cents=monthly_income)

        return member_ids

    def _hydrate_budget(self, household: Household, category_rows: list[dict]):
        """Hidratar household con presupuestos por categoría"""
        for row in category_rows:
            name = row["name"]
            parent = row["parent_name"]
            planned_amount = row["planned_amount"]

            household.add_category(name=name, parent=parent)
            household.budget.set_planned_amount(
                category=name, amount_cents=planned_amount
            )

    def _hydrate_expenses(
        self, household: Household, expense_rows: list[dict], member_ids
    ):
        """ """
        member_ids = {v: k for k, v in member_ids.items()}

        for row in expense_rows:
            participants: list = list(row["participants"])

            member: str = member_ids.get(row["payer_id"], "")  # FIXME

            category: Category = household.budget.get_category(row["category"])
            amount_cents: int = row["amount_cents"]
            description: str = row["description"]
            date: datetime = row["expense_date"]
            expense = Expense(
                amount_cents=amount_cents,
                category=category,
                date=date,
                description=description,
                member=member,
                participants=participants,
            )
            household.register_expense(expense)

    def _hydrate_debts():
        pass

    def _hydrate_savings():
        pass

    def _hydrate_buckets():
        pass

    def _hydrate_custom_splits(self):
        pass
