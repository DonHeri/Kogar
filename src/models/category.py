class Category:
    def __init__(self, name: str) -> None:
        self.name = name


class AutoCalculatedCategory(Category):
    def calculate_own_budget(self, total_incomes: int, otros_budgeted: int) -> int:
        return total_incomes - otros_budgeted
