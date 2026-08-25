from src.models.constants import Phase
from src.storage.period_repository import PeriodRepository
from src.workflow.household_loader import HouseholdLoader, Load
from src.workflow.summary_service import SummaryService


class QueryService:
    def __init__(
        self,
        period_repository: PeriodRepository,
        household_loader: HouseholdLoader,
    ):

        self.period_repository = period_repository
        self.household_loader = household_loader

    # Resumen de planificación
    def planning_summary(self, period_id: int):
        """Obtiene el resumen de planificación para un período específico."""

        # Cargar household completo (members, debts, savings) y el período
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.BUDGET | Load.DEBTS | Load.SAVINGS
        )
        # Validar que estamos en fase para settear el método
        period.status.require_at_least(Phase.PLANNING)
        planning_summary = SummaryService.get_planning_summary(household)
        return planning_summary

    # Resumen del mes
    def month_summary(self, period_id: int):
        """Obtiene el resumen mensual para un período específico."""

        # Cargar household completo (members, debts, savings) y el período
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.FULL
        )
        # Validar que estamos en fase para settear el método
        period.status.require_at_least(Phase.MONTH)
        month_summary = SummaryService.get_month_summary(household)
        return month_summary

    # Estado de un miembro
    def member_status(self, period_id: int, member_name: str):
        """Obtiene el estado de un miembro específico para un período específico."""

        # Cargar household completo (members, debts, savings) y el período
        household, _, period = self.household_loader.load_household(
            period_id=period_id, load=Load.FULL
        )
        # Validar que estamos en fase para settear el método
        period.status.require_at_least(Phase.MONTH)
        status = SummaryService.get_member_status(household, member_name)
        return status

    # Settlement
    def settlement_summary(self, period_id: int) -> list[dict]:
        """Obtiene el resumen de liquidación para un período específico."""

        # Cargar household completo (members, debts, savings) y el período
        household, _, period = self.household_loader.load_household(
            period_id, load=Load.FOR_QUERIES
        )
        # Validar que estamos en fase para settear el método
        period.status.require_at_least(Phase.MONTH)
        settlement_transfers: list[dict] = SummaryService.get_settlement_summary(
            household=household
        )
        return settlement_transfers

    # Deuda del hogar
    def household_debt_summary(self, period_id: int) -> dict:
        """Obtiene el resumen de deuda del hogar para un período específico."""

        # Cargar household completo (members, debts, savings) y el período
        household, period = self.household_loader.load_household(period_id)
        # Validar que estamos en fase para settear el método
        period.status.require_at_least(Phase.MONTH)
        debt_summary: dict = SummaryService.get_all_debts_summary(
            household=household, period=period
        )
        return debt_summary

    def member_debt_status(self, period_id: int, member_name: str) -> dict:
        """Obtiene el estado de deuda de un miembro específico para un período específico."""

        # Cargar household completo (members, debts, savings) y el período
        household, period = self.household_loader.load_household(period_id)
        # Validar que estamos en fase para settear el método
        period.status.require_at_least(Phase.MONTH)
        debt_status: dict = SummaryService.get_debt_status(
            household=household, member_name=member_name, period=period
        )
        return debt_status

    # Ahorro del hogar
    def household_saving_summary(self, period_id: int) -> dict:
        """Obtiene el resumen de ahorro del hogar para un período específico."""

        # Cargar household completo (members, debts, savings) y el período
        household, period = self.household_loader.load_household(period_id)
        # Validar que estamos en fase para settear el método
        period.status.require_at_least(Phase.MONTH)
        saving_summary: dict = SummaryService.get_all_savings_summary(
            household=household, period=period
        )
        return saving_summary

    def member_saving_status(self, period_id: int, member_name: str) -> dict:
        """Obtiene el estado de ahorro de un miembro específico para un período específico."""

        # Cargar household completo (members, debts, savings) y el período
        household, period = self.household_loader.load_household(period_id)
        # Validar que estamos en fase para settear el método
        period.status.require_at_least(Phase.MONTH)
        saving_status: dict = SummaryService.get_saving_status(
            household=household, member_name=member_name, period=period
        )
        return saving_status

    # ============================================================
    # QUERIES
    # ============================================================
    #
    # def household_loader.load_household(self, period_id: int):
    #    """Carga el hogar y el período correspondiente a period_id. Devuelve (household, period)"""


#
#    # Rehidratar
#    household, _, period = self.household_loader.load_full(period_id=period_id)
#
#    return (household, period)
