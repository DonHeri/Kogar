from src.models.expense import Expense
from src.models.category_library import CategoryLibrary
from datetime import datetime


# Se inyecta en Household
class ExpensesTracker:
    """Gestor de gastos individuales"""

    def __init__(self):
        self.expenses = []

    # ====== STORAGE ======
    def add_expense(self, expense: Expense) -> None:
        """Añade gasto a la colección"""
        self.expenses.append(expense)

    def get_all_expenses(self) -> list:
        """Retorna todos los gastos"""
        return self.expenses.copy()

    # ====== FILTERS ======
    def get_expenses_by_category(self, category: str) -> list[Expense]:
        """Filtra por categoría"""
        return [e for e in self.expenses if e.category == category]

    def get_expenses_by_member(self, member: str) -> list[Expense]:
        """Filtra por miembro"""
        return [e for e in self.expenses if e.member == member]

    # ====== AGGREGATIONS ======
    def get_total_spent(self) -> int:
        """Total gastado (céntimos)"""
        return sum(e.amount for e in self.expenses)

    def get_total_spent_by_category(self, category: str) -> int:
        """Total por categoría"""
        return sum(e.amount for e in self.expenses if e.category == category)

    def get_total_spent_by_member(self, member: str) -> int:
        """Total por miembro"""
        return sum(e.amount for e in self.expenses if e.member == member)

    def get_category_breakdown(self):
        """Desglose por categoría

        Retorna:
        {
            "category" : total_spent(cents),
            "category_2" : total_spent(cents),
        }
        """
        breakdown = {}

        for expense in self.expenses:
            category = expense.category
            amount = expense.amount

            if expense.category not in breakdown:
                breakdown[expense.category] = 0

            breakdown[category] += amount

        return breakdown

    def get_member_breakdown(self) -> dict[str, int]:
        """Desglose por categoría

        Retorna:
        {
            "member" : total_spent(cents),
            "member_2" : total_spent(cents),
        }
        """
        breakdown = {}
        for expense in self.expenses:
            if expense.member not in breakdown:
                breakdown[expense.member] = 0
            breakdown[expense.member] += expense.amount
        return breakdown
