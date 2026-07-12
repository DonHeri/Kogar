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

    def finish_registration(
        self, household_id: int, start_date: date | None = None
    ) -> int:
        """

        Args:
            household_id: Identificador del núcleo a avanzar de fase
            start_date: Fecha que indica comienzo del periodo actual


        Returns:
            period_id = Identificador de BD del periodo actual
        """
        household, _ = self.household_loader.load_members_only(
            household_id=household_id
        )

        household.validate_has_members()
        household.validate_total_incomes_positive()

        if start_date is None:
            start_date = date.today()

        household.freeze_registration_state()

        period = Period(
            household_id=household_id,
            start_date=start_date,
            status=Phase.PLANNING,
        )

        period_id = self.period_repo.save(period=period)

        return period_id
