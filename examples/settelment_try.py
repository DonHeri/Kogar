from src.models.expense_tracker import ExpenseTracker
from src.models.expense import Expense
from src.models.household import Household
from src.workflow.workflow_manager import WorkflowManager
from src.models.budget import Budget
from src.models.saving_tracker import SavingTracker


# ====== SETUP BÁSICO ======
budget = Budget()
tracker = ExpenseTracker()
saving = SavingTracker()
household = Household(budget=budget, expense_tracker=tracker, saving_tracker=saving)
wm = WorkflowManager(household)

# ====== FASE: REGISTRATION ======
wm.register_member("Amanda")
wm.register_member("Heri")

wm.set_incomes("Amanda", 20000)  # 2000€
wm.set_incomes("Heri", 10000)  # 1000€
print("📋 Registration Summary:")
print(wm.get_registration_summary())

expense_1 = Expense(
    member="Heri",
    category="fijos",
    amount_cents=800,
    description="Pago Luz",
    is_shared=True,
)

expense_2 = Expense(
    member="Heri",
    category="fijos",
    amount_cents=200,
    description="Pago Internet",
    is_shared=False,
)
expense_3 = Expense(
    member="Amanda", category="variables", amount_cents=600, description="Cena"
)
expense_4 = Expense(
    member="Amanda",
    category="variables",
    amount_cents=1000,
    description="Cumple",
    is_shared=True,
)
expense_5 = Expense(
    member="Heri",
    category="variables",
    amount_cents=1500,
    description="Regalos",
    is_shared=True,
)
expense_6 = Expense(
    member="Heri",
    category="fijos",
    amount_cents=800,
    description="Pago Luz",
    is_shared=True,
)

expense_7 = Expense(
    member="Heri",
    category="fijos",
    amount_cents=20,
    description="Pago Internet",
    is_shared=False,
)
expense_8 = Expense(
    member="Amanda", category="variables", amount_cents=600, description="Cena"
)
expense_9 = Expense(
    member="Amanda",
    category="variables",
    amount_cents=1000,
    description="Cumple",
    is_shared=True,
)
expense_10 = Expense(
    member="Heri",
    category="variables",
    amount_cents=1500,
    description="Regalos",
    is_shared=True,
)

tracker.add_expense(
    [
        expense_1,
        expense_2,
        expense_3,
        expense_4,
        expense_5,
        expense_6,
        expense_7,
        expense_8,
        expense_9,
        expense_10,
    ]
)

print(f"\nSETTLEMENT")
print("-" * 50)
print(household.get_settlement())
