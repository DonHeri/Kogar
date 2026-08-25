from src.models.expense_tracker import ExpenseTracker
from src.models.expense import Expense

tracker = ExpenseTracker()

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

tracker.add_expense([expense_1, expense_2, expense_3, expense_4, expense_5])

# print(tracker.get_all_expenses())
print(tracker.get_shared_expenses_by_members())
