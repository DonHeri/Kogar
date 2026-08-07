from datetime import date, datetime
from uuid import UUID

from src.storage.member_repository import MemberRepository
from src.storage.household_repository import HouseholdRepository
from src.storage.period_repository import PeriodRepository
from src.storage.expense_repository import ExpenseRepository
from src.storage.debt_entry_repository import DebtEntryRepository
from src.storage.saving_bucket_repository import SavingBucketRepository
from src.storage.saving_bucket_entry_repository import SavingBucketEntryRepository
from src.storage.budget_categories_repository import BudgetCategoryRepository

from src.models.period import Period

from src.models.category import Category
from src.models.constants import MetodoReparto, Phase
from src.models.expense import Expense
from src.models.household import Household
from src.models.member import Member
from src.models.saving_bucket import SavingBucket
from src.models.debt_bucket import DebtBucket
from src.utils.currency import to_cents, to_percentage_basis
from src.utils.dates import add_months
from src.utils.text import normalize_name
from src.workflow.budget_distribution_service import BudgetDistributionService
from src.workflow.settlement_calculator import SettlementCalculator
from src.workflow.summary_service import SummaryService


class WorkflowManager:
    def __init__(
        self,
        household: Household,
        household_repo: HouseholdRepository | None = None,
        member_repo: MemberRepository | None = None,
        period_repo: PeriodRepository | None = None,
        expense_repo: ExpenseRepository | None = None,
        debt_repo: DebtEntryRepository | None = None,
        saving_bucket_entry_repo: SavingBucketEntryRepository | None = None,
        saving_bucket_repo: SavingBucketRepository | None = None,
        budget_categories_repository: BudgetCategoryRepository | None = None,
    ) -> None:
        self.household = household
        self.current_phase = Phase.PLANNING
        self._completed_phases = {Phase.PLANNING}
        self.household_repo = household_repo
        self.member_repo = member_repo
        self.period_repo = period_repo
        self.expense_repo = expense_repo
        self.debt_repo = debt_repo
        self.saving_bucket_entry_repo = saving_bucket_entry_repo
        self.saving_bucket_repo = saving_bucket_repo
        self.budget_categories_repository = budget_categories_repository
        self.period_id: int | None = None
        self.period: Period | None = None
        self.household_id: int | None = None
        self.member_ids: dict[str, int] = {}  # nombre_normalizado → id BD

    # ====== PLANNING PHASE - Miembros e ingresos ======
    def register_member(self, name: str):
        """Registra un miembro. Se puede hacer mientras se planifica el período."""
        self.validate_phase(Phase.PLANNING)
        member = Member(name)  # Member normaliza automáticamente
        self.household.register_member(member)
        self._persist_new_members()

    def set_member_incomes(self, name: str, amount_euros: float):
        """Cambia el ingreso de un miembro.

        Se puede hacer durante toda la planificación: el reparto se recalcula sobre
        el ingreso vivo hasta que finish_planning congela el acuerdo del período.
        """
        self.validate_phase(Phase.PLANNING)
        name = normalize_name(name)  # Normalizar para lookup
        amount_cents = to_cents(amount_euros)
        self.household.set_member_income(name, amount_cents)

        if self.member_repo and name in self.member_ids:
            self.member_repo.change_incomes(
                member_id=self.member_ids[name], new_incomes_cents=amount_cents
            )

    # ====== PLANNING PHASE - Distribution Configuration ======
    def assign_distribution_method(self, method: MetodoReparto):
        """Configura el método de reparto (PROPORTIONAL, EQUAL, CUSTOM)"""
        self.validate_phase(Phase.PLANNING)
        self.household.assign_distribution_method(method)

        if self.period_repo and self.period_id:
            self.period_repo.update_method(self.period_id, method)

    def set_custom_splits(self, splits: dict[str, float]):
        """Define porcentajes personalizados 0-100 (solo para método CUSTOM)"""
        self.validate_phase(Phase.PLANNING)
        splits_basis_points = {
            name: to_percentage_basis(pct) for name, pct in splits.items()
        }
        self.household.set_custom_splits(splits_basis_points)

    # ====== PLANNING PHASE - Category Management ======
    def add_category(
        self,
        name: str,
        parent: str | None = None,
        budget_euros: float | None = None,
    ):
        """Crea categoría en PLANNING, con su importe si se indica.

        `budget_euros` opcional: crear una categoría con presupuesto es una sola
        llamada desde fuera, no dos. Sin él la categoría nace con techo 0, que es
        el comportamiento de siempre.
        """
        self.validate_phase(Phase.PLANNING)
        parent = normalize_name(parent) if parent else None
        self.household.add_category(name, parent=parent)

        if budget_euros is None:
            return

        BudgetDistributionService.set_budget_for_category(
            self.household, name, to_cents(budget_euros)
        )

    def set_standard_categories(self):
        """Establece categorías estándar [fijos,variables,deuda,ahorro]"""
        self.validate_phase(Phase.PLANNING)
        self.household.set_standard_categories()

    def remove_category(self, name: str):
        """Elimina categoría en PLANNING"""
        self.validate_phase(Phase.PLANNING)
        self.household.remove_category(name)

    def _resolve_category(self, name: str) -> Category:
        """Traduce el nombre (string del exterior) al objeto Category vivo del presupuesto."""
        return self.household.budget.get_category(name)

    # ====== PLANNING PHASE - Budget Assignment ======
    def set_budget_for_category(self, category: str, amount_euros: float):
        """Asigna presupuesto a categoría (recibe euros, convierte a céntimos)"""
        self.validate_phase(Phase.PLANNING)
        amount_cents = to_cents(amount_euros)
        BudgetDistributionService.set_budget_for_category(
            self.household, category, amount_cents
        )

    def set_budget_by_percentages(self, percentages_floats: dict[str, float]) -> None:
        """Asigna presupuesto a categoría calculando monto desde % de ingresos totales.

        Raises:
            ValueError: Si la suma de porcentajes supera el 100%
        """
        self.validate_phase(Phase.PLANNING)

        total_pct = sum(percentages_floats.values())
        if total_pct > 100:
            raise ValueError(f"Los porcentajes suman {total_pct}%, máximo 100%")

        percentages_int = {}
        for category, percentage_float in percentages_floats.items():
            percentage_int = to_percentage_basis(percentage_float)
            percentages_int[category] = percentage_int

        BudgetDistributionService.set_budget_by_percentages(
            self.household, percentages=percentages_int
        )

    def get_budget_as_percentage(self, category: str):
        """
        Retorna qué % del ingreso total representa el presupuesto de la categoría.

        Ejemplo: Ingresos 3000€, Fijos 1500€ → retorna 5000 (50%)

        Returns:
            int: Porcentaje en basis points (5000 = 50% de ingresos)
        """
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_budget_as_percentage(category=category)

    # ====== PLANNING PHASE — SAVING & DEBT ======
    def get_saving_status(self, member: str) -> dict:
        """Resumen de ahorro de un miembro en el período: buckets + totales (PLANNING+).
        Informativo — nada aquí es una obligación, ver Household.get_saving_status."""
        self.validate_phase_accessible(Phase.PLANNING)
        member = normalize_name(member)
        start_date, end_date = self._current_period_range()
        return self.household.get_saving_status_by_member(member, start_date, end_date)

    def get_saving_requirement_by_member(self, member: str) -> int:
        """Cuánto exigirían las metas del miembro este mes (informativo, snapshot de hoy)."""
        self.validate_phase_accessible(Phase.PLANNING)
        member = normalize_name(member)
        return self.household.get_saving_requirement_by_member(member)

    def add_debt_bucket(
        self,
        name: str,
        principal_euros: float,
        owner: str,
        installment_euros: float,
        start_date=None,
        description: str = "",
    ) -> UUID:
        """Declara una deuda personal (PLANNING+). Convierte euros→céntimos en el borde."""
        self.validate_phase_accessible(Phase.PLANNING)
        owner = normalize_name(owner)
        bucket = DebtBucket(
            debt_bucket_name=name.strip(),
            principal_cents=to_cents(principal_euros),
            owner=owner,
            installment_cents=to_cents(installment_euros),
            start_date=start_date,
            description=description.strip(),
        )
        return self.household.add_debt_bucket(bucket)

    def set_debt_bucket_installment(self, bucket_id: UUID, amount_euros: float) -> None:
        """Fija la cuota mensual real de una deuda (la del usuario)."""
        self.validate_phase_accessible(Phase.PLANNING)
        self.household.set_debt_bucket_installment(bucket_id, to_cents(amount_euros))

    def register_debt_payment(
        self,
        member: str,
        bucket_id: UUID,
        amount_euros: float,
        payment_date=None,
    ) -> None:
        """Registra un pago contra un bucket de deuda en el período activo (MONTH)."""
        self.validate_phase(Phase.MONTH)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        if payment_date is None:
            payment_date = datetime.now()
        self._validate_movement_date(payment_date)

        self.household.register_debt_payment(
            member_name=member,
            amount_cents=amount_cents,
            bucket_id=bucket_id,
            payment_date=payment_date,
        )
        # Persistencia de pagos de deuda: T7 (diferida).

    def get_debt_status(self, member: str) -> dict:
        """Resumen de deuda de un miembro en el período: buckets + totales (PLANNING+)."""
        self.validate_phase_accessible(Phase.PLANNING)
        member = normalize_name(member)
        start_date, end_date = self._current_period_range()
        return self.household.get_debt_status_by_member(member, start_date, end_date)

    def get_all_debts_summary(self) -> dict:
        """Resumen de deuda de todos los miembros del hogar (PLANNING+)."""
        self.validate_phase_accessible(Phase.PLANNING)
        start_date, end_date = self._current_period_range()
        return self.household.get_all_debts_summary(start_date, end_date)

    def get_debt_history(self, member: str) -> list:
        """Historial completo de pagos de deuda de un miembro (MONTH+)"""
        self.validate_phase_accessible(Phase.MONTH)
        member = normalize_name(member)
        return self.household.get_debt_history(member)

    def _validate_movement_date(self, movement_date) -> None:
        """Un movimiento no puede tener fecha anterior al inicio del período abierto.

        La fecha es lo que decide a qué período pertenece un movimiento. Una fecha
        anterior al inicio caería fuera de esta ventana y no hay forma de imputarla
        a un período ya cerrado, así que quedaría registrada pero invisible.

        Quien llama decide qué hacer con el aviso: volver a registrarlo con una fecha
        de este período, o descartarlo.
        """
        if movement_date is None or self.period is None:
            return

        day = (
            movement_date.date()
            if isinstance(movement_date, datetime)
            else movement_date
        )
        if day < self.period.start_date:
            raise ValueError(
                f"La fecha {day} es anterior al inicio del período activo "
                f"({self.period.start_date}) y pertenece a uno ya cerrado. "
                f"Regístralo con una fecha de este período o descártalo."
            )

    def _current_period_range(self) -> tuple[date, date]:
        """Rango semiabierto [inicio, fin) del período activo.

        El fin es exclusivo para que el día de corte pertenezca solo al mes que
        empieza, y no se cuente en los dos. Mientras el período sigue abierto no
        tiene techo: todo lo registrado en él cuenta.
        """
        start_date = self.period.start_date if self.period else date.today()
        end_date = self.period.end_date if self.period else date.max
        return start_date, end_date or date.max

    # ====== PLANNING PHASE - Contribution Queries ======

    def get_category_budget(self, category_name: str) -> int:
        """Consultar presupuesto asignado a una categoría específica"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_category_planned_amount(category=category_name)

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

    def get_total_contributions_by_member(self):
        "Contribución total por miembro según el método de reparto activo (disponible en PLANNING)."
        return self.household.get_total_contributions_by_member()

    def get_reserve_contribution_by_member(self, member_name: str) -> int:
        """Dinero no presupuestado de un miembro según su porcentaje"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_reserve_contribution_by_member(member_name)

    def validate_debt_doesnt_exceed_capacity(self):
        """Valida que la deuda comprometida no supere la parte de reserva de cada miembro.
        El ahorro no se valida — es elección, no obligación."""
        self.validate_phase(Phase.PLANNING)
        return self.household.validate_debt_doesnt_exceed_capacity()

    # ====== PLANNING PHASE - Finalization ======
    def finish_planning(self):
        """Validar el plan, congelar el acuerdo del período y avanzar a mes.

        Aquí es donde el ingreso deja de ser editable: hasta este punto el reparto se
        recalcula en vivo; a partir de él manda el acuerdo congelado.
        """
        self.validate_phase(Phase.PLANNING)

        if not self.household.members:
            raise ValueError("Registra al menos un miembro")
        if self.household.get_total_incomes() <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos")

        # Validar que hay al menos una categoría con presupuesto
        categories = self.household.get_active_categories()
        if not categories:
            raise ValueError("Debe haber al menos una categoría creada")

        total_budgeted = self.household.get_total_budgeted()
        if total_budgeted <= 0:
            raise ValueError("Debe asignar presupuesto a al menos una categoría")

        self.household.validate_debt_doesnt_exceed_capacity()

        # Congelar estado de planificación (cachea percentages y contributions acordadas)
        self.household.freeze_planning_state()
        # Cambiar fase y marcarla como accesible
        self.current_phase = Phase.MONTH
        self._completed_phases.add(Phase.MONTH)

        if self.period_repo and self.period_id:
            self.period_repo.update_status(self.period_id, Phase.MONTH)

            self.period_repo.save_agreed_contributions(
                period_id=self.period_id,
                contributions=self.household.get_agreed_contributions(),
            )
            self.period_repo.save_percentages(
                period_id=self.period_id,
                percentages=self.household.get_agreed_percentages(),
            )

        if self.budget_categories_repository and self.period_id:
            budget_categories = self.household.budget.get_budget_categories()
            for _, budget_category in budget_categories.items():
                self.budget_categories_repository.save(
                    budget_category=budget_category, household_period_id=self.period_id
                )

    # ====== MONTH PHASE - Expense Registration ======

    def register_expense(
        self,
        member: str,
        category: str,
        amount_euros: float,
        description: str = "",
        participants: list[str] | None = None,
    ):
        """Registrar un gasto en fase MONTH.

        participants: lista de miembros que comparten el gasto.
          - Si se pasa → se usan esos (normalizados).
          - Si es None → se deriva de la categoría:
              is_shared=True  → todos los miembros del hogar.
              is_shared=False → solo el pagador.
        """
        self.validate_phase(Phase.MONTH)
        member_normalized = normalize_name(member)
        category = category.strip()
        description = description.strip()
        amount_cents = to_cents(amount_euros)
        cat = self._resolve_category(category)

        if participants is not None:
            participants = [normalize_name(name) for name in participants]
        else:
            if cat.is_shared:
                participants = self.household.get_member_names()
            else:
                participants = [member_normalized]

        expense = Expense(
            member=member_normalized,
            category=cat,
            amount_cents=amount_cents,
            description=description,
            participants=participants,
        )
        self.household.register_expense(expense=expense)

        if self.expense_repo and self.period_id:
            self.expense_repo.save(
                expense=expense, period_id=self.period_id, member_ids=self.member_ids
            )

    def finish_month(self, end_date: date | None = None):
        """Cerrar el mes en curso, esté en la fase que esté.

        Cerrar un mes que no llegó a usarse es legítimo: el período existió y su
        ventana temporal acaba aquí. Por eso solo se exige que siga abierto, en vez
        de obligar a haber pasado por MONTH.
        """
        if self.period is None:
            raise ValueError("No hay ningún período abierto que cerrar")
        if self.period.status == Phase.CLOSING:
            raise ValueError("El período ya está cerrado")

        self.current_phase = Phase.CLOSING
        self._completed_phases.add(Phase.CLOSING)

        if end_date is None:
            end_date = date.today()
        self.period.end_date = end_date
        self.period.status = Phase.CLOSING

        if self.period_repo and self.period_id:
            self.period_repo.update_status(self.period_id, Phase.CLOSING)
            self.period_repo.update_end_date(self.period_id, end_date=end_date)

    # ====== PLANNING PHASE - SAVING ======

    def get_savings_total_shared(self) -> int:
        """Total ahorrado en fondo compartido por todos los miembros (MONTH+)"""
        self.validate_phase_accessible(Phase.MONTH)
        return self.household.get_savings_total_shared()

    def get_savings_shared_by_period(self, start_date: date, end_date: date) -> dict:
        """Movimientos compartidos por rango de fechas → {member: [SavingEntry]} (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_savings_shared_by_period(start_date, end_date)

    # ====== Saving Bucket ======
    def create_saving_bucket(
        self,
        bucket_name: str,
        owners: list,
        goal_euros: float | None = None,
        deadline: datetime | None = None,
        deadline_in_months: int | None = None,
        description: str = "",
    ) -> UUID:
        """Crea y registra un nuevo bucket de ahorro. La meta es opcional (colchón).
        Personal o compartido se deriva de owners. Retorna su UUID.

        deadline_in_months: alternativa a deadline para quien no piensa en
        fecha de calendario, sino en plazo ("dentro de 7 meses"). Si se dan
        los dos a la vez, deadline_in_months manda.
        """
        self.validate_phase_accessible(Phase.PLANNING)
        goal_cents = to_cents(goal_euros) if goal_euros is not None else None
        bucket_name = bucket_name.strip()
        description = description.strip()
        owners = [normalize_name(name) for name in owners]

        if deadline_in_months is not None:
            target = add_months(date.today(), deadline_in_months)
            deadline = datetime(target.year, target.month, target.day)

        bucket = SavingBucket(
            saving_bucket_name=bucket_name,
            owners=owners,
            goal_cents=goal_cents,
            deadline=deadline,
            description=description,
        )

        bucket_id = self.household.add_saving_bucket(bucket)

        if self.saving_bucket_repo and self.household_id:
            self.saving_bucket_repo.save(
                saving_bucket=bucket,
                household_id=self.household_id,
                member_ids=self.member_ids,
            )

        return bucket_id

    def deposit_to_saving_bucket(
        self, bucket_id: UUID, member: str, amount_euros: float, date=None
    ) -> None:
        """Registra un depósito en un bucket (MONTH)"""
        self.validate_phase(Phase.MONTH)
        self._validate_movement_date(date)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        self.household.deposit_to_saving_bucket(bucket_id, member, amount_cents, date)

        if (
            self.saving_bucket_entry_repo
            and self.period_id
            and member in self.member_ids
        ):
            self.saving_bucket_entry_repo.save(
                period_id=self.period_id,
                bucket_id=bucket_id,
                member_id=self.member_ids[member],
                amount_cents=amount_cents,
                entry_date=date or datetime.now(),
            )

    def withdraw_from_saving_bucket(
        self, bucket_id: UUID, member: str, amount_euros: float, date=None
    ) -> None:
        """Registra un retiro de un bucket (MONTH)"""
        self.validate_phase(Phase.MONTH)
        self._validate_movement_date(date)
        member = normalize_name(member)
        amount_cents = to_cents(amount_euros)
        self.household.withdraw_from_bucket(bucket_id, member, amount_cents, date)

        if (
            self.saving_bucket_entry_repo
            and self.period_id
            and member in self.member_ids
        ):
            self.saving_bucket_entry_repo.save(
                period_id=self.period_id,
                bucket_id=bucket_id,
                member_id=self.member_ids[member],
                amount_cents=-amount_cents,
                entry_date=date or datetime.now(),
            )

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

    def get_shared_buckets(self, member: str):
        """Obtiene los buckets compartidos en los que participa un miembro (PLANNING+)"""
        self.validate_phase_accessible(Phase.PLANNING)
        member = normalize_name(member)
        return self.household.get_shared_buckets(member)

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
        return SummaryService.get_member_status(
            household=self.household, member_name=member_name
        )

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
        return SettlementCalculator.calculate(household=self.household)

    # ====== MONTH - NEW-MONTH ======
    def start_new_month(self, start_date: date | None = None):
        """Abrir un período: único punto por el que nace uno.

        Es también el arranque del programa: el primero no tiene período previo.
        La fecha de inicio la decide quien llama; por defecto, hoy.

        Dejar hueco entre un período y el siguiente es un uso normal — el usuario
        pasó un tiempo sin usar la aplicación. Lo que no se admite es empezar antes
        de que el anterior acabase: ahí los rangos se solaparían y un movimiento
        contaría en los dos.
        """
        if start_date is None:
            start_date = date.today()

        if self.period is not None:
            if self.period.status != Phase.CLOSING:
                raise ValueError(
                    "Cierra el mes en curso con finish_month() antes de abrir uno nuevo"
                )
            if self.period.end_date and start_date < self.period.end_date:
                raise ValueError(
                    f"El período no puede empezar el {start_date}: el anterior acaba "
                    f"el {self.period.end_date} y los rangos se solaparían."
                )

        self.household.reset_for_new_month()
        self._completed_phases = {Phase.PLANNING}
        self.current_phase = Phase.PLANNING

        self._start_period(start_date=start_date)

    def _start_period(self, start_date: date | None = None):
        """Instancia un nuevo período"""
        if start_date is None:
            start_date = date.today()

        # El hogar debe existir antes: household_periods.household_id es NOT NULL
        self._ensure_household()

        # Buckets personales y categorías base para poder planificar
        self.household.prepare_period()

        period = Period(
            household_id=self.household_id,
            start_date=start_date,
            status=Phase.PLANNING,
        )

        self.period = period

        if self.period_repo:
            self.period_id = self.period_repo.save(period)

    def _ensure_household(self) -> None:
        """Crea la fila del hogar si aún no existe. Idempotente."""
        if self.household_id or not self.household_repo:
            return
        self.household_id = self.household_repo.save()

    def _persist_new_members(self) -> None:
        """Persiste los miembros que aún no tienen id de BD. Idempotente."""
        if not self.member_repo or not self.household_id:
            return
        for name, member in self.household.members.items():
            if name in self.member_ids:
                continue
            self.member_ids[name] = self.member_repo.save(
                member=member, household_id=self.household_id
            )

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
        """Obtiene lista de categorías activas, en plano y sin jerarquía"""
        return self.household.get_active_categories()

    def get_root_categories(self) -> list[str]:
        """Obtiene las categorías raíz, las que cuentan contra el ingreso"""
        return self.household.get_root_categories()

    def get_category_children(self, category_name: str) -> list[str]:
        """Obtiene las categorías que cuelgan de una raíz"""
        return self.household.get_children(category_name)

    def get_category_billable(self, category_name: str) -> int:
        """Obtiene lo que una categoría reparte entre los miembros: su
        presupuesto menos lo que ya ha delegado en sus hijas"""
        return self.household.get_category_billable(category_name)

    # ====== QUERIES - Phase Summaries ======
    def get_registration_summary(self):
        """Obtiene resumen de miembros e ingresos (disponible desde PLANNING)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return SummaryService.get_registration_summary(household=self.household)

    def get_planning_summary(self) -> dict:
        """Obtiene resumen completo de planificación (disponible desde PLANNING)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return SummaryService.get_planning_summary(household=self.household)

    def get_month_summary(self):
        """Obtiene resumen completo de month (disponible desde MONTH)"""
        self.validate_phase_accessible(Phase.MONTH)
        return SummaryService.get_month_summary(household=self.household)

    # ====== QUERIES - Frozen Data ======
    def get_incomes(self) -> dict[str, int]:
        """Ingreso vivo de cada miembro (disponible desde PLANNING)"""
        self.validate_phase_accessible(Phase.PLANNING)
        return self.household.get_incomes()

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
