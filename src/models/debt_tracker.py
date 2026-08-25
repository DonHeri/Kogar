from datetime import datetime

from src.models.debt_account import DebtAccount


class DebtTracker:
    """
    Gestiona las cuentas de deuda de todos los miembros del hogar.

    Responsabilidades:
    - Crear y almacenar una DebtAccount por miembro
    - Delegar pagos a la cuenta correspondiente
    - Exponer queries agregadas sobre pagos de deuda

    Patrón idéntico a SavingTracker, simplificado:
    sin buckets, sin destinos (PERSONAL/SHARED), sin retiros.
    """

    def __init__(self) -> None:
        self._accounts: dict[str, DebtAccount] = {}

    # ====== GESTIÓN DE CUENTAS ======

    def create_account(self, member_name: str) -> None:
        """
        Crea una cuenta de deuda para un miembro.
        Si ya existe, no hace nada.
        """
        if member_name not in self._accounts:
            self._accounts[member_name] = DebtAccount(member_name)

    def pay(
        self,
        member_name: str,
        amount_cents: int,
        description: str = "",
        date: datetime | None = None,
    ) -> None:
        """Registra un pago de deuda de un miembro"""
        self._validate_member_has_account(member_name)
        self._accounts[member_name].pay(
            amount_cents=amount_cents,
            description=description,
            date=date,
        )

    # ====== QUERIES ======

    def get_total_paid(self, member_name: str) -> int:
        """Total pagado de deuda por un miembro"""
        self._validate_member_has_account(member_name)
        return self._accounts[member_name].total_paid

    def get_member_summary(self, member_name: str) -> dict:
        """Resumen de deuda del miembro"""
        self._validate_member_has_account(member_name)
        account = self._accounts[member_name]
        now = datetime.now()

        return {
            "total_paid": account.total_paid,
            "history": account.get_history(),
            "actual_month": account.get_monthly_summary(now.month, now.year),
        }

    def get_history(self, member_name: str) -> list:
        """Historial completo de pagos de un miembro"""
        self._validate_member_has_account(member_name)
        return self._accounts[member_name].get_history()

    # ====== VALIDACIONES ======

    def _validate_member_has_account(self, member_name: str) -> None:
        if member_name not in self._accounts:
            raise ValueError("Miembro no tiene DebtAccount en tracker")
