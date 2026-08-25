from datetime import date, datetime
from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.workflow.workflow_manager import WorkflowManager


def nuevo_wm():
    return WorkflowManager(
        Household(
            Budget(), ExpenseTracker(), SavingBucketTracker(), DebtBucketTracker()
        )
    )

wm = nuevo_wm(); wm.start_new_month()
wm.register_member("Amanda"); wm.set_member_incomes("Amanda", 6000)
wm.register_member("Heri");   wm.set_member_incomes("Heri", 4000)
wm.set_budget_for_category("fijos", 1000)
wm.finish_planning()

print(wm.get_agreed_percentages())   # {'amanda': 6000, 'heri': 4000} ← congelado aquí
print(wm.get_incomes())              # ingresos vivos (antes: get_registered_incomes)