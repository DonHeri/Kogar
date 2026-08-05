from src.models.household import Household
from src.models.constants import Phase
from src.utils.text import normalize_name
from src.utils.currency import to_cents, to_percentage_basis
from src.storage.expense_repository import ExpenseRepository
from src.workflow.household_loader import HouseholdLoader
from src.models.category import Category
from src.models.expense import Expense


class ExpenseService:
    """Orquestación stateless del servicio de Expense"""

    def __init__(
        self, expense_repo: ExpenseRepository, household_loader: HouseholdLoader
    ) -> None:
        self.household_loader = household_loader
        self.expense_repository = expense_repo

    def register_expense(
        self,
        household_id: int,
        period_id: int,
        member: str,
        category: str,
        amount_euros: float,
        description: str = "",
        participants: list[str] | None = None,
    ):
        """Registrar un gasto cargando todos los datos desde bd"""
        # Primero debo cargar los datos
        household, members_id, period = self.household_loader.load_base(
            period_id=period_id
        )

        # Validar fase
        period.status.require(Phase.MONTH)

        # Normalizar datos
        member_normalized = normalize_name(member)
        category = category.strip()
        description = description.strip()
        amount_cents = to_cents(amount_euros)
        cat = self._resolve_category(name=category, household=household)

        # Comprobaciones nueva transacción
        if participants is not None:
            participants = [normalize_name(name) for name in participants]
        else:
            if cat.is_shared:
                participants = household.get_member_names()
            else:
                participants = [member_normalized]

        expense = Expense(
            member=member_normalized,
            category=cat,
            amount_cents=amount_cents,
            description=description,
            participants=participants,
        )

        # Registrar movimiento
        household.register_expense(expense=expense)

        # Guardar en db
        self.expense_repository.save(
            expense=expense, member_ids=members_id, period_id=period_id
        )


    def _resolve_category(self, household: Household, name: str) -> Category:
        """Traduce el nombre (string del exterior) al objeto Category vivo del presupuesto."""
        return household.budget.get_category(name)
