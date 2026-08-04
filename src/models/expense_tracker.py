from src.models.expense import Expense
from src.utils.text import normalize_name


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
    def filter_expenses(
        self,
        categories: list[str] | None = None,
        member: str | None = None,
    ) -> list[Expense]:
        """Gastos que cumplen los filtros indicados. Sin filtros, todos.

        categories: nombres de categoría; el gasto entra si su categoría está
            en la lista. Una sola categoría se pasa como lista de un elemento,
            y un subárbol entero como la lista de sus nombres — el tracker no
            sabe qué cuelga de qué, solo suma lo que le señalan.
        member: quién pagó.
        """
        expenses = self.expenses

        if categories is not None:
            expenses = [e for e in expenses if e.category.name in categories]

        if member is not None:
            normalized_member = normalize_name(member)
            expenses = [e for e in expenses if e.member == normalized_member]

        return list(expenses)

    # ====== AGGREGATIONS ======
    def get_total_spent(
        self,
        categories: list[str] | None = None,
        member: str | None = None,
    ) -> int:
        """Total gastado (céntimos) por los gastos que cumplen los filtros"""
        return sum(
            e.amount for e in self.filter_expenses(categories=categories, member=member)
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
            category = expense.category.name
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
