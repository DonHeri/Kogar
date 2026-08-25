from src.storage.budget_categories_repository import BudgetCategoryRepository
from src.storage.expense_repository import ExpenseRepository
from src.storage.connection import DatabaseConnection

from src.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER


with DatabaseConnection(
    database=DB_NAME,
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
) as conn:
    expense_repo = ExpenseRepository(conn)

    expenses = expense_repo.find_by_period(period_id=26)

    print(f"# ============================================================")
    print(f"# By period")
    print(f"# ============================================================")
    for row in expenses:
        print(row)
    print()
    print(f"# ============================================================")
    print(f"# with participants")
    print(f"# ============================================================")

    expenses = expense_repo.find_with_participants(period_id=26)
    for row in expenses:
        print(row)
