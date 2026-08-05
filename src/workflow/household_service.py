from src.models.member import Member
from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.workflow.household_loader import HouseholdLoader
from src.utils.text import normalize_name
from src.utils.currency import to_cents
from src.models.period import Period
from src.models.constants import Phase
from datetime import date, datetime


class HouseholdService:
    """Orquestación stateless del servicio de Household"""

    def __init__(
        self,
        household_repo: HouseholdRepository,
        member_repo: MemberRepository,
        period_repo: PeriodRepository,
        household_loader: HouseholdLoader,
    ) -> None:
        self.household_repo = household_repo
        self.member_repo = member_repo
        self.period_repo = period_repo
        self.household_loader = household_loader

    def create_household(self):
        """
        Crea un núcleo familiar y devuelve su id

        Returns:
            household_id
        """
        household_id = self.household_repo.save()

        return household_id

    def register_member(self, household_id: int, name: str):
        """Registra un nuevo miembro en el hogar y lo persiste de inmediato en BD.

        Args:
            household_id: Identificador del núcleo familiar
            name: Nombre del miembro (se normaliza internamente)

        Returns:
            member_id: Identificador de BD del miembro creado

        Raises:
            ValueError: si el nombre ya está registrado en el hogar
        """
        self._validate_members_editable(household_id=household_id)

        household, _ = self.household_loader.load_members_only(
            household_id=household_id
        )
        member_normalized = normalize_name(name)

        member = Member(member_normalized)

        household.register_member(member=member)

        member_id = self.member_repo.save(household_id=household_id, member=member)

        return member_id

    def set_member_income(self, household_id: int, name: str, amount_euros: float):
        """Establece el ingreso mensual de un miembro ya registrado y lo persiste en BD.

        Args:
            household_id: Identificador del núcleo familiar
            name: Nombre del miembro (se normaliza internamente)
            amount_euros: Ingreso mensual en euros

        Raises:
            ValueError: si el miembro no existe en el hogar
        """
        self._validate_members_editable(household_id=household_id)

        household, member_ids = self.household_loader.load_members_only(
            household_id=household_id
        )
        member_normalized = normalize_name(name)
        amount_cents = to_cents(amount_euros)

        household.set_member_income(amount_cents=amount_cents, name=member_normalized)

        member_id: int = member_ids[member_normalized]
        self.member_repo.change_incomes(
            new_incomes_cents=amount_cents, member_id=member_id
        )

    # ====== VALIDATORS ======
    def _validate_members_editable(self, household_id: int) -> None:
        """Miembros e ingresos solo se tocan mientras el plan sigue abierto.

        finish_planning congela las contribuciones acordadas contra los ingresos
        de ese momento. Cambiarlos después deja el acuerdo persistido apuntando a
        números que ya no existen, y el settlement sale con datos viejos.

        Sin período abierto no hay acuerdo que romper, así que se permite: es el
        caso de dar de alta el hogar antes del primer start_new_month.

        Raises:
            ValueError: si el período en curso ya pasó de PLANNING
        """
        period = self.period_repo.get_current(household_id=household_id)

        if period and period.status != Phase.PLANNING:
            raise ValueError(
                f"Miembros e ingresos solo se modifican en fase {Phase.PLANNING.value}. "
                f"Fase actual: {period.status.value}"
            )

