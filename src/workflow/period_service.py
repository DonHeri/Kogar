from src.models.member import Member
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.budget_categories_repository import BudgetCategoryRepository
from src.workflow.household_loader import HouseholdLoader, Load
from src.utils.text import normalize_name
from src.utils.currency import to_cents, to_percentage_basis
from src.workflow.budget_distribution_service import BudgetDistributionService
from src.models.period import Period
from src.models.constants import Phase, MetodoReparto
from datetime import date, datetime


class PeriodService:
    def __init__(
        self,
        household_loader: HouseholdLoader,
        period_repo: PeriodRepository,
        budget_categories_repo: BudgetCategoryRepository,
    ):
        self.household_loader = household_loader
        self.period_repo = period_repo
        self.budget_categories_repository = budget_categories_repo

    def start_new_month(
        self,
        household_id: int,
        start_date: date | None = None,
        carry_over: bool = True,
    ) -> int:
        """Abre un período nuevo, que nace ya en PLANNING.

        Registrar miembros e ingresos deja de ser una fase previa: se hace dentro
        del período abierto, planificando.

        Args:
            household_id: Identificador del núcleo para el que se abre el período
            start_date: Fecha de inicio. Por defecto, hoy — no se hereda del anterior:
                dejar hueco entre períodos es un uso normal.
            carry_over: Si hay período anterior, arrastra su configuración como
                borrador editable. Poner False para empezar de cero.

        Returns:
            period_id = Identificador de BD del periodo creado
        """

        if self.period_repo.get_current(household_id=household_id):
            raise ValueError(
                "Cierra el mes en curso con finish_month() antes de abrir uno nuevo"
            )

        if start_date is None:
            start_date = date.today()

        last_period = self.period_repo.get_last(household_id=household_id)

        if last_period:
            if last_period.end_date and start_date < last_period.end_date:
                raise ValueError(
                    f"El período no puede empezar el {start_date}: el anterior acaba "
                    f"el {last_period.end_date} y los rangos se solaparían."
                )

        period = Period(
            household_id=household_id,
            start_date=start_date,
            status=Phase.PLANNING,
            method=last_period.method if last_period else MetodoReparto.PROPORTIONAL,
        )

        period_id = self.period_repo.save(period=period)

        if carry_over and last_period and last_period.id:
            self._carry_over_config(
                source_period_id=last_period.id,
                target_period_id=period_id,
            )

        return period_id

    def _carry_over_config(
        self, source_period_id: int, target_period_id: int
    ) -> None:
        """Copia la configuración del período anterior como punto de partida.

        Se arrastra lo que describe *cómo se reparte y en qué se presupuesta*:
        categorías con su importe y los porcentajes personalizados. No se arrastra
        nada de lo ocurrido — gastos, pagos y movimientos son del período que cerró.

        Es un borrador: el usuario ajusta lo que cambie durante PLANNING. Arrastrar
        ahorra trabajo, no impone nada.
        """
        source, _, source_period = self.household_loader.load_household(source_period_id, load=Load.BUDGET)

        for _, budget_category in source.get_budget_categories().items():
            self.budget_categories_repository.save(
                household_period_id=target_period_id, budget_category=budget_category
            )

        # Solo se arrastra un reparto que el usuario decidió. Un período cerrado
        # con método PROPORTIONAL también tiene porcentajes guardados — son su
        # acuerdo, calculado desde los ingresos de aquel mes. Copiarlos aquí los
        # congelaría como si fueran una decisión, y el mes nuevo dejaría de
        # recalcularlos con los ingresos de ahora.
        if source_period.method == MetodoReparto.CUSTOM:
            splits = self.period_repo.get_percentages(period_id=source_period_id)
            if splits:
                self.period_repo.save_percentages(
                    period_id=target_period_id, percentages=splits
                )

    def set_distribution_method(self, method: MetodoReparto, period_id: int):

        household, _, period = self.household_loader.load_household(period_id, load=Load.BUDGET)

        # Validar que estamos en fase para settear el método
        period.status.require(Phase.PLANNING)

        household.set_distribution_method(method=method)

        self.period_repo.update_method(method=method, period_id=period_id)

    def set_custom_splits(self, splits: dict[str, float], period_id: int):
        """Recibe porcentajes 0-100 y los convierte: este es el borde."""
        household, _, period = self.household_loader.load_household(period_id, load=Load.BUDGET)
        period.status.require(Phase.PLANNING)

        splits_basis_points = {
            name: to_percentage_basis(pct) for name, pct in splits.items()
        }
        household.set_custom_splits(splits=splits_basis_points)

        self.period_repo.save_percentages(
            period_id=period_id, percentages=household.get_custom_splits()
        )
        # set_custom_splits deja el método en CUSTOM: el período tiene que
        # enterarse, o al recargar el reparto volvería a ser el anterior.
        self.period_repo.update_method(method=household.method, period_id=period_id)

    def add_category(
        self,
        period_id: int,
        name: str,
        parent: str | None = None,
        budget_euros: float | None = None,
        participants: list[str] | None = None,
    ):
        """Crea una categoría del período, con su importe si se indica.

        `budget_euros` opcional, y por una razón que solo se ve en esta capa: crear
        una categoría con importe eran dos llamadas, y cada una rehidrataba el hogar
        entero por su cuenta. Aquí se hace con una sola carga.

        Asignar el importe puede recalcular más de una categoría (la raíz recalcula
        la reserva), por eso se persisten todas y no solo la nueva.
        """
        household, _, period = self.household_loader.load_household(period_id, load=Load.BUDGET)

        period.status.require(Phase.PLANNING)

        name = normalize_name(name)
        parent = normalize_name(parent) if parent else None

        # Pasar validaciones dominio
        if participants is None and parent is None:
            participants = household.get_member_names()
        household.add_category(name=name, participants=participants, parent=parent)
        # recuperar objeto
        budget_category = household.budget.get_budget_category(name)
        # persistir
        self.budget_categories_repository.save(
            household_period_id=period_id, budget_category=budget_category
        )

        if budget_euros is None:
            return

        BudgetDistributionService.set_budget_for_category(
            household, category_name=name, amount_cents=to_cents(budget_euros)
        )

        for category_name, budget_category in household.get_budget_categories().items():
            self.budget_categories_repository.update_planned_amount(
                household_period_id=period_id,
                name=category_name,
                planned_amount=budget_category.planned_amount,
            )

    def set_standard_categories(self, period_id: int):
        household, _, period = self.household_loader.load_household(period_id, load=Load.BUDGET)

        period.status.require(Phase.PLANNING)

        household.set_standard_categories()

        for _, budget_category in household.get_budget_categories().items():
            self.budget_categories_repository.save(
                household_period_id=period_id, budget_category=budget_category
            )

    def remove_category(self, period_id: int, name: str):
        household, _, period = self.household_loader.load_household(period_id, load=Load.BUDGET)
        period.status.require(Phase.PLANNING)

        name = normalize_name(name)
        # Pasar validaciones dominio (existe, sin gastos huérfanos, etc.)
        household.remove_category(name=name)

        self.budget_categories_repository.delete(
            household_period_id=period_id, name=name
        )

    def set_planned_amount(self, period_id: int, category: str, amount_euros: float):
        household, _, period = self.household_loader.load_household(period_id, load=Load.BUDGET)
        period.status.require(Phase.PLANNING)

        amount_cents = to_cents(amount_euros)
        # Dominio valida (techo, reserva, etc.) y puede recalcular más de una categoría
        # (p. ej. asignar la raíz recalcula la reserva) — por eso persistimos todas.
        BudgetDistributionService.set_budget_for_category(
            household, category_name=category, amount_cents=amount_cents
        )

        for name, budget_category in household.get_budget_categories().items():
            self.budget_categories_repository.update_planned_amount(
                household_period_id=period_id,
                name=name,
                planned_amount=budget_category.planned_amount,
            )

    def set_budget_by_percentages(
        self, period_id: int, percentages_floats: dict[str, float]
    ):
        household, _, period = self.household_loader.load_household(period_id, load=Load.BUDGET)
        period.status.require(Phase.PLANNING)

        total_pct = sum(percentages_floats.values())
        if total_pct > 100:
            raise ValueError(f"Los porcentajes suman {total_pct}%, máximo 100%")

        percentages = {
            name: to_percentage_basis(pct) for name, pct in percentages_floats.items()
        }
        BudgetDistributionService.set_budget_by_percentages(
            household, percentages=percentages
        )

        for name, budget_category in household.get_budget_categories().items():
            self.budget_categories_repository.update_planned_amount(
                household_period_id=period_id,
                name=name,
                planned_amount=budget_category.planned_amount,
            )

    def finish_month(self, period_id: int, end_date: date | None = None):
        """No necesita rehidratar el household: solo mira/actualiza el período."""
        period = self._load_period(period_id)

        if period.status == Phase.CLOSING:
            raise ValueError("El período ya está cerrado")

        if end_date is None:
            end_date = date.today()

        self.period_repo.update_status(period_id=period_id, status=Phase.CLOSING)
        self.period_repo.update_end_date(period_id=period_id, end_date=end_date)

    # ============================================================
    #   PENDIENTES DE REFACTORIZACIÓN DE DEUDA
    # ============================================================

    def finish_planning(self, period_id: int):
        """Confirma el plan del período y lo pasa a MONTH.

        Aquí es donde el ingreso deja de ser editable: hasta este punto el reparto se
        recalcula en vivo; a partir de él manda el acuerdo guardado.

        Las categorías no se persisten aquí: ya se guardaron al crearlas y al
        presupuestarlas. Lo único que nace en este paso es el acuerdo.
        """
        household, _, period = self.household_loader.load_household(period_id, load=Load.BUDGET)

        period.status.require(Phase.PLANNING)
        household.validate_has_members()
        household.validate_total_incomes_positive()

        categories = household.get_active_categories()
        if not categories:
            raise ValueError("Debe haber al menos una categoría creada")

        total_budgeted = household.get_total_budgeted()
        if total_budgeted <= 0:
            raise ValueError("Debe asignar presupuesto a al menos una categoría")

        household.validate_debt_doesnt_exceed_capacity()

        # Congelar y persistir son el mismo acto en dos sitios: el objeto muere
        # al acabar la llamada, así que aquí la memoria del acuerdo es la BD.
        household.freeze_planning_state()

        self.period_repo.save_agreed_contributions(
            period_id=period_id,
            contributions=household.get_agreed_contributions(),
        )
        self.period_repo.save_percentages(
            period_id=period_id,
            percentages=household.get_agreed_percentages(),
        )

        self.period_repo.update_status(period_id, Phase.MONTH)

    # ============================================================
    # QUERIES
    # ============================================================



    def _load_period(self, period_id: int) -> Period:
        period = self.period_repo.find_by_id(period_id=period_id)
        if period is None:
            raise ValueError(f"Período {period_id} no encontrado")
        return period
