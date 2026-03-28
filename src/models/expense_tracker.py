from src.models.expense import Expense
from src.utils.text import normalize_name


# Se inyecta en Household
class ExpenseTracker:
    """Gestor de gastos individuales"""

    def __init__(self):
        self.expenses = []

    # ====== STORAGE ======
    def add_expense(self, expense: Expense | list) -> None:  # TODO quitar opción lista
        """Añade gasto a la colección"""
        if isinstance(expense, Expense):
            self.expenses.append(expense)

        if isinstance(expense, list):
            self.expenses.extend(expense)

    def get_all_expenses(self) -> list[Expense]:
        """Retorna todos los gastos"""
        return self.expenses.copy()

    def get_shared_expenses_by_members(self):
        """"""
        shared_expenses_by_member = {}
        for expense in self.expenses:
            if expense.is_shared:
                shared_expenses_by_member[expense.member] = (
                    shared_expenses_by_member.get(expense.member, 0) + expense.amount
                )
        return shared_expenses_by_member

    # ====== FILTERS ======
    def get_expenses_by_category(self, category: str) -> list[Expense]:
        """Filtra por categoría"""
        return [e for e in self.expenses if e.category == category]

    def get_expenses_by_member(self, member: str) -> list[Expense]:
        """Filtra por miembro"""
        normalized_member = normalize_name(member)
        return [e for e in self.expenses if e.member == normalized_member]

    # ====== AGGREGATIONS ======
    def get_total_spent(self) -> int:
        """Total gastado (céntimos)"""
        return sum(e.amount for e in self.expenses)

    def get_total_spent_by_category(self, category: str) -> int:
        """Total gastado por categoría"""
        return sum(e.amount for e in self.expenses if e.category == category)

    def get_total_spent_by_member(self, member: str) -> int:
        """Total gastado por miembro"""
        normalized_member = normalize_name(member)
        return sum(e.amount for e in self.expenses if e.member == normalized_member)

    def get_total_spent_by_member_and_category(self, member: str, category: str) -> int:
        """Cuánto gastó un miembro específico en una categoría específica"""
        normalized_member = normalize_name(member)
        return sum(
            e.amount
            for e in self.expenses
            if e.member == normalized_member and e.category == category
        )

    def get_category_breakdown(self) -> dict[str, int]:
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

            if category not in breakdown:
                breakdown[category] = 0

            breakdown[category] += amount

        return breakdown

    def get_member_breakdown(self) -> dict[str, int]:
        """Desglose por miembro

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
