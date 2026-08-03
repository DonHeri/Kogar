from src.models.budget_category import BudgetCategory
from src.models.category import AutoCalculatedCategory, Category
from src.models.category_library import CategoryLibrary
from src.utils.currency import to_cents


class Budget:
    """Orquesta la gestión de categorías de presupuesto"""

    def __init__(self) -> None:
        self.categories: dict[str, BudgetCategory] = {}
        self._children: dict[str, list[str]] = {}
        self.library = CategoryLibrary()

    # ====== INITIALIZATION ======
    def set_standard_categories(self):
        """Establece las categorías estándar predefinidas('fijos','variables';
        'reserva' como almacén del sobrante para ahorro/deuda/otras categorías)"""

        for name in CategoryLibrary.get_standards_categories().keys():
            if name in self.categories:
                continue
            self.add_category(name=name)

    # ====== CATEGORY MANAGEMENT ======

    def add_category(
        self, name: str, parent: str | None = None, is_shared: bool | None = None
    ):
        """Agrega una nueva categoría al presupuesto"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_active_category(normalized)

        if not self.library.is_known(normalized):
            self.library.add_category(normalized)

        if parent is not None:
            parent = CategoryLibrary.normalize(parent)
            self._validate_category_exists(parent)

            if self.validate_category_is_child(parent):
                raise ValueError(
                    "Solo se permiten 2 niveles de profundidad: "
                    "una categoría hija no puede ser padre"
                )
            is_shared = self.categories[parent].is_shared
            category = self.library.create_category(normalized, is_shared=is_shared)

            self._children.setdefault(parent, []).append(normalized)

        else:
            category = self.library.create_category(normalized, is_shared=is_shared)

        self.categories[normalized] = BudgetCategory(category, 0, parent=parent)

    # ====== BUDGET ASSIGNMENT ======
    def set_planned_amount(self, category: str, amount_cents: int) -> None:
        """Establece el monto presupuestado para una categoría (céntimos)"""
        normalized = CategoryLibrary.normalize(category)
        self._validate_category_exists(normalized)
        self._validate_amount_cents(amount_cents)
        self.categories[normalized].planned_amount = amount_cents

    def delete_budget_category(self, category_name: str) -> None:
        """Elimina una categoría del presupuesto.

        Lanza si tiene hijas: promoverlas a raíz metería su importe a competir
        contra el ingreso y le cambiaría el presupuesto al usuario sin que lo
        pida. Se borran o se mueven ellas primero.

        El destino de los gastos no se decide aquí — Budget no los conoce. Eso
        lo resuelve Household antes de llamar.
        """
        normalized = CategoryLibrary.normalize(category_name)
        self._validate_category_exists(normalized)
        self._validate_has_no_children(normalized)

        parent = self.categories[normalized].parent
        del self.categories[normalized]
        self._detach_from_parent(name=normalized, parent=parent)

    def _detach_from_parent(self, name: str, parent: str | None) -> None:
        """Saca el nombre del índice de  hijas de su padre"""
        if parent is None:
            return

        siblings = self._children.get(parent, [])
        if name in siblings:
            siblings.remove(name)
        if not siblings:
            self._children.pop(parent, None)

    # ====== QUERIES ======
    def get_budget_categories(self) -> dict[str, BudgetCategory]:
        """Retorna todas las categoría con presupuesto activas"""
        return self.categories.copy()

    def get_budget_category(self, name: str) -> BudgetCategory:
        """Retorna la categoría con su presupuesto"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_category_exists(normalized)
        budget_category = self.categories[normalized]
        return budget_category

    def get_category_names(self) -> list[str]:
        """Retorna lista de todas las categorías activas"""
        return list(self.categories.keys())

    def get_planned_amount(self, name: str) -> int:
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

    def get_auto_calculated_category(self) -> AutoCalculatedCategory:
        """Retorna la categoría auto-calculada (reserva). Falla si no existe."""
        for budget_category in self.categories.values():
            if isinstance(budget_category.category, AutoCalculatedCategory):
                return budget_category.category
        raise ValueError("No hay categoría auto-calculada en el presupuesto")

    def get_child_total_planned(self, category: str) -> int:
        """Calcula el total planificado entre categorías hijas"""
        normalized = CategoryLibrary.normalize(category)
        self._validate_category_exists(normalized)

        child_planned_amount = sum(
            self.categories[child].planned_amount
            for child in self._children.get(normalized, [])
        )

        return child_planned_amount

    def get_children(self, name: str) -> list[str]:
        """Nombres de las categorías hija que cuelgan de esta"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_category_exists(normalized)
        return list(self._children.get(normalized, []))

    def get_billable_amount(self, category_name: str) -> int:
        """Parte del presupuesto que se reparte entre los miembros: el planificado
        menos lo delegado a sus hijas. En una hoja, su planificado entero."""
        normalized = CategoryLibrary.normalize(category_name)
        self._validate_category_exists(normalized)

        billable = self.get_planned_amount(normalized) - self.get_child_total_planned(
            normalized
        )

        return billable

    # ====== VALIDATORS ======
    def validate_category_is_child(self, name: str) -> bool:
        normalized = CategoryLibrary.normalize(name)
        return self.categories[normalized].parent is not None

    def _validate_active_category(self, name: str) -> None:
        """Valida que la categoría no existe (para agregar nueva)"""
        if name in self.categories:
            raise ValueError(f"La categoría ya existe")

    def _validate_has_no_children(self, name: str) -> None:
        """Valida que la categoría no deja hijas colgando (para borrar)"""
        children = self._children.get(name, [])
        if children:
            raise ValueError(
                f"La categoría {name} tiene subcategorías ({', '.join(children)}). "
                "Bórralas o muévelas antes de borrarla."
            )

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
