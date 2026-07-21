from src.models.member import Member
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.budget_categories_repository import BudgetCategoryRepository
from src.workflow.household_loader import HouseholdLoader
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
        self.budget_categories_repo = budget_categories_repo

    def set_distribution_method(self, method: MetodoReparto, period_id: int):

        period = self._load_period(period_id)
        household_id = period.household_id

        household, _, phase = self.household_loader.load_base(
            household_id=household_id, period_id=period_id
        )

        # Validar que estamos en fase para settear el método
        self.validate_phase(required_phase=Phase.PLANNING, current_phase=phase)

        household.assign_distribution_method(method=method)

        self.period_repo.update_method(method=method, period_id=period_id)

    def set_custom_splits(self, splits: dict[str, float], period_id: int):

        period = self._load_period(period_id)

        household_id = period.household_id

        household, _, phase = self.household_loader.load_base(
            household_id=household_id, period_id=period_id
        )
        self.validate_phase(current_phase=phase, required_phase=Phase.PLANNING)

        household.set_custom_splits(splits=splits)

        self.period_repo.save_custom_splits(
            period_id=period_id, splits=household.get_custom_splits()
        )

    def add_category(self, period_id: int, name: str, parent: str | None = None):
        """ """
        period = self._load_period(period_id)
        household_id = period.household_id

        household, _, phase = self.household_loader.load_base(
            household_id=household_id, period_id=period_id
        )

        self.validate_phase(current_phase=phase, required_phase=Phase.PLANNING)

        name = normalize_name(name)
        parent = normalize_name(parent) if parent else None

        # Pasar validaciones dominio
        household.add_category(name=name, parent=parent)
        # recuperar objeto
        budget_category = household.budget.get_budget_category(name)
        # persistir
        self.budget_categories_repo.save(
            household_period_id=period_id, budget_category=budget_category
        )

    def set_standard_categories(self, period_id: int):
        period = self._load_period(period_id)
        household_id = period.household_id

        # if household_id para que household siempre int
        household, _, phase = self.household_loader.load_base(
            household_id=household_id, period_id=period_id
        )

        self.validate_phase(current_phase=phase, required_phase=Phase.PLANNING)

        household.set_standard_categories()

        for _, budget_category in household.get_budget_categories().items():
            self.budget_categories_repo.save(
                household_period_id=period_id, budget_category=budget_category
            )

    def remove_category(self, period_id: int, name: str):
        period = self._load_period(period_id)
        household_id = period.household_id

        household, _, phase = self.household_loader.load_base(
            household_id=household_id, period_id=period_id
        )
        self.validate_phase(current_phase=phase, required_phase=Phase.PLANNING)

        name = normalize_name(name)
        # Pasar validaciones dominio (existe, sin gastos huérfanos, etc.)
        household.remove_category(name=name)

        self.budget_categories_repo.delete(household_period_id=period_id, name=name)

    def set_planned_amount(self, period_id: int, category: str, amount_euros: float):
        period = self._load_period(period_id)
        household_id = period.household_id

        household, _, phase = self.household_loader.load_base(
            household_id=household_id, period_id=period_id
        )
        self.validate_phase(current_phase=phase, required_phase=Phase.PLANNING)

        amount_cents = to_cents(amount_euros)
        # Dominio valida (techo, reserva, etc.) y puede recalcular más de una categoría
        # (p. ej. asignar la raíz recalcula la reserva) — por eso persistimos todas.
        BudgetDistributionService.set_budget_for_category(
            household, category=category, amount_cents=amount_cents
        )

        for name, budget_category in household.get_budget_categories().items():
            self.budget_categories_repo.update_planned_amount(
                household_period_id=period_id,
                name=name,
                planned_amount=budget_category.planned_amount,
            )

    def set_budget_by_percentages(
        self, period_id: int, percentages_floats: dict[str, float]
    ):
        period = self._load_period(period_id)
        household_id = period.household_id

        household, _, phase = self.household_loader.load_base(
            household_id=household_id, period_id=period_id
        )
        self.validate_phase(current_phase=phase, required_phase=Phase.PLANNING)

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
            self.budget_categories_repo.update_planned_amount(
                household_period_id=period_id,
                name=name,
                planned_amount=budget_category.planned_amount,
            )

    def finish_month(self, period_id: int):
        """No necesita rehidratar el household: solo mira/actualiza el período."""
        period = self._load_period(period_id)
        self.validate_phase(current_phase=period.status, required_phase=Phase.MONTH)

        self.period_repo.update_status(period_id=period_id, status=Phase.CLOSING)
        self.period_repo.update_end_date(period_id=period_id, end_date=date.today())

    def start_new_month(self, period_id:int):
        period = self._load_period(period_id)
        household_id = period.household_id

        household, _, phase = self.household_loader.load_base(
            household_id=household_id, period_id=period_id
        )

    # ============================================================
    #   PENDIENTES DE REFACTORIZACIÓN DE DEUDA
    # ============================================================

    def set_member_debt(self): ...
    def set_member_saving_goal(self): ...
    def auto_assign_saving_goals(self): ...
    def finish_planning(self): ...

    # ============================================================
    # QUERIES
    # ============================================================

    def validate_phase(
        self, required_phase: Phase, current_phase: Phase
    ):  # FIXME se repite: Meter en utils o phase_service?
        """Valida que la fase actual sea exactamente la requerida"""
        if current_phase != required_phase:
            raise ValueError(
                f"Operación solo permitida en fase {required_phase.value}. "
                f"Fase actual: {current_phase.value}"
            )

    def _load_period(self, period_id: int) -> Period:
        period = self.period_repo.find_by_id(period_id=period_id)
        if period is None:
            raise ValueError(f"Período {period_id} no encontrado")
        return period
