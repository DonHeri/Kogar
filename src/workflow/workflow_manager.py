from datetime import datetime
from uuid import UUID

from src.models.constants import CategoryBehavior, MetodoReparto, Phase, SavingScope
from src.models.expense import Expense
from src.models.household import Household
from src.models.member import Member
from src.models.saving_bucket import SavingBucket
from src.utils.currency import to_cents, to_percentage_basis
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
        self.validate_phase(Phase.PLANNING)
        self.household.set_standard_categories()

    def remove_category(self, name: str):
        """Elimina categoría en PLANNING"""
        self.validate_phase(Phase.PLANNING)
        self.household.remove_category(name)

    def get_category_behavior(self, category: str):
        """Retorna el behavior de una categoría: SHARED o PERSONAL (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_category_behavior(category)

    # ====== PLANNING PHASE - Budget Assignment ======
    def set_budget_for_category(self, category: str, amount_euros: float):
        """Asigna presupuesto a categoría (recibe euros, convierte a céntimos)"""
        self.validate_phase(Phase.PLANNING)
        amount_cents = to_cents(amount_euros)
        self.household.set_budget_for_category(category, amount_cents)

    def set_budget_by_percentages(self, percentages_floats: dict[str, float]) -> None:
        """Asigna presupuesto a categoría calculando monto desde % de ingresos totales"""
        self.validate_phase(Phase.PLANNING)

        percentages_int = {}
        for category, percentage_float in percentages_floats.items():
            percentage_int = to_percentage_basis(percentage_float)
            percentages_int[category] = percentage_int

        self.household.set_budget_by_percentages(percentages=percentages_int)

    def get_budget_as_percentage(self, category: str):
        """
        Retorna qué % del ingreso total representa el presupuesto de la categoría.

        Ejemplo: Ingresos 3000€, Fijos 1500€ → retorna 5000 (50%)

        Returns:
            int: Porcentaje en basis points (5000 = 50% de ingresos)
        """
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_budget_as_percentage(category=category)

    def apply_percentage_distribution(self, percentages: dict[str, float]) -> None:
        """
        Asigna presupuestos a múltiples categorías como % del ingreso.

        IMPORTANTE: Las categorías deben existir previamente.
        Llama a set_standard_categories() o add_category() primero.

        Args:
            percentages: {category: pct} donde pct es 0-100

        Raises:
            ValueError: Si alguna categoría no existe o suma >100%
        """
        self.validate_phase(Phase.PLANNING)

        # Validar suma ≤ 100
        total_pct = sum(percentages.values())
        if total_pct > 100:
            raise ValueError(f"Los porcentajes suman {total_pct}%, máximo 100%")

        # Validar que todas las categorías existen ANTES de aplicar
        active_categories = self.household.get_active_categories()
        missing = [cat for cat in percentages.keys() if cat not in active_categories]
        if missing:
            raise ValueError(
                f"Categorías no existen: {missing}. Llama a add_category() primero."
            )

        # Aplicar (ahora seguro que todas existen). Reserva se autocalcula.
        total_incomes = self.household.get_total_incomes()
        for category, pct in percentages.items():
            if category == "reserva":
                continue
            pct_basis = to_percentage_basis(pct)
            amount_cents = (total_incomes * pct_basis) // 10000
            self.household.set_budget_for_category(category, amount_cents)

    # ====== SET SAVING GOAL  ======
    def set_member_saving_goal(self, member: str, amount_euros: float) -> None:
        """Declara el ahorro personal de un miembro (PLANNING)"""
        self.validate_phase(Phase.PLANNING)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        self.household.set_member_saving_goal(member, amount_cents)

    def get_saving_goal_status(self, member_name):
        self.validate_phase_accessible(Phase.PLANNING)
        member = normalize_name(member_name)
        return self.household.get_saving_goal_status(member)

    # ====== SET DEBT - Declarar deuda para cada miembro ======
    def set_member_debt(self, member: str, amount_euros: float) -> None:
        """Declara la deuda personal mensual de un miembro (PLANNING)"""
        self.validate_phase(Phase.PLANNING)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        self.household.set_member_debt(member, amount_cents)

    def auto_assign_saving_goals(self):
        self.validate_phase(Phase.PLANNING)
        return self.household.auto_assign_saving_goals()

    def register_debt_payment(self, member, amount_euros, description="", date=None):
        self.validate_phase(Phase.MONTH)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        self.household.register_debt_payment(member, amount_cents, description, date)

    def get_debt_status(self, member_name):
        self.validate_phase_accessible(Phase.PLANNING)
        member = normalize_name(member_name)
        return self.household.get_debt_status(member_name=member)

    def get_all_debts(self) -> dict[str, int]:
        """Retorna {member: deuda_comprometida_céntimos} (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_member_debts()

    def get_all_saving_goals(self) -> dict[str, int]:
        """Retorna {member: ahorro_comprometido_céntimos} (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_saving_goals()

    def get_debt_history(self, member: str) -> list:
        """Historial completo de pagos de deuda de un miembro (MONTH+)"""
        self.validate_phase_accessible(Phase.MONTH)
        member = normalize_name(member)
        return self.household.get_debt_history(member)

    # ====== PLANNING PHASE - Contribution Queries ======
    def get_category_budget(self, category_name: str) -> int:
        """Consultar presupuesto asignado a una categoría específica"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_category_budget(category=category_name)

    def get_total_budgeted(self) -> int:
        """Total presupuestado (suma de todas las categorías)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_total_budgeted()

    def preview_budget_contribution_summary(self, method: MetodoReparto):
        """Preview: muestra cómo quedarían las contribuciones con un método específico"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.preview_budget_contribution_summary(method)

    def get_current_contributions(self):
        """Obtiene contribuciones con el método ya configurado (self.method)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_current_contributions()

    def get_missing_money(self) -> int:
        """Dinero no presupuestado total (ingresos - presupuesto)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_missing_money()

    def get_missing_money_by_member(self, member_name: str) -> int:
        """Dinero no presupuestado de un miembro según su porcentaje"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_missing_money_by_member(member_name)

    def validate_debt_and_saving_dont_exceed_capacity(self):
        self.validate_phase(Phase.PLANNING)
        return self.household.validate_debt_and_saving_dont_exceed_capacity()

    # ====== PLANNING PHASE - Finalization ======
    def finish_planning(self):
        """Validar presupuestos, congelar acuerdos y avanzar a mes"""
        self.validate_phase(Phase.PLANNING)

        # Validar que hay al menos una categoría con presupuesto
        categories = self.household.get_active_categories()
        if not categories:
            raise ValueError("Debe haber al menos una categoría creada")

        total_budgeted = self.household.get_total_budgeted()
        if total_budgeted <= 0:
            raise ValueError("Debe asignar presupuesto a al menos una categoría")

        self.household.validate_debt_and_saving_dont_exceed_capacity()

        # Congelar estado de planificación (cachea percentages y contributions acordadas)
        self.household.freeze_planning_state()
        # Cambiar fase y marcarla como accesible
        self.current_phase = Phase.MONTH
        self._completed_phases.add(Phase.MONTH)

    # ====== MONTH PHASE - Expense Registration ======

    def register_expense(
        self,
        member: str,
        category: str,
        amount_euros: float,
        desc: str = "",
        is_shared: bool | None = None,
    ):
        """Registrar un gasto.

        is_shared: si None, se deriva del CategoryBehavior de la categoría.
        Pasarlo explícitamente sobreescribe el default.
        """
        self.validate_phase(Phase.MONTH)
        member_normalized = normalize_name(member)
        category = category.strip()
        desc = desc.strip()
        amount_cents = to_cents(amount_euros)

        if is_shared is None:
            behavior = self.household.get_category_behavior(category)
            is_shared = behavior == CategoryBehavior.SHARED

        expense = Expense(
            member=member_normalized,
            category=category,
            amount_cents=amount_cents,
            description=desc,
            is_shared=is_shared,
        )
        self.household.register_expense(expense=expense)

    def finish_month(self):
        """Avanzar de MONTH a CLOSING"""
        self.validate_phase(Phase.MONTH)
        self.current_phase = Phase.CLOSING
        self._completed_phases.add(Phase.CLOSING)

    # ====== PLANNING PHASE - SAVING ======

    def register_savings_deposit(
        self,
        member: str,
        amount_euros: float,
        destination: SavingScope,
        description: str = "",
        date=None,
    ) -> None:
        """Registra un depósito en la cuenta de ahorro de un miembro (MONTH)"""
        self.validate_phase(Phase.MONTH)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        self.household.register_savings_deposit(
            member, amount_cents, destination, description, date
        )

    def register_savings_withdrawal(
        self,
        member: str,
        amount_euros: float,
        destination: SavingScope,
        description: str = "",
        date=None,
    ) -> None:
        """Registra un retiro de la cuenta de ahorro de un miembro (MONTH)"""
        self.validate_phase(Phase.MONTH)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        self.household.register_savings_withdrawal(
            member, amount_cents, destination, description, date
        )

    def get_member_savings_summary(self, member: str) -> dict:
        """Retorna resumen de ahorro de un miembro (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        member = normalize_name(member)
        return self.household.get_member_savings_summary(member)

    def get_savings_total_shared(self) -> int:
        """Total ahorrado en fondo compartido por todos los miembros (MONTH+)"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_savings_total_shared()

    def get_savings_shared_by_month(self, month: int, year: int) -> dict:
        """Movimientos compartidos por mes/año → {member: [SavingEntry]} (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_savings_shared_by_month(month, year)

    # ====== Saving Bucket ======
    def create_saving_bucket(
        self,
        bucket_name: str,
        goal_euros: float,
        scope: SavingScope,
        owners: list,
        deadline: datetime | None = None,
        description: str = "",
    ) -> UUID:
        """Crea y registra un nuevo bucket. Retorna su UUID."""
        self.validate_phase_accessible(Phase.PLANNING)
        goal_cents = to_cents(goal_euros)
        bucket_name = bucket_name.strip()
        description.strip()
        owners = [normalize_name(name) for name in owners]

        bucket = SavingBucket(
            bucket_name, goal_cents, scope, owners, deadline, description
        )

        bucket_id = self.household.add_saving_bucket(bucket)

        return bucket_id

    def deposit_to_bucket(
        self, bucket_id: UUID, member: str, amount_euros: float, date=None
    ) -> None:
        """Registra un depósito en un bucket (MONTH)"""
        self.validate_phase(Phase.MONTH)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        self.household.deposit_to_bucket(bucket_id, member, amount_cents, date)

    def withdraw_from_bucket(
        self, bucket_id: UUID, member: str, amount_euros: float, date=None
    ) -> None:
        """Registra un retiro de un bucket (MONTH)"""
        self.validate_phase(Phase.MONTH)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        self.household.withdraw_from_bucket(bucket_id, member, amount_cents, date)

    def get_bucket_by_id(self, bucket_id: UUID):
        """Obtiene un bucket por su UUID (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_bucket_by_id(bucket_id)

    def get_all_buckets(self):
        """Obtiene todos los buckets del hogar (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_all_buckets()

    def get_buckets_by_member(self, member: str):
        """Obtiene buckets en los que participa un miembro (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        member = normalize_name(member)
        return self.household.get_buckets_by_member(member)

    # ====== MONTH PHASE - member balance Queries ======
    def get_member_owed_total(self, member_name: str) -> int:
        """Cuánto debe pagar un miembro según el acuerdo"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_member_owed_total(member_name)

    def get_member_paid_total(self, member_name: str) -> int:
        """Total pagado por un miembro"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_member_paid_total(member_name)

    def get_member_balance(self, member_name: str) -> int:
        """Balance del miembro (pagado - debido)"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_member_balance(member_name)

    def get_member_status(self, member_name: str) -> dict:
        """Retorna dict: {income, owed, paid, balance, contributions_by_category}"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_member_status(member_name)

    # ====== MONTH PHASE - Category spent Queries ======
    def get_category_spent(self, category_name: str) -> int:
        """Cuánto se ha gastado en una categoría"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_category_spent(category_name)

    def get_total_spent(self) -> int:
        """Total gastado en el mes"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_total_spent()

    def get_category_remaining(self, category_name: str) -> int:
        """Cuánto queda por gastar en una categoría (presupuesto - gastado)"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_category_remaining(category_name)

    def get_total_remaining(self) -> int:
        """Total restante por pagar (presupuesto - gastado)"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_total_remaining()

    def get_settlement(self) -> list[dict]:
        """Transferencias mínimas para saldar gastos compartidos entre miembros"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_settlement()

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
