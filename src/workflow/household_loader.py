from datetime import datetime
from uuid import UUID
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.expense_repository import ExpenseRepository
from src.storage.debt_bucket_repository import DebtBucketRepository
from src.storage.debt_entry_repository import DebtEntryRepository
from src.storage.budget_categories_repository import BudgetCategoryRepository
from src.storage.saving_bucket_repository import SavingBucketRepository
from src.storage.saving_bucket_entry_repository import SavingBucketEntryRepository

from src.models.budget import Budget
from src.models.household import Household
from src.models.expense import Expense
from src.models.debt_bucket import DebtBucket
from src.models.debt_entry import DebtEntry
from src.models.saving_bucket import SavingBucket
from src.models.member import Member
from src.models.expense_tracker import ExpenseTracker
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.models.debt_bucket_tracker import DebtBucketTracker

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
        debt_bucket_repository: DebtBucketRepository,
        debt_entry_repository: DebtEntryRepository,
        saving_bucket_repository: SavingBucketRepository,
        saving_bucket_entry_repository: SavingBucketEntryRepository,
    ):
        self._household_repo = household_repo
        self._member_repo = member_repo
        self._period_repo = period_repo
        self._budget_categories_repo = budget_categories_repo
        self._expense_repository = expense_repository
        self._debt_bucket_respository = debt_bucket_repository
        self._debt_entry_respository = debt_entry_repository
        self._saving_bucket_repository = saving_bucket_repository
        self._saving_bucket_entry_repository = saving_bucket_entry_repository

    # ============================================================
    # # recetas públicas (composiciones por PROFUNDIDAD, no por servicio)
    # ============================================================

    def load_members_only(
        self, household_id: int, period: Period | None = None
    ) -> tuple[Household, dict[str, int]]:

        # crear household
        household = self._build_base(period=period)

        # Hidratar miembros
        member_rows = self._member_repo.list_members(household_id)

        member_ids = self._hydrate_members(household=household, members=member_rows)

        return (household, member_ids)

    def load_base(
        self, household_id: int, period_id: int
    ) -> tuple[Household, dict[str, int], Phase]:

        # 1. Leer filas

        period = self._period_repo.find_by_id(period_id)
        phase = period.status
        category_rows = sorted(
            self._budget_categories_repo.find_by_period(period_id),
            key=lambda row: row["parent_name"] is not None,
        )

        # 2. Construir Household base (trackers vacíos)
        household, member_ids = self.load_members_only(
            household_id=household_id, period=period
        )

        # 3. Repoblar lo que el gasto necesita
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

    def load_with_debts(self, household_id: int, period_id: int):
        # 1. Leer filas
        period = self._period_repo.find_by_id(period_id)
        phase = period.status
        debt_buckets_rows: list[dict] = self._debt_bucket_respository.find_by_household(
            household_id=household_id
        )

        # 2. Construir Household base (trackers vacíos)
        household, member_ids = self.load_members_only(
            household_id=household_id, period=period
        )

        # 3. Repoblar lo que el gasto necesita
        self._hydrate_debt_buckets(
            household=household,
            debt_buckets_rows=debt_buckets_rows,
            member_ids=member_ids,
        )

        return (household, member_ids, phase)

    def load_with_savings(self, household_id: int, period_id: int):
        # 1. Leer filas
        period = self._period_repo.find_by_id(period_id)
        phase = period.status
        saving_buckets_rows: list[dict] = self._saving_bucket_repository.find_with_owners(
            household_id=household_id
        )

        # 2. Construir Household base (trackers vacíos)
        household, member_ids = self.load_members_only(
            household_id=household_id, period=period
        )

        # 3. Repoblar buckets de ahorro + sus movimientos
        self._hydrate_saving_buckets(
            household=household,
            saving_buckets_rows=saving_buckets_rows,
            member_ids=member_ids,
        )

        return (household, member_ids, phase)

    # ============================================================
    # helpers privados (las piezas)
    # ============================================================

    def _build_base(self, period: Period | None) -> Household:
        budget = Budget()
        debt_tracker = DebtBucketTracker()
        saving_bucket_tracker = SavingBucketTracker()
        expense_tracker = ExpenseTracker()
        method = period.method if period else MetodoReparto.PROPORTIONAL

        household = Household(
            budget=budget,
            debt_bucket_tracker=debt_tracker,
            expense_tracker=expense_tracker,
            saving_bucket_tracker=saving_bucket_tracker,
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
        self,
        household: Household,
        expense_rows: list[dict],
        member_ids: dict[str, int],
    ):

        member_ids: dict[int, str] = {v: k for k, v in member_ids.items()}

        for row in expense_rows:
            participants: list = list(row["participants"])

            member: str = member_ids[row["payer_id"]]

            category: Category = household.budget.get_category(row["category"])
            amount_cents: int = row["amount_cents"]
            description: str = row["description"]
            date: datetime = row["expense_date"]
            expense = Expense(
                id=row["id"],
                amount_cents=amount_cents,
                category=category,
                date=date,
                description=description,
                member=member,
                participants=participants,
            )
            household.register_expense(expense)

    def _hydrate_debt_buckets(
        self,
        household: Household,
        debt_buckets_rows: list[dict],
        member_ids: dict[str, int],
    ):
        member_ids: dict[int, str] = {v: k for k, v in member_ids.items()}

        bucket_ids = [row["id"] for row in debt_buckets_rows]
        all_entries = self._debt_entry_respository.find_by_buckets(bucket_ids)

        entries_by_bucket: dict[UUID, list[dict]] = {}
        for entry_row in all_entries:
            entries_by_bucket.setdefault(entry_row["debt_id"], []).append(entry_row)

        for row in debt_buckets_rows:
            debt_bucket_name: str = row["bucket_name"]
            principal_cents: int = row["principal_cents"]
            owner: str = member_ids[row["member_id"]]
            installment_cents = row["installment_cents"]
            term_months: int | None = row["term_months"]
            start_date: datetime = row["start_date"]
            description: str = row["description"]

            id = row["id"]

            bucket = DebtBucket(
                debt_bucket_name=debt_bucket_name,
                principal_cents=principal_cents,
                owner=owner,
                installment_cents=installment_cents,
                id=id,
                start_date=start_date,
                description=description,
            )
            household.debt_bucket_tracker.add_bucket(bucket)

            # Orden cronológico: hoy pay() no valida contra saldo (sobrepago sin
            # restricción, decisión T1), así que el orden no cambia el resultado —
            # pero se reproduce igual que ahorro, por consistencia y por si algún
            # día pay() gana una validación que sí dependa del saldo acumulado.
            bucket_entries = sorted(
                entries_by_bucket.get(id, []), key=lambda e: e["payment_date"]
            )
            for entry_row in bucket_entries:
                bucket.pay(
                    amount_cents=entry_row["amount_cents"],
                    member_name=owner,
                    date=entry_row["payment_date"],
                    id=entry_row["id"],
                    description=entry_row["description"],
                )

    def _hydrate_saving_buckets(
        self,
        household: Household,
        saving_buckets_rows: list[dict],
        member_ids: dict[str, int],
    ):
        member_names_by_id: dict[int, str] = {v: k for k, v in member_ids.items()}

        bucket_ids = [row["id"] for row in saving_buckets_rows]
        all_entries = self._saving_bucket_entry_repository.find_by_buckets(bucket_ids)

        entries_by_bucket: dict[UUID, list[dict]] = {}
        for entry_row in all_entries:
            entries_by_bucket.setdefault(entry_row["bucket_id"], []).append(entry_row)

        for row in saving_buckets_rows:
            id = row["id"]

            bucket = SavingBucket(
                saving_bucket_name=row["bucket_name"],
                owners=list(row["owners"]),
                goal_cents=row["goal_cents"],
                deadline=row["deadline"],
                description=row["description"] or "",
                is_default=row["is_default"],
                id=id,
            )
            household.saving_bucket_tracker.add_bucket(bucket)

            # Se reproducen en orden cronológico: el saldo en cada paso coincide
            # con el saldo histórico real en ese momento, así withdraw() valida
            # correctamente contra un saldo que ya se está reconstruyendo bien.
            bucket_entries = sorted(
                entries_by_bucket.get(id, []), key=lambda e: e["entry_date"]
            )
            for entry_row in bucket_entries:
                member_name = member_names_by_id[entry_row["member_id"]]
                amount_cents = entry_row["amount_cents"]
                if amount_cents >= 0:
                    bucket.deposit(
                        amount_cents=amount_cents,
                        member_name=member_name,
                        date=entry_row["entry_date"],
                    )
                else:
                    bucket.withdraw(
                        amount_cents=-amount_cents,
                        member_name=member_name,
                        date=entry_row["entry_date"],
                    )

    def _hydrate_custom_splits(self):
        pass
