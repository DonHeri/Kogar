class Category:
    def __init__(self, name: str, is_shared: bool = True) -> None:
        self.name = name
        self.is_shared = is_shared


class AutoCalculatedCategory(Category):
    def calculate_own_budget(self, total_incomes: int, otros_budgeted: int) -> int:
        return total_incomes - otros_budgeted
