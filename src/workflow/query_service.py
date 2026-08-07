from src.models.constants import Phase
from src.workflow.household_loader import HouseholdLoader, Load
from src.workflow.summary_service import SummaryService


class QueryService:
    """Consultas de lectura sobre un período, sin `WorkflowManager`.

    Cada consulta pide al loader **solo lo que va a leer**. El hogar entero hace
    falta en los resúmenes que cruzan presupuesto, gastos, deuda y ahorro; una
    consulta de deuda no necesita ni el presupuesto ni los gastos, y cargarlos
    serían tres tablas por petición para nada.

    No recibe `PeriodRepository`: el período lo lee el loader por dentro
    (`_require_period`) y lo devuelve junto al hogar, así que pedirlo aquí obligaba
    a construir una dependencia que nadie usaba.
    """

    def __init__(self, household_loader: HouseholdLoader):
        self.household_loader = household_loader

    # ============================================================
    # Resúmenes del período
    # ============================================================

    def planning_summary(self, period_id: int):
        """Obtiene el resumen de planificación para un período específico.

        Sin gastos: en PLANNING todavía no hay ninguno que resumir.
        """
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.BUDGET | Load.DEBTS | Load.SAVINGS
        )
        period.status.require_at_least(Phase.PLANNING)

        planning_summary = SummaryService.get_planning_summary(household)
        return planning_summary

    def month_summary(self, period_id: int):
        """Obtiene el resumen mensual para un período específico."""
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.FULL
        )
        period.status.require_at_least(Phase.MONTH)

        month_summary = SummaryService.get_month_summary(household)
        return month_summary

    def member_status(self, period_id: int, member_name: str):
        """Obtiene el estado de un miembro específico para un período específico."""
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.FULL
        )
        period.status.require_at_least(Phase.MONTH)

        status = SummaryService.get_member_status(household, member_name)
        return status

    # ============================================================
    # Settlement
    # ============================================================

    def settlement_summary(self, period_id: int) -> list[dict]:
        """Obtiene el resumen de liquidación para un período específico.

        Le basta con el presupuesto y los gastos: desde que los pesos viajan dentro
        de cada `Expense`, el reparto ya no consulta ingresos ni custom splits.
        """
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.FOR_QUERIES
        )
        period.status.require_at_least(Phase.MONTH)

        settlement_transfers: list[dict] = SummaryService.get_settlement_summary(
            household=household
        )
        return settlement_transfers

    # ============================================================
    # Deuda
    # ============================================================

    def household_debt_summary(self, period_id: int) -> dict:
        """Obtiene el resumen de deuda del hogar para un período específico."""
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.DEBTS
        )
        period.status.require_at_least(Phase.MONTH)

        debt_summary: dict = SummaryService.get_all_debts_summary(
            household=household, period=period
        )
        return debt_summary

    def member_debt_status(self, period_id: int, member_name: str) -> dict:
        """Obtiene el estado de deuda de un miembro específico para un período específico."""
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.DEBTS
        )
        period.status.require_at_least(Phase.MONTH)

        debt_status: dict = SummaryService.get_debt_status(
            household=household, member_name=member_name, period=period
        )
        return debt_status

    # ============================================================
    # Ahorro
    # ============================================================

    def household_saving_summary(self, period_id: int) -> dict:
        """Obtiene el resumen de ahorro del hogar para un período específico."""
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.SAVINGS
        )
        period.status.require_at_least(Phase.MONTH)

        saving_summary: dict = SummaryService.get_all_savings_summary(
            household=household, period=period
        )
        return saving_summary

    def member_saving_status(self, period_id: int, member_name: str) -> dict:
        """Obtiene el estado de ahorro de un miembro específico para un período específico."""
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.SAVINGS
        )
        period.status.require_at_least(Phase.MONTH)

        saving_status: dict = SummaryService.get_saving_status(
            household=household, member_name=member_name, period=period
        )
        return saving_status
