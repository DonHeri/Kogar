from datetime import datetime

from src.models.budget import Budget
from src.models.constants import MetodoReparto, SavingScope
from src.models.debt_tracker import DebtTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.member import Member
from src.models.saving_tracker import SavingTracker
from src.utils.currency import format_percentage, to_euros
from src.workflow.workflow_manager import WorkflowManager

# Persistencia
from src.storage.connection import DatabaseConnection
from src.storage.member_repository import MemberRepository
from src.storage.household_repository import HouseholdRepository
from src.storage.period_repository import PeriodRepository
from src.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

with DatabaseConnection(
    database=DB_NAME,
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
) as conn:
    household_repo = HouseholdRepository(conn)
    member_repo = MemberRepository(conn)
    period_repo = PeriodRepository(conn)
    # =============================================
    # SETUP — Instanciar todo
    # =============================================

    household = Household(
        budget=Budget(),
        expense_tracker=ExpenseTracker(),
        saving_tracker=SavingTracker(),
        debt_tracker=DebtTracker(),
        method=MetodoReparto.PROPORTIONAL,
    )

    print("=" * 60)
    print("FASE 1: REGISTRO")
    print("=" * 60)

    household.register_member(Member("Amanda"))
    household.set_member_income("Amanda", 133958)

    household.register_member(Member("Heri"))
    household.set_member_income("Heri", 112450)

    household.freeze_registration_state()

    categories = household.get_active_categories()
    pcts = [5000, 3000, 2000]
    percentages = {category: pct for category, pct in zip(categories, pcts)}

    household.set_budget_by_percentages(percentages=percentages)

    household.assign_distribution_method(method=MetodoReparto.EQUAL)

    contributions = household.get_current_contributions()
    members = household.members.keys()

    totals = {member: 0 for member in members}

    for cat in contributions:
        for member, amount in contributions[cat]["contributions"].items():
            totals[member] += amount

    totals_method = household.get_total_contributions_by_member()

    print(totals)
    print(totals_method)
