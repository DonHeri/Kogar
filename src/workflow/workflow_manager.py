from src.models.member import Member
from src.models.household import Household
from src.models.expense import Expense
from src.models.constants import Phase, MetodoReparto
from src.utils.currency import to_cents, to_euros


class WorkflowManager:
    def __init__(self, household: Household) -> None:
        self.household = household
        self.current_phase = Phase.REGISTRATION

    # ====== FASE REGISTRO ======
    # En esta fase registramos a los usuarios
    def register_member(self, name: str):
        """Registra miembros en fase inicial"""
        self.validate_phase(Phase.REGISTRATION)
        name = name.strip()
        member = Member(name)
        self.household.register_member(member)

    # Ingresamos salarios
    def set_incomes(self, name: str, amount_eur: float):
        """Registra ingresos"""
        self.validate_phase(Phase.REGISTRATION)
        amount_cents = to_cents(amount_eur)
        self.household.set_member_income(name, amount_cents)

    # Si hay miembros e ingresos > 0; cambiamos de fase
    def finish_registration(self):
        """Validar y avanzar a planificación"""
        if not self.household.members:
            raise ValueError("Registra al menos un miembro")
        if self.household.get_total_incomes() <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos")

        # Cambiar fase
        self.current_phase = Phase.PLANNING

    # ====== FASE PLANIFICACIÓN ======

    def assign_distribution_method(self, method: MetodoReparto):
        self.household.assign_distribution_method(method)

    def add_category(self, name: str):
        """Crea categoría en PLANNING"""
        self.validate_phase(Phase.PLANNING)
        self.household.add_category(name)

    def set_standard_categories(self):
        """Establece categorías estándar [fijos,variables,deuda,ahorro]"""
        self.household.set_standard_categories()

    def remove_category(self, name: str):
        """Elimina categoría en PLANNING"""
        self.validate_phase(Phase.PLANNING)
        self.household.remove_category(name)

    def set_budget_for_category(self, category: str, amount: float):
        """Asigna presupuesto a categoría"""
        self.validate_phase(Phase.PLANNING)
        self.household.set_budget_for_category(category, amount)

    def finish_planning(self):
        """Validar presupuestos y avanzar a mes"""
        self.validate_phase(Phase.PLANNING)

        # Validar que hay al menos una categoría con presupuesto
        categories = self.household.get_active_categories()
        if not categories:
            raise ValueError("Debe haber al menos una categoría creada")

        total_budgeted = sum(
            self.household.budget.categories[cat].planned_amount for cat in categories
        )
        if total_budgeted <= 0:
            raise ValueError("Debe asignar presupuesto a al menos una categoría")

        # Cambiar fase
        self.current_phase = Phase.MONTH

    # ====== FASE MONTH ======
    def register_expense(
        self, member: str, category: str, amount_euros: float, desc=""
    ):
        """Registrar un gasto"""
        self.validate_phase(Phase.MONTH)
        member = member.strip()
        category = category.strip()
        desc = desc.strip()
        amount_cents = to_cents(amount_euros)
        expense = Expense(
            member=member,
            category=category,
            amount_cents=amount_cents,
            description=desc,
        )
        self.household.register_expense(expense=expense)

    # ====== FASE CIERRE ======

    # ==================== QUERIES (Phase-independent) ====================
    def get_registered_members(self) -> list[str]:
        """Muestra miembros registrados"""
        return list(self.household.members.keys())

    def get_member_income(self, name: str):
        """Get a specific member incomes in cents (available in all phases)"""
        if name not in self.household.members:
            raise ValueError(f"{name} does not exist")

        return self.household.members[name].monthly_income

    def get_total_incomes(self) -> int:
        """Get total household income in cents (available in all phases)"""
        return self.household.get_total_incomes()

    def get_active_categories(self) -> list[str]:
        """Ve categorías activas"""
        return self.household.get_active_categories()

    def get_planning_summary(self) -> dict:
        """Obtiene resumen completo de planificación (disponible en PLANNING)"""
        self.validate_phase(Phase.PLANNING)
        return self.household.get_planning_summary()

    # ====== HELPERS ======
    def validate_phase(self, required_phase: Phase):
        if self.current_phase != required_phase:
            raise ValueError(
                f"Operación solo permitida en fase {required_phase.value}. "
                f"Fase actual: {self.current_phase.value}"
            )
