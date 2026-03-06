from src.models.expense import Expense


# Se inyecta en Household
class ExpenseTracker:
    """Gestor de gastos individuales"""

    def __init__(self):
        self.expenses = []

    # ====== STORAGE ======
    def add_expense(self, expense: Expense) -> None:
        """Añade gasto a la colección"""
        self.expenses.append(expense)

    def get_all_expenses(self) -> list[Expense]:
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
        """Total gastado por categoría"""
        return sum(e.amount for e in self.expenses if e.category == category)

    def get_total_spent_by_member(self, member: str) -> int:
        """Total gastado por miembro"""
        return sum(e.amount for e in self.expenses if e.member == member)

    def get_total_spent_by_member_and_category(self, member: str, category: str) -> int:
        """Cuánto gastó un miembro específico en una categoría específica"""
        return sum(
            e.amount
            for e in self.expenses
            if e.member == member and e.category == category
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
