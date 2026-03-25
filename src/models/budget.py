from src.models.budget_category import BudgetCategory
from src.utils.currency import to_cents
from src.models.category_library import CategoryLibrary


class Budget:
    """Orquesta la gestión de categorías de presupuesto"""

    def __init__(self) -> None:
        self.categories = {}
        self.library = CategoryLibrary()

    # ====== INITIALIZATION ======
    def set_standard_categories(self):
        """Establece las categorías estándar predefinidas"""
        for name in CategoryLibrary.get_standards_categories().keys():
            behavior = self.library.get_default_behavior(name)
            self.categories[name] = BudgetCategory(name, 0, behavior)

    # ====== CATEGORY MANAGEMENT ======
    def add_category(self, name: str):
        """Agrega una nueva categoría al presupuesto"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_active_category(normalized)
        behavior = self.library.get_default_behavior(normalized)
        self.categories[normalized] = BudgetCategory(normalized, 0, behavior)

        if not self.library.is_known(normalized):
            self.library.add_category(normalized)

    # ====== BUDGET ASSIGNMENT ======
    def set_budget(self, category: str, amount_cents: int) -> None:
        """Establece el monto presupuestado para una categoría (céntimos)"""
        normalized = CategoryLibrary.normalize(category)
        self._validate_category_exists(normalized)
        self._validate_amount_cents(amount_cents)
        self.categories[normalized].planned_amount = amount_cents

    def delete_budget_category(self, category: str) -> None:
        """Elimina una categoría del presupuesto"""
        normalized = CategoryLibrary.normalize(category)
        self._validate_category_exists(normalized)
        del self.categories[normalized]

    # ====== QUERIES ======
    def get_categories_list(self) -> list[str]:
        """Retorna lista de todas las categorías activas"""
        return list(self.categories.keys())

    def get_category_budget(self, name: str) -> int:
        """Obtiene presupuesto asignado a una categoría"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_category_exists(normalized)
        return self.categories[normalized].planned_amount

    def get_total_budgeted(self) -> int:
        """Obtiene total presupuestado"""
        return sum(cat.planned_amount for cat in self.categories.values())

    # ====== VALIDATORS ======
    def _validate_active_category(self, name: str) -> None:
        """Valida que la categoría no existe (para agregar nueva)"""
        if name in self.categories:
            raise ValueError(f"La categoría ya existe")

    def _validate_category_exists(self, name: str) -> None:
        """Valida que la categoría existe (para modificar)"""
        if name not in self.categories:
            raise ValueError(f"La categoría debe estar creada")

    def _validate_amount(self, amount: float) -> None:
        """Valida que el monto sea válido (>= 0)"""
        if amount < 0:
            raise ValueError("Monto del presupuesto debe ser superior a 0")

    def _validate_amount_cents(self, amount_cents: int) -> None:
        """Valida que el monto en céntimos sea válido (>= 0)"""
        if amount_cents < 0:
            raise ValueError("Monto del presupuesto debe ser superior a 0")

    def _validate_category_exist_in_library(self, name: str) -> bool:
        """Verifica si la categoría está en la librería"""
        return self.library.is_known(name)
