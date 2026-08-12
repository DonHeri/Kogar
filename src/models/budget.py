from src.models.budget_category import BudgetCategory
from src.models.constants import MetodoReparto
from src.models.category import AutoCalculatedCategory, Category
from src.models.category_library import CategoryLibrary
from src.models.exceptions import CeilingBelowChildrenError
from src.utils.text import normalize_name


class Budget:
    """Orquesta la gestión de categorías de presupuesto"""

    def __init__(self) -> None:
        self.categories: dict[str, BudgetCategory] = {}
        self._children: dict[str, list[str]] = {}
        self.library = CategoryLibrary()

    # ====== INITIALIZATION ======
    def set_standard_categories(self, participants: list[str]):
        """Establece las categorías estándar predefinidas('fijos','variables';
        'reserva' como almacén del sobrante para ahorro/deuda/otras categorías)"""

        for name in CategoryLibrary.get_standards_categories().keys():
            if name in self.categories:
                continue
            self.add_category(name=name, participants=participants)

    # ====== CATEGORY MANAGEMENT ======

    def add_category(
        self,
        name: str,
        participants: list[str] | None = None,
        parent: str | None = None,
        method: MetodoReparto | None = None,
        custom_splits: dict[str, int] | None = None,
    ):
        """Agrega una nueva categoría al presupuesto.

        Args:
            participants: quiénes cargan con la categoría. En una hija, None
                hereda los del padre. En una raíz no hay de quién heredar, así
                que es obligatorio: Budget no conoce a los miembros del hogar.

        Raises:
            ValueError: si una raíz llega sin participantes, o si una hija mete
                a alguien que su padre no tiene.
        """
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

            if participants is None:
                participants = self.categories[parent].participants
            else:
                self._validate_subset_of_parent(participants, parent)

            self._children.setdefault(parent, []).append(normalized)

        else:
            if not participants:
                raise ValueError(
                    "Una categoría raíz debe declarar al menos un participante"
                )

        category = self.library.create_category(normalized)

        self.categories[normalized] = BudgetCategory(
            category,
            0,
            participants,
            parent=parent,
            method=method,
            custom_splits=custom_splits,
        )

    # ====== BUDGET ASSIGNMENT ======
    def set_planned_percentage(
        self, category_name: str, percentage: int, resolved_amount_cents: int
    ):
        """Settea el peso de una categoría en porcentaje. Recibe cantidad resuelta en céntimos"""
        normalized = CategoryLibrary.normalize(category_name)
        self._validate_category_exists(normalized)
        self._validate_covers_children(
            name=normalized, amount_cents=resolved_amount_cents
        )
        self.categories[normalized].set_planned_percentage(
            percentage=percentage, resolved_amount_cents=resolved_amount_cents
        )

    def recalculate_percentage_categories(self, incomes: dict[str, int]) -> None:
        """Recalcula el techo de cada categoría con porcentaje declarado, contra el
        ingreso vivo de sus propios participantes.

        Hijas antes que raíces: así, cuando le toca a una raíz, `_validate_covers_children`
        ya ve el total actualizado de sus hijas, no el de antes de este recálculo.
        """
        children_first = sorted(
            self.categories.items(), key=lambda item: item[1].parent is None
        )
        for name, category in children_first:
            percentage = category.planned_percentage
            if percentage is None:
                continue
            participants_income = sum(
                incomes[member] for member in category.participants
            )
            resolved_amount_cents = participants_income * percentage // 10000
            self.set_planned_percentage(name, percentage, resolved_amount_cents)

    def set_split_method(self, category_name: str, method: MetodoReparto) -> None:
        """Cambia el método de reparto de una categoría ya creada."""
        normalized = CategoryLibrary.normalize(category_name)
        self._validate_category_exists(normalized)
        self.categories[normalized].set_split_method(method)

    def set_custom_splits(
        self, category_name: str, custom_splits: dict[str, int]
    ) -> None:
        """Declara los splits personalizados de una categoría; la deja en CUSTOM."""
        normalized = CategoryLibrary.normalize(category_name)
        self._validate_category_exists(normalized)
        self.categories[normalized].set_custom_splits(custom_splits)

    def add_participant_to_budget_category(
        self,
        member_name: str,
        category_name: str,
    ):
        """Añade un participante a una categoría ya creada.

        En una hija, el nuevo tiene que estar en el padre: ampliarla metería
        dinero de un tercero en una bolsa que no es suya. Ampliar un padre sí
        es libre — sus hijas siguen siendo subconjunto.
        """
        normalized = CategoryLibrary.normalize(category_name)
        self._validate_category_exists(normalized)

        parent = self.categories[normalized].parent
        if parent is not None:
            self._validate_subset_of_parent([member_name], parent)

        self.categories[normalized].add_participant(member_name)

    def set_planned_amount(self, category: str, amount_cents: int) -> None:
        """Establece el monto presupuestado para una categoría (céntimos).

        Lanza si el importe deja por debajo lo que ya han repartido sus hijas:
        un techo menor que sus hijas daría un facturable negativo y volvería a
        descuadrar el reparto entre miembros.
        """
        normalized = CategoryLibrary.normalize(category)
        self._validate_category_exists(normalized)
        self._validate_amount_cents(amount_cents)
        self._validate_covers_children(normalized, amount_cents)

        self.categories[normalized].set_fixed_amount(amount_cents)

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

    def get_child_total_planned(self, category_name: str) -> int:
        """Calcula el total planificado entre categorías hijas"""
        normalized = CategoryLibrary.normalize(category_name)
        self._validate_category_exists(normalized)

        child_planned_amount = sum(
            self.categories[child].planned_amount
            for child in self._children.get(normalized, [])
        )

        return child_planned_amount

    def get_root_categories(self) -> list[str]:
        """Nombres de las categorías raíz (sin padre)"""
        return [name for name, cat in self.categories.items() if cat.parent is None]

    def get_children(self, name: str) -> list[str]:
        """Nombres de las categorías hija que cuelgan de esta"""
        normalized = CategoryLibrary.normalize(name)
        self._validate_category_exists(normalized)
        return list(self._children.get(normalized, []))

    def get_category_billable(self, category_name: str) -> int:
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

    def _validate_subset_of_parent(self, participants: list[str], parent: str) -> None:
        """Valida que una hija no participe a nadie que su padre no tenga.

        Una hija vive dentro del techo de su padre. Si metiera a un tercero, ese
        techo dejaría de significar lo que dice, porque estaría repartiendo entre
        gente que el padre no reparte.
        """
        parent_participants = self.categories[parent].participants
        intruders = [
            name
            for name in participants
            if normalize_name(name) not in parent_participants
        ]
        if intruders:
            raise ValueError(
                f"Una subcategoría no puede añadir participantes que su padre "
                f"({parent}) no tiene: {', '.join(sorted(intruders))}. "
                f"Participantes de {parent}: {', '.join(sorted(parent_participants))}"
            )

    def _validate_covers_children(self, name: str, amount_cents: int) -> None:
        """Valida que el techo no baja por debajo de lo repartido en sus hijas"""
        children_total = self.get_child_total_planned(name)
        if amount_cents < children_total:
            raise CeilingBelowChildrenError(
                category=name, children_total_cents=children_total
            )

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
