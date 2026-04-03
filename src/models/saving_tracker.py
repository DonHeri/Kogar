from src.models.saving_account import SavingAccount
from src.models.constants import SavingScope
from datetime import datetime


class SavingTracker:
    """
    Gestiona las cuentas de ahorro individuales de todos los miembros del hogar.

    Responsabilidades:
    - Crear y almacenar una SavingAccount por miembro
    - Exponer queries agregadas sobre el ahorro compartido del hogar
    - Filtrar movimientos por miembro, destino y mes

    No gestiona ahorro personal — ese dato pertenece a cada SavingAccount.
    """

    def __init__(self) -> None:
        self._accounts: dict[str, SavingAccount] = {}

    # ====== GESTIÓN DE CUENTAS ======

    def create_account(self, member_name: str) -> None:
        """
        Crea una cuenta de ahorro para un miembro.
        Si ya existe, no hace nada.

        Args:
            member_name: Nombre normalizado del miembro
        """
        if member_name not in self._accounts:
            self._accounts[member_name] = SavingAccount(member_name)

    def deposit(
        self,
        member_name: str,
        amount_cents: int,
        destination: SavingScope,
        description="",
        date=None,
    ):
        self._accounts[member_name].deposit(
            amount_cents=amount_cents,
            destination=destination,
            description=description,
            date=date,
        )

    def withdraw(
        self,
        member_name: str,
        amount_cents: int,
        destination: SavingScope,
        description="",
        date=None,
    ):
        self._accounts[member_name].withdraw(
            amount_cents=amount_cents,
            destination=destination,
            description=description,
            date=date,
        )

    # ====== QUERIES ======

    def get_shared_balance(self, member_name: str) -> int:
        """
        Retorna el balance compartido de un miembro específico.

        Args:
            member_name: Nombre normalizado del miembro

        Returns:
            int: Total en céntimos aportado al fondo compartido
        """
        return self._accounts[member_name].balance_shared

    def get_history_shared(self, member_name: str) -> list:
        """
        Retorna el historial de movimientos compartidos de un miembro.

        Args:
            member_name: Nombre normalizado del miembro

        Returns:
            list[SavingEntry]: Entries con destination=SHARED del miembro
        """
        history = self._accounts[member_name].get_history()
        return [e for e in history if e.destination == SavingScope.SHARED]

    def get_member_summary(self, member_name: str) -> dict:
        """Retorna summary de ahorro del usuario"""
        self._validate_member_has_account(member_name)
        account = self._accounts[member_name]
        now = datetime.now()

        return {
            "balance_total": account.balance_total,
            "balance_personal": account.balance_personal,
            "balance_shared": account.balance_shared,
            "history": account.get_history(),
            "actual_month": account.get_monthly_summary(now.month, now.year),
        }

    def get_total_shared(self) -> int:
        """
        Retorna el total ahorrado en el fondo compartido por todos los miembros.

        Returns:
            int: Suma de balance_shared de todas las cuentas, en céntimos
        """
        return sum(account.balance_shared for account in self._accounts.values())

    def get_shared_by_month(self, month: int, year: int) -> dict[str, list]:
        """
        Retorna los movimientos compartidos de cada miembro en un mes concreto.

        Args:
            month: Mes (1-12)
            year: Año (ej. 2026)

        Returns:
            dict[str, list]: {member_name: [SavingEntry, ...]}
            Incluye todos los miembros, con lista vacía si no tienen movimientos ese mes.
        """
        result: dict[str, list] = {}

        for name, account in self._accounts.items():
            result[name] = [
                entry
                for entry in account.get_history()
                if entry.destination == SavingScope.SHARED
                and entry.date.month == month
                and entry.date.year == year
            ]

        return result

    def get_total_shared_history(self) -> dict[str, list]:
        """Historial completo de movimientos compartidos de todos los miembros"""
        return {
            name: [
                e for e in account.get_history() if e.destination == SavingScope.SHARED
            ]
            for name, account in self._accounts.items()
        }

    # ====== Validadores ======
    def _validate_member_has_account(self, member_name: str):
        """Valida que el miembro tiene cuenta"""
        if member_name not in self._accounts:
            raise ValueError("Miembro no tiene SavingAccount en tracker")
