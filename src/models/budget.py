from src.models.budget_category import BudgetCategory
from src.utils.currency import to_cents
from src.models.category_library import CategoryLibrary
from src.models.subcategory_library import SubcategoryLibrary


class Budget:
    """Orquesta las diferentes categoría presupuestadas"""

    def __init__(self) -> None:
        self.categories = {
            "fijos": BudgetCategory("fijos", 0),
            "variables": BudgetCategory("variables", 0),
            "deuda": BudgetCategory("deuda", 0),
            "ahorro": BudgetCategory("ahorro", 0),
        }

    def set_budget(self, category: str, amount: float) -> None:
        """Establece un presupuesto para una categoría"""
        if category not in self.categories:
            raise ValueError("La categoría debe estar creada")
        if amount < 0:
            raise ValueError("Monto del presupuesto debe ser superior a 0")

        self.categories[category].planned_amount = to_cents(amount)

    def add_category(self): 
        """Crear categorías"""
        pass
