from src.models.budget_category import BudgetCategory
from src.models.category import AutoCalculatedCategory, Category
from src.models.category_library import CategoryLibrary
from src.utils.currency import to_cents


class Budget:
    """Orquesta la gestión de categorías de presupuesto"""

    def __init__(self) -> None:
        self.categories = {}
        self.library = CategoryLibrary()

    # ====== INITIALIZATION ======
    def set_standard_categories(self):
        """Establece las categorías estándar predefinidas"""
        for name in CategoryLibrary.get_standards_categories().keys():
            category = self.library.create_category(name)
            self.categories[name] = BudgetCategory(category, 0, parent=None)

    # ====== CATEGORY MANAGEMENT ======
    def add_category(self, name: str, parent: str | None = None):
        """Agrega una nueva categoría al presupuesto"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_active_category(normalized)

        if not self.library.is_known(normalized):
            self.library.add_category(normalized)

        if parent is not None:
            parent = CategoryLibrary.normalize(parent)
            self._validate_category_exists(parent)

        category = self.library.create_category(normalized)
        self.categories[normalized] = BudgetCategory(category, 0, parent=parent)

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
        """Obtiene total presupuestado en las categorías raíces. Las categorías hijas viven dentro del techo de la categoría padre"""
        return sum(
            cat.planned_amount for cat in self.categories.values() if cat.parent is None
        )

    def get_category(self, name: str) -> Category:
        """Obtiene el objeto Category de una categoría activa"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_category_exists(normalized)
        return self.categories[normalized].category

    def get_auto_calculated_category(self) -> Category:
        """Retorna la categoría auto-calculada (reserva). Falla si no existe."""
        for budget_category in self.categories.values():
            if isinstance(budget_category.category, AutoCalculatedCategory):
                return budget_category.category
        raise ValueError("No hay categoría auto-calculada en el presupuesto")

    def category_is_child(self, name: str) -> bool:
        return self.categories[name].parent is not None

    def get_child_total_planned(self, category: str) -> int:
        """Calcula el total planificado entre categorías hijas"""
        normalized = CategoryLibrary.normalize(category)
        self._validate_category_exists(category)

        if self.category_is_child(normalized):
            parent = self.categories[normalized].parent
        else:
            parent = normalized

        child_planned_amount = sum(
            cat.planned_amount
            for cat in self.categories.values()
            if cat.parent == parent
        )

        return child_planned_amount

    # ====== VALIDATORS ======

    def _validate_active_category(self, name: str) -> None:
        """Valida que la categoría no existe (para agregar nueva)"""
        if name in self.categories:
            raise ValueError(f"La categoría ya existe")

    def _validate_category_exists(self, name: str) -> None:
        """Valida que la categoría existe (para modificar)"""
        if name not in self.categories:
            raise ValueError(f"La categoría debe estar creada")

    def _validate_amount_cents(self, amount_cents: int) -> None:
        """Valida que el monto en céntimos sea válido (>= 0)"""
        if amount_cents < 0:
            raise ValueError("Monto del presupuesto debe ser superior a 0")

    def _validate_category_exist_in_library(self, name: str) -> bool:
        """Verifica si la categoría está en la librería"""
        return self.library.is_known(name)
