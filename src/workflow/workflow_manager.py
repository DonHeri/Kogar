from src.models.member import Member
from src.models.household import Household
from src.models.expense import Expense
from src.models.constants import Phase, MetodoReparto
from src.utils.currency import to_cents, to_euros
from src.utils.text import normalize_name


class WorkflowManager:
    def __init__(self, household: Household) -> None:
        self.household = household
        self.current_phase = Phase.REGISTRATION
        self._completed_phases = {Phase.REGISTRATION}

    # ====== REGISTRATION PHASE ======
    def register_member(self, name: str):
        """Registra miembros en fase inicial"""
        self.validate_phase(Phase.REGISTRATION)
        member = Member(name)  # Member normaliza automáticamente
        self.household.register_member(member)

    def set_incomes(self, name: str, amount_eur: float):
        """Registra ingresos"""
        self.validate_phase(Phase.REGISTRATION)
        name = normalize_name(name)  # Normalizar para lookup
        amount_cents = to_cents(amount_eur)
        self.household.set_member_income(name, amount_cents)

    def finish_registration(self):
        """Validar, congelar ingresos y avanzar a planificación"""
        if not self.household.members:
            raise ValueError("Registra al menos un miembro")
        if self.household.get_total_incomes() <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos")

        # Congelar ingresos registrados
        self.household.freeze_registration_state()

        # Cambiar fase y marcarla como accesible
        self.current_phase = Phase.PLANNING
        self._completed_phases.add(Phase.PLANNING)

    # ====== PLANNING PHASE - Distribution Configuration ======
    def assign_distribution_method(self, method: MetodoReparto):
        """Configura el método de reparto (PROPORTIONAL, EQUAL, CUSTOM)"""
        self.validate_phase(Phase.PLANNING)
        self.household.assign_distribution_method(method)

    def set_custom_splits(self, splits: dict[str, float]):
        """Define porcentajes personalizados (solo para método CUSTOM)"""
        self.validate_phase(Phase.PLANNING)
        self.household.set_custom_splits(splits)

    # ====== PLANNING PHASE - Category Management ======
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

    # ====== PLANNING PHASE - Budget Assignment ======
    def set_budget_for_category(self, category: str, amount_euros: float):
        """Asigna presupuesto a categoría (recibe euros, convierte a céntimos)"""
        self.validate_phase(Phase.PLANNING)
        amount_cents = to_cents(amount_euros)
        self.household.set_budget_for_category(category, amount_cents)

    # ====== PLANNING PHASE - Contribution Queries ======
    def preview_budget_contribution_summary(self, method: MetodoReparto):
        """Preview: muestra cómo quedarían las contribuciones con un método específico"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.preview_budget_contribution_summary(method)

    def get_current_contributions(self):
        """Obtiene contribuciones con el método ya configurado (self.method)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_current_contributions()

    # ====== PLANNING PHASE - Finalization ======
    def finish_planning(self):
        """Validar presupuestos, congelar acuerdos y avanzar a mes"""
        self.validate_phase(Phase.PLANNING)

        # Validar que hay al menos una categoría con presupuesto
        categories = self.household.get_active_categories()
        if not categories:
            raise ValueError("Debe haber al menos una categoría creada")

        total_budgeted = total_budgeted = self.household.get_total_budgeted()
        if total_budgeted <= 0:
            raise ValueError("Debe asignar presupuesto a al menos una categoría")

        # Congelar estado de planificación (cachea percentages y contributions acordadas)
        self.household.freeze_planning_state()

        # Cambiar fase y marcarla como accesible
        self.current_phase = Phase.MONTH
        self._completed_phases.add(Phase.MONTH)

    # ====== MONTH PHASE - Expense Registration ======
    def register_expense(
        self, member: str, category: str, amount_euros: float, desc=""
    ):
        """Registrar un gasto"""
        self.validate_phase(Phase.MONTH)
        member_normalized = normalize_name(member)
        category = category.strip()
        desc = desc.strip()
        amount_cents = to_cents(amount_euros)
        expense = Expense(
            member=member_normalized,
            category=category,
            amount_cents=amount_cents,
            description=desc,
        )
        self.household.register_expense(expense=expense)

    # ====== QUERIES - General (Phase-independent) ======
    def get_registered_members(self) -> list[str]:
        """Muestra miembros registrados"""
        return list(self.household.members.keys())

    def get_member_income(self, name: str):
        """Obtiene ingreso de un miembro específico en céntimos"""
        name = normalize_name(name)
        if name not in self.household.members:
            raise ValueError(f"{name} does not exist")
        return self.household.members[name].monthly_income

    def get_total_incomes(self) -> int:
        """Obtiene ingreso total del hogar en céntimos"""
        return self.household.get_total_incomes()

    def get_active_categories(self) -> list[str]:
        """Obtiene lista de categorías activas"""
        return self.household.get_active_categories()

    # ====== QUERIES - Phase Summaries ======
    def get_registration_summary(self):
        """Obtiene resumen completo de registro (disponible desde REGISTRATION)"""
        self.validate_phase_accessible(Phase.REGISTRATION)
        return self.household.get_registration_summary()

    def get_planning_summary(self) -> dict:
        """Obtiene resumen completo de planificación (disponible desde PLANNING)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_planning_summary()

    def get_month_summary(self):
        """Obtiene resumen completo de month (disponible desde MONTH)"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_month_summary()

    # ====== QUERIES - Frozen Data ======
    def get_registered_incomes(self) -> dict[str, int]:
        """Obtiene ingresos congelados (disponible desde PLANNING)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_registered_incomes()

    def get_agreed_percentages(self) -> dict[str, int]:
        """Obtiene porcentajes acordados congelados (disponible desde MONTH)"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_agreed_percentages()

    def get_agreed_contributions(self):
        """Obtiene contribuciones acordadas congeladas (disponible desde MONTH)"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_agreed_contributions()

    # ====== VALIDATORS ======
    def validate_phase(self, required_phase: Phase):
        """Valida que la fase actual sea exactamente la requerida"""
        if self.current_phase != required_phase:
            raise ValueError(
                f"Operación solo permitida en fase {required_phase.value}. "
                f"Fase actual: {self.current_phase.value}"
            )

    def validate_phase_accessible(self, required_phase: Phase):
        """Valida que la fase sea accesible (actual o ya completada)"""
        if (
            self.current_phase == required_phase
            or required_phase in self._completed_phases
        ):
            return
        raise ValueError(
            f"Operación solo permitida en fase {required_phase.value} o posterior. "
            f"Fase actual: {self.current_phase.value}"
        )
