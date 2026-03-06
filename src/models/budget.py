from src.models.budget_category import BudgetCategory
from src.utils.currency import to_cents
from src.models.category_library import CategoryLibrary


class Budget:
    """Orquesta la gestión de categorías de presupuesto"""

    def __init__(self) -> None:
        self.categories = {}

    # ====== INITIALIZATION ======
    def set_standard_categories(self):
        """Establece las categorías estándar predefinidas"""
        standard_categories = CategoryLibrary.get_standards_categories()

        for name in standard_categories.keys():
            self.categories[name] = BudgetCategory(name, 0)

    # ====== CATEGORY MANAGEMENT ======
    def add_category(self, name: str):
        """Agrega una nueva categoría al presupuesto"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_active_category(normalized)
        self.categories[normalized] = BudgetCategory(normalized, 0)

        if not CategoryLibrary.is_known(normalized):
            CategoryLibrary.add_category(normalized)

    # ====== BUDGET ASSIGNMENT ======
    def set_budget(self, category: str, amount: float) -> None:
        """Establece el monto presupuestado para una categoría"""
        normalized = CategoryLibrary.normalize(category)
        self._validate_category_exists(normalized)
        self._validate_amount(amount)
        self.categories[normalized].planned_amount = to_cents(amount)

    def delete_budget_category(self, category: str) -> None:
        """Elimina una categoría del presupuesto"""
        normalized = CategoryLibrary.normalize(category)
        self._validate_category_is_deletable(normalized)
        del self.categories[normalized]

    # ====== EXPENSES ======
    def register_payment(self, category: str, member: str, amount: int) -> None:
        """Registra un pago en una categoría específica"""
        normalized = CategoryLibrary.normalize(category)
        self._validate_category_exists(normalized)
        self.categories[normalized].register_payment(member, amount)

    # ====== QUERIES ======
    def get_categories_list(self) -> list[str]:
        """Retorna lista de todas las categorías activas"""
        return list(self.categories.keys())

    def get_category_budget(self, name: str) -> int:
        """Obtiene presupuesto asignado a una categoría"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_category_exists(normalized)
        return self.categories[normalized].planned_amount

    def get_category_spent(self,name: str) -> int:
        """Obtiene gastado en una categoría"""
        normalized = CategoryLibrary.normalize(name)
        return self.categories[normalized].spent
    
    def get_category_remaining(self,name: str) -> int:
        """Obtiene lo que falta por pagar en una categoría"""
        normalized = CategoryLibrary.normalize(name)
        return self.categories[normalized].remaining()
        
    
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

    def _validate_category_exist_in_library(self, name: str) -> bool:
        """Verifica si la categoría está en la librería"""
        return CategoryLibrary.is_known(name)

    def _validate_category_is_deletable(self, category: str) -> None:
        """Valida que la categoría no tiene gastos registrados"""
        self._validate_category_exists(category)

        if self.categories[category].spent > 0:
            raise ValueError(f"La categoría {category} ya tiene pagos registrados")
