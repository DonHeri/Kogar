from datetime import datetime, date
from typing import Dict
from uuid import UUID

from src.models.budget import Budget
from src.models.category import AutoCalculatedCategory
from src.models.constants import MetodoReparto, SavingScope
from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.models.finance_calculator import FinanceCalculator
from src.models.member import Member
from src.models.income_entry import IncomeEntry
from src.models.saving_bucket import SavingBucket
from src.models.saving_tracker import SavingTracker
from src.models.debt_tracker import DebtTracker
from src.utils.currency import to_percentage_basis
from src.utils.text import normalize_name


class Household:
    def __init__(
        self,
        budget: Budget,
        expense_tracker: ExpenseTracker,
        saving_tracker: SavingTracker,
        debt_tracker: DebtTracker,
        method: MetodoReparto = MetodoReparto.PROPORTIONAL,
    ) -> None:

        self.members: Dict[str, Member] = {}
        self.budget = budget
        self.expense_tracker: ExpenseTracker = expense_tracker
        self.savings_tracker: SavingTracker = saving_tracker
        self.debt_tracker: DebtTracker = debt_tracker
        self.method: MetodoReparto = method
        self._custom_splits = {}
        self._registered_incomes = {}
        self._member_debts: dict[str, int] = {}
        self._saving_goals: dict[str, int] = {}
        self._agreed_percentages = {}
        self._agreed_contributions = {}
        self._income_entries: list[IncomeEntry] = []

    # ====== REGISTRATION ======

    def register_member(self, member: Member):
        """Registra un nuevo miembro en el hogar"""
        if member.name in self.members:
            raise ValueError(f"{member.name} ya está registrado en el hogar")

        self.members[member.name] = member
        self._saving_goals[member.name] = 0
        self._member_debts[member.name] = 0

    def set_member_income(self, name: str, amount_cents: int):
        """Establece el ingreso mensual de un miembro (en céntimos)"""
        name = normalize_name(name)
        if name not in self.members:
            raise ValueError(f"{name} no existe en el hogar")

        self.members[name].add_incomes(amount_cents)

    def freeze_registration_state(self):
        """Congela los ingresos registrados al pasar a fase PLANNING"""
        self._registered_incomes = {
            name: member.monthly_income for name, member in self.members.items()
        }
        for name in self.members:
            self.savings_tracker.create_account(name)
            self.debt_tracker.create_account(name)

        # Crear categorías estándar
        if not self.budget.categories:
            self.budget.set_standard_categories()

    # ====== PLANNING — CATEGORIES ======

    def add_category(self, name: str, parent: str | None = None):
        """Agrega categoría y la propaga a Budget"""
        self.budget.add_category(name, parent=parent)

    def remove_category(self, name: str):
        """Elimina categoría"""
        self.budget.delete_budget_category(name)

    def set_standard_categories(self):
        self.budget.set_standard_categories()

    # ====== PLANNING — BUDGET ======

    def set_member_debt(self, member_name: str, amount_cents: int) -> None:
        """Declara la deuda personal mensual de un miembro (PLANNING)"""
        self.validate_member_exist(member_name)
        self._member_debts[member_name] = amount_cents

    def set_member_saving_goal(self, member_name: str, amount_cents: int) -> None:
        """Declara el ahorro personal mensual de un miembro (PLANNING)"""
        self.validate_member_exist(member_name)
        self._saving_goals[member_name] = amount_cents

    # ====== PLANNING — DISTRIBUTION ======

    def assign_distribution_method(self, method: MetodoReparto):
        """Establece método de reparto"""
        self.method = method

    def set_custom_splits(self, splits: dict[str, float]):
        """Define porcentajes de reparto personalizados (0-100)"""
        self.validate_has_members()
        self._validate_all_members_have_split(splits)

        self._custom_splits = {
            name: to_percentage_basis(pct) for name, pct in splits.items()
        }

    def get_custom_splits(self):
        return self._custom_splits

    def validate_debt_and_saving_dont_exceed_capacity(self):
        """
        Valida que los compromisos personales (deuda + ahorro) no superen
        la parte de 'reserva' que le corresponde a cada miembro.
        """
        for member in self.members:
            reserve_capacity = self.get_reserve_contribution_by_member(member)
            debt = self._member_debts.get(member, 0)
            saving = self._saving_goals.get(member, 0)

            if (debt + saving) > reserve_capacity:
                raise ValueError(
                    f"Compromisos ({debt + saving}¢) de {member} superan su "
                    f"parte de reserva ({reserve_capacity}¢)"
                )

    def freeze_planning_state(self):
        """Congela el estado de planificación al pasar a fase MONTH"""
        self._agreed_percentages = self.get_percentages_by_method(self.method)
        self._agreed_contributions = self.get_current_contributions()

    def auto_assign_saving_goals(self):
        """Calcula automáticamente los objetivos de ahorro de cada miembro según su parte de la categoría auto-calculada (reserva) y su deuda personal"""

        for member in self.members:
            reserve_contribution = self.get_reserve_contribution_by_member(member)
            debt = self._member_debts.get(member, 0)

            self._saving_goals[member] = reserve_contribution - debt

    # ====== MONTH — EXPENSES ======

    def register_expense(self, expense: Expense):
        """Registra un gasto (almacena solo en ExpenseTracker)"""
        self.validate_member_exist(expense.member)
        self.validate_category_exist(expense.category.name)
        self.expense_tracker.add_expense(expense)

    # ====== MONTH — SAVINGS ======

    def register_savings_deposit(
        self,
        member_name: str,
        amount_cents: int,
        scope: SavingScope,
        description="",
        date=None,
    ):
        self.validate_member_exist(member_name)

        self.savings_tracker.deposit(
            member_name=member_name,
            amount_cents=amount_cents,
            scope=scope,
            description=description,
            date=date,
        )

    def register_savings_withdrawal(
        self,
        member_name: str,
        amount_cents: int,
        destination: SavingScope,
        description="",
        date=None,
    ):
        self.validate_member_exist(member_name)

        self.savings_tracker.withdraw(
            member_name=member_name,
            amount_cents=amount_cents,
            destination=destination,
            description=description,
            date=date,
        )

    # ====== MONTH — DEBT ======

    def register_debt_payment(
        self,
        member_name: str,
        amount_cents: int,
        payment_date: datetime | None = None,
        description="",
        allow_overpayment: bool = False,
    ):
        """Registra un pago de deuda validando que no supera el compromiso del mes.

        El DebtTracker se reinstancia cada mes en reset_for_new_month, así que
        get_total_paid ya devuelve solo lo pagado en el período activo — sin filtrar
        por fechas. El histórico entre meses vive en BD (DebtRepository).
        """
        self.validate_member_exist(member_name)
        committed = self._member_debts.get(member_name, 0)
        paid = self.debt_tracker.get_total_paid(member_name)

        if not allow_overpayment and ((paid + amount_cents) > committed):
            raise ValueError(f"El pago supera el compromiso de deuda ({committed}¢)")

        self.debt_tracker.pay(member_name, amount_cents, description, date=payment_date)

    # ====== MONTH — BUCKETS ======

    def add_saving_bucket(self, bucket: SavingBucket) -> UUID:
        bucket_id = self.savings_tracker.add_saving_bucket(bucket)
        return bucket_id

    def deposit_to_bucket(
        self, bucket_id: UUID, member_name: str, amount_cents: int, date=None
    ) -> None:
        self.validate_member_exist(member_name)
        self.savings_tracker.deposit_to_bucket(
            bucket_id, member_name, amount_cents, date
        )

    def withdraw_from_bucket(
        self, bucket_id: UUID, member_name: str, amount_cents: int, date=None
    ) -> None:
        self.validate_member_exist(member_name)
        self.savings_tracker.withdraw_from_bucket(
            bucket_id, member_name, amount_cents, date
        )

    # ====== MONTH — NEW MONTH ======

    def reset_for_new_month(self):
        """Reinicia el estado mutable del período. Miembros, categorías.
        También se reinicia el estado de ExpenseTracker, DebtTracker y SavingTracker para evitar acumulación de movimientos pasados."""
        self.expense_tracker = ExpenseTracker()
        self.debt_tracker = DebtTracker()
        self.savings_tracker = SavingTracker()
        self._registered_incomes = {}
        self._agreed_contributions = {}
        self._agreed_percentages = {}
        self._member_debts = {name: 0 for name in self.members}
        self._saving_goals = {name: 0 for name in self.members}
        self._income_entries = list()

    # ====== QUERIES — REGISTRATION ======

    def get_member_names(self):
        return self.members.keys()

    def get_registered_incomes(self) -> dict[str, int]:
        """Obtiene ingresos congelados (disponible en PLANNING/MONTH)"""
        if not self._registered_incomes:
            raise ValueError(
                "Los ingresos no han sido congelados. Llama a finish_registration() primero."
            )
        return self._registered_incomes.copy()

    # ====== QUERIES — PLANNING ======

    def get_active_categories(self) -> list[str]:
        """Lista categorías activas"""
        return self.budget.get_categories_list()

    def get_category_budget(self, category: str) -> int:
        """Obtiene presupuesto asignado a una categoría"""
        return self.budget.get_category_budget(category)

    def get_total_incomes(self):
        """Calcula el ingreso total mensual (usa datos congelados si están disponibles)"""
        self.validate_has_members()
        self.validate_total_incomes_positive()

        extra_incomes = [e.amount_cents for e in self._income_entries]

        # Usar datos congelados si están disponibles (PLANNING/MONTH)
        if self._registered_incomes:
            incomes = list(self._registered_incomes.values()) + extra_incomes
        else:
            # Usar datos mutables solo en REGISTRATION
            incomes = [m.monthly_income for m in self.members.values()] + extra_incomes

        total = FinanceCalculator.sum_values(incomes)
        return total

    def get_total_budgeted(self):
        """Obtiene total presupuestado (cents)"""
        return self.budget.get_total_budgeted()

    def get_reserve_contribution_by_member(self, name: str) -> int:
        """Obtiene cuánto le corresponde a un miembro de la categoría auto-calculada (reserva) según el método activo"""
        name = normalize_name(name)
        self.validate_member_exist(name)
        auto_cat = self.budget.get_auto_calculated_category()
        contributions = (
            self.get_current_contributions()
            .get(auto_cat.name, {})
            .get("contributions", {})
        )
        return contributions.get(name, 0)

    def get_budget_as_percentage(self, category: str):
        """
        Retorna qué % del ingreso total representa el presupuesto de la categoría.

        Ejemplo: Ingresos 3000€, Fijos 1500€ → retorna 5000 (50%)

        Returns:
            int: Porcentaje en basis points (5000 = 50% de ingresos)
        """
        category_budget = self.get_category_budget(category)
        total = self.get_total_incomes()
        pct_basis = (category_budget * 10000) // total
        return pct_basis

    def get_percentages_by_method(self, method: MetodoReparto):
        """Calcula el porcentaje de reparto (usa datos congelados si están disponibles)"""
        self.validate_has_members()
        self.validate_total_incomes_positive()

        # Usar datos congelados si están disponibles (PLANNING/MONTH)
        if self._registered_incomes:
            income_map = self._registered_incomes
        else:
            # Usar datos mutables solo en REGISTRATION
            income_map = {name: m.monthly_income for name, m in self.members.items()}

        percentages = {}

        match method:
            case MetodoReparto.PROPORTIONAL:
                percentages = (
                    FinanceCalculator.calculate_percentage_based_on_weight_of_income(
                        income_map
                    )
                )
            case MetodoReparto.EQUAL:
                percentages = FinanceCalculator.calculate_equal_percentage(income_map)

            case MetodoReparto.CUSTOM:
                if not hasattr(self, "_custom_splits"):
                    raise ValueError(
                        "Método CUSTOM requiere llamar a set_custom_splits() primero"
                    )
                return self._custom_splits

        return percentages

    def preview_budget_contribution_summary(self, method: MetodoReparto):
        """
        Calcula contribuciones por categoría con método de reparto inyectado.

        Returns:
            dict: Por cada categoría:
                - planned: presupuesto planificado (céntimos)
                - contributions: {nombre_miembro: contribución (céntimos)}
                - total_assigned: suma de contributions
        """
        income_map = self._registered_incomes or {
            name: m.monthly_income for name, m in self.members.items()
        }

        summary = {}

        for cat_name, category in self.budget.categories.items():
            if method == MetodoReparto.CUSTOM:
                contributions = (
                    FinanceCalculator.calculate_contribution_from_custom_splits(
                        self._custom_splits, category.planned_amount
                    )
                )

            elif method == MetodoReparto.EQUAL:
                equal_income_map = {name: 1 for name in income_map}
                contributions = FinanceCalculator.calculate_contribution_from_incomes(
                    equal_income_map, category.planned_amount
                )

            else:
                contributions = FinanceCalculator.calculate_contribution_from_incomes(
                    income_map, category.planned_amount
                )

            summary[cat_name] = {
                "planned": category.planned_amount,
                "contributions": contributions,
                "total_assigned": sum(contributions.values()),
            }

        return summary

    def get_current_contributions(self):
        """Obtiene contribuciones usando el método ya configurado (self.method)"""
        return self.preview_budget_contribution_summary(self.method)

    def get_total_contributions_by_member(self) -> dict[str, int]:
        "Suma las contribuciones de cada miembro en todas las categorías. Devuelve {nombre: total_cents}."
        contributions = self.get_current_contributions()

        totals = {member: 0 for member in self.members}

        for cat in contributions:
            for member, amount in contributions[cat]["contributions"].items():
                totals[member] += amount

        return totals

    def get_agreed_percentages(self) -> dict[str, int]:
        """Obtiene porcentajes acordados congelados (disponible en MONTH)"""
        if not self._agreed_percentages:
            raise ValueError(
                "Los porcentajes no han sido congelados. Llama a finish_planning() primero."
            )
        return self._agreed_percentages.copy()

    def get_agreed_contributions(self):
        """Obtiene contribuciones acordadas congeladas (disponible en MONTH)"""
        if not self._agreed_contributions:
            raise ValueError(
                "Las contribuciones no han sido congeladas. Llama a finish_planning() primero."
            )
        return self._agreed_contributions.copy()

    def get_member_debts(self):
        return self._member_debts

    def get_saving_goals(self):
        return self._saving_goals

    # ====== QUERIES — MONTH ======
    def get_extra_income_entries(self):
        """Obtiene ingresos extra registrados en MONTH"""
        return self._income_entries.copy()

    def recalculate_reserve(self):
        """Recalcula la categoría auto-calculada (reserva) según ingresos y presupuestos actuales"""
        reserve_cat = self.budget.get_auto_calculated_category()
        total_incomes = self.get_total_incomes()
        current_reserve = self.get_category_budget(reserve_cat.name)
        other_budgeted = self.get_total_budgeted() - current_reserve

        new_reserve_amount = reserve_cat.calculate_own_budget(
            total_incomes, other_budgeted
        )
        self.budget.set_budget(reserve_cat.name, new_reserve_amount)

    def get_member_owed_total(self, member_name: str) -> int:
        """Cuánto acordó pagar el miembro"""
        member_name = normalize_name(member_name)
        self.validate_member_exist(member_name)
        contributions = self.get_agreed_contributions()
        total = sum(
            cat_data["contributions"][member_name]
            for cat_data in contributions.values()
        )
        return total

    def get_member_paid_total(self, member_name: str) -> int:
        """Total gastado por un miembro"""
        member_name = normalize_name(member_name)
        return self.expense_tracker.get_total_spent_by_member(member_name)

    def get_member_balance(self, member_name: str) -> int:
        """Balance: pagado - acordado (negativo = debe, positivo = pagó de más)"""
        member_name = normalize_name(member_name)
        self.validate_member_exist(member_name)
        owed = self.get_member_owed_total(member_name)
        paid = self.get_member_paid_total(member_name)

        return paid - owed

    def get_category_spent(self, category: str) -> int:
        """Obtiene total gastado en una categoría (consulta ExpenseTracker)"""
        return self.expense_tracker.get_total_spent_by_category(category)

    def get_total_spent(self) -> int:
        """Obtiene total gastado (consulta ExpenseTracker)"""
        return self.expense_tracker.get_total_spent()

    def get_category_remaining(self, category: str) -> int:
        """Calcula presupuesto restante de una categoría: planificado - gastado"""
        budgeted = self.budget.get_category_budget(category)
        spent = self.get_category_spent(category)
        return budgeted - spent

    def get_total_remaining(self) -> int:
        """Calcula total restante: presupuesto total - total gastado"""
        budgeted = self.get_total_budgeted()
        spent = self.get_total_spent()
        return budgeted - spent

    def get_debt_status(self, member_name):
        self.validate_member_exist(member_name)
        committed = self._member_debts.get(member_name, 0)
        paid = self.debt_tracker.get_total_paid(member_name)
        return {"committed": committed, "paid": paid, "remaining": committed - paid}

    def get_debt_history(self, member_name: str) -> list:
        self.validate_member_exist(member_name)
        return self.debt_tracker.get_history(member_name)

    def get_member_savings_summary(self, member_name: str):
        """Retorna dict resumen:
        {
        "balance_total" : int -> total ahorrado por el miembro,
        "balance_personal": int -> total ahorrado por el miembro, destino PERSONAL,
        "balance_shared": int -> total ahorrado por el miembro, destino SHARED,
        "history": list[SavingEntry] -> Copia completa de movimientos del miembro
        }
        """
        return self.savings_tracker.get_member_summary(member_name)

    def get_saving_goal_status(self, member_name):
        self.validate_member_exist(member_name)
        committed = self._saving_goals.get(member_name, 0)
        summary = self.get_member_savings_summary(member_name)
        paid = summary["balance_personal"] + summary["balance_shared"]
        return {"committed": committed, "paid": paid, "remaining": committed - paid}

    def get_bucket_by_id(self, bucket_id: UUID) -> SavingBucket:
        return self.savings_tracker.get_bucket_by_id(bucket_id)

    def get_all_buckets(self) -> dict[UUID, SavingBucket]:
        return self.savings_tracker.get_all_buckets()

    def get_buckets_by_member(self, member_name: str) -> dict[UUID, SavingBucket]:
        return self.savings_tracker.get_buckets_by_member(member_name)

    def get_savings_total_shared(self) -> int:
        return self.savings_tracker.get_total_shared()

    def get_savings_shared_by_period(self, start_date: date, end_date: date) -> dict:
        return self.savings_tracker.get_shared_by_period(start_date, end_date)

    # ====== VALIDATORS ======

    def validate_has_members(self):
        """Valida que hay miembros registrados"""
        if not self.members:
            raise ValueError("No hay miembros registrados")

    def validate_total_incomes_positive(self):
        """Valida que el ingreso total es mayor a 0 (usa datos congelados si están disponibles)"""
        # Usar datos congelados si están disponibles (PLANNING/MONTH)
        if self._registered_incomes:
            incomes = list(self._registered_incomes.values())
        else:
            # Usar datos mutables solo en REGISTRATION
            incomes = [m.monthly_income for m in self.members.values()]

        total = FinanceCalculator.sum_values(incomes)
        if total <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos > 0")

    def _validate_all_members_have_split(self, splits: dict[str, float]):
        """Valida que todos los miembros tienen asignado un porcentaje"""
        for name in self.members:
            if name not in splits:
                raise ValueError(f"Falta el porcentaje para el miembro: {name}")

    def validate_category_exist(self, category: str):
        """Valida que una categoría existe en el presupuesto"""
        return self.budget._validate_category_exists(category)

    def validate_member_exist(self, member_name: str):
        """Valida que un miembro existe en el hogar"""
        member_name = normalize_name(member_name)
        if member_name not in self.members:
            raise ValueError(f"{member_name} no existe en el hogar")
