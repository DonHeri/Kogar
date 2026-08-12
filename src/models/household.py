from datetime import datetime, date
from typing import Dict
from uuid import UUID

from src.models.budget import Budget
from src.models.budget_category import BudgetCategory
from src.models.category import AutoCalculatedCategory
from src.models.constants import MetodoReparto
from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.models.finance_calculator import FinanceCalculator
from src.models.member import Member
from src.models.income_entry import IncomeEntry
from src.models.saving_bucket import SavingBucket
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.models.debt_bucket import DebtBucket

from src.models.debt_bucket_tracker import DebtBucketTracker
from src.utils.text import normalize_name


class Household:
    def __init__(
        self,
        budget: Budget,
        expense_tracker: ExpenseTracker,
        saving_bucket_tracker: SavingBucketTracker,
        debt_bucket_tracker: DebtBucketTracker,
        method: MetodoReparto = MetodoReparto.PROPORTIONAL,
    ) -> None:

        self.members: Dict[str, Member] = {}
        self.budget = budget
        self.expense_tracker: ExpenseTracker = expense_tracker
        self.saving_bucket_tracker: SavingBucketTracker = saving_bucket_tracker
        self.debt_bucket_tracker: DebtBucketTracker = debt_bucket_tracker
        self.method: MetodoReparto = method
        self._custom_splits = {}
        self._agreed_percentages = {}
        self._agreed_contributions = {}
        self._income_entries: list[IncomeEntry] = []

    # ====== MIEMBROS ======

    def register_member(self, member: Member):
        """Registra un nuevo miembro en el hogar, con su bucket de ahorro personal"""
        if member.name in self.members:
            raise ValueError(f"{member.name} ya está registrado en el hogar")

        self.members[member.name] = member
        self._create_personal_saving_bucket(member.name)

    def set_member_income(self, name: str, amount_cents: int):
        """Establece el ingreso mensual de un miembro (en céntimos)"""
        name = normalize_name(name)
        if name not in self.members:
            raise ValueError(f"{name} no existe en el hogar")

        self.members[name].set_income(amount_cents)
        self.budget.recalculate_percentage_categories(self.get_incomes())

    def prepare_period(self):
        """Deja el hogar listo para planificar: buckets personales y categorías base.

        Ya no congela ingresos: mientras el período está abierto manda el ingreso
        vivo del miembro, y el acuerdo del mes se congela en freeze_planning_state().
        """
        self._create_personal_saving_bucket_for_members()

        if self.members and not self.budget.categories:
            self.budget.set_standard_categories(self.get_member_names())

    def _create_personal_saving_bucket(self, name: str) -> None:
        """Crea el bucket de ahorro personal de un miembro si aún no lo tiene."""
        if self.saving_bucket_tracker.get_default_bucket_by_member(name):
            return

        personal_bucket = SavingBucket(
            saving_bucket_name=f"{name}'s personal saving",
            owners=[name],
            is_default=True,
        )
        self.saving_bucket_tracker.add_bucket(personal_bucket)

    def _create_personal_saving_bucket_for_members(self):
        """Asegura el bucket de ahorro personal de todos los miembros. Idempotente."""
        for name in self.members:
            self._create_personal_saving_bucket(name)

    # ====== PLANNING — CATEGORIES ======

    def add_category(
        self,
        name: str,
        participants: list[str] | None = None,
        parent: str | None = None,
        method: MetodoReparto | None = None,
        custom_splits: dict[str, int] | None = None,
    ):
        """Agrega categoría y la propaga a Budget.

        En una hija, `participants=None` hereda los del padre. Es el único caso
        en que puede faltar: una raíz no tiene de quién heredar.
        """
        participants_normalized = self._validate_participants_are_members(participants)

        if method is None:
            method = self.method

        self.budget.add_category(
            name,
            participants=participants_normalized,
            parent=parent,
            method=method,
            custom_splits=custom_splits,
        )

    def _validate_participants_are_members(
        self, participants: list[str] | None
    ) -> list[str] | None:
        """Valida que cada participante viva en el hogar.

        Budget no puede comprobarlo: no conoce a los miembros. Sin esto, una
        categoría reparte entre alguien que no existe y el reparto revienta
        más tarde, lejos de donde se declaró el error.
        """
        participants_normalized: list[str] = []
        if participants is None:
            return

        for name in participants:
            normalized = normalize_name(name)
            self.validate_member_exist(normalized)
            participants_normalized.append(normalized)
        return participants_normalized

    def remove_category(self, name: str):
        """Elimina una categoría y resuelve el destino de sus gastos.

        Los gastos de una hija suben a su padre: es neutro, porque ya contaban
        dentro de su techo. Una raíz no tiene a quién subirlos, así que con
        gastos no se puede borrar.

        Que la categoría tenga hijas lo vigila Budget, que es quien es dueño
        del árbol.
        """
        normalized = normalize_name(name)
        parent = self.budget.get_budget_category(name=normalized).parent

        if parent is not None:
            self._reassign_expenses(from_category=normalized, to_category=parent)
        elif self.get_category_spent(category_name=normalized) > 0:
            raise ValueError(
                f"No se puede borrar la categoría {normalized} porque tiene gastos "
                "asociados. Muévelos a otra categoría antes de borrar."
            )

        self.budget.delete_budget_category(normalized)

    def _reassign_expenses(self, from_category: str, to_category: str) -> None:
        """Mueve los gastos de una categoría a otra"""
        destination = self.budget.get_category(to_category)
        for expense in self.expense_tracker.filter_expenses(categories=[from_category]):
            expense.category = destination

    def set_standard_categories(self):
        """Categorías estándar con todo el hogar dentro. Muere en P5."""
        self.budget.set_standard_categories(self.get_member_names())

    # ====== PLANNING — BUDGET ======

    def set_planned_percentage(self, category: str, percentage: int) -> None:
        """Declara el techo de una categoría como % del ingreso de sus propios
        participantes, no del total del hogar. Se resuelve aquí y no en Budget,
        porque Budget no conoce ingresos — Household es quien tiene los dos
        datos a la vez.
        """
        participants = self.budget.get_budget_category(category).participants
        incomes = self.get_incomes()
        participants_income = sum(incomes[name] for name in participants)
        resolved_amount_cents = participants_income * percentage // 10000
        self.budget.set_planned_percentage(category, percentage, resolved_amount_cents)

    # ====== PLANNING — DISTRIBUTION ======

    def set_distribution_method(self, method: MetodoReparto):
        """Establece método de reparto"""
        self.method = method

    def set_custom_splits(self, splits: dict[str, int]):
        """Define porcentajes de reparto personalizados, en basis points.

        52.99% entra como 5299. La conversión desde 0-100 la hacen los bordes,
        que es donde vive to_percentage_basis: el dominio no habla en floats.
        Así el usuario y la BD entran por la misma puerta, sin que rehidratar
        vuelva a multiplicar por 100.

        Definirlos deja el método en CUSTOM. Es la única razón para definirlos,
        y separarlo permitía guardar unos porcentajes que el reparto ignoraba
        sin avisar. Como invariante vive aquí: si lo hiciera cada cliente, basta
        que uno se olvide para volver a los datos muertos.
        """
        self.validate_has_members()
        self._validate_all_members_have_split(splits)
        self._validate_splits_add_up(splits)

        self._custom_splits = dict(splits)
        self.method = MetodoReparto.CUSTOM

    def get_custom_splits(self):
        return self._custom_splits

    def validate_debt_doesnt_exceed_capacity(self):
        """Valida que la deuda (obligación real) de cada miembro no supere su
        parte de reserva. El ahorro NO se valida aquí — es elección, no obligación."""
        for member in self.members:
            reserve_capacity = self.get_reserve_contribution_by_member(member)
            debt = self.debt_bucket_tracker.total_expected_installment_by_member(
                member_name=member
            )
            if debt > reserve_capacity:
                raise ValueError(
                    f"La deuda ({debt}¢) de {member} supera su "
                    f"parte de reserva ({reserve_capacity}¢)"
                )

    def freeze_planning_state(self):
        """Congela el estado de planificación al pasar a fase MONTH"""
        self._agreed_percentages = self.get_percentages_by_method(self.method)
        self._agreed_contributions = self.get_contributions_by_category()

    def restore_agreement(
        self,
        contributions: dict[str, dict[str, int]],
        percentages: dict[str, int],
    ):
        """Repone el acuerdo congelado que viene de BD.

        Recibe lo mismo que produce freeze_planning_state, en la misma forma: el
        acuerdo tiene una sola representación, se calcule o se lea.
        """
        self._agreed_contributions = {
            category: dict(by_member) for category, by_member in contributions.items()
        }
        self._agreed_percentages = dict(percentages)

    # ====== MONTH — EXPENSES ======

    def register_expense(self, expense: Expense):
        """Registra un gasto (almacena solo en ExpenseTracker)"""
        self.validate_member_exist(expense.member)
        self.validate_category_exist(expense.category.name)

        # Validar participantes
        for participant in expense.participants:
            self.validate_member_exist(participant)

        # Agregar expense
        self.expense_tracker.add_expense(expense)

    # ====== MONTH — DEBT BUCKETS ======
    def add_debt_bucket(self, debt_bucket: DebtBucket) -> UUID:
        """Registra un bucket de deuda personal (un único owner)."""
        self.validate_member_exist(member_name=debt_bucket.owner)
        bucket_id = self.debt_bucket_tracker.add_bucket(debt_bucket)

        return bucket_id

    def set_debt_bucket_installment(self, bucket_id: UUID, amount_cents: int):
        """Fija la cuota mensual de un bucket (la settea el usuario)"""
        self.debt_bucket_tracker.set_bucket_installment(
            bucket_id=bucket_id, amount_cents=amount_cents
        )

    def register_debt_payment(
        self,
        member_name: str,
        amount_cents: int,
        bucket_id: UUID,
        payment_date: datetime | None = None,
    ):
        """Registra un pago de deuda validando que no supera el compromiso del mes.

        El histórico entre meses vive en BD (DebtRepository).
        """
        self.validate_member_exist(member_name)

        self.debt_bucket_tracker.pay(
            amount_cents=amount_cents,
            bucket_id=bucket_id,
            date=payment_date,
            member_name=member_name,
        )

    def get_debt_status_by_member(
        self, member_name: str, start_date: date, end_date: date | None = None
    ):
        """Resumen de deuda de un miembro en el período: detalle por bucket + totales."""
        self.validate_member_exist(member_name)
        return self.debt_bucket_tracker.member_debt_summary(
            member_name, start_date, end_date
        )

    def get_debt_installment_by_member(self, member_name: str) -> int:
        """Cuota mensual comprometida por el miembro, sumando todos sus buckets."""
        return self.debt_bucket_tracker.total_expected_installment_by_member(
            member_name
        )

    def get_debt_history(self, member_name: str) -> list:
        """Todos los pagos de deuda de un miembro, en todos sus buckets."""
        self.validate_member_exist(member_name)
        history: list = []
        for bucket in self.debt_bucket_tracker.get_bucket_by_member(
            member_name
        ).values():
            history.extend(bucket.entries)
        return history

    def get_all_debts_summary(
        self, start_date: date, end_date: date | None = None
    ) -> dict:
        """Resumen de deuda de todos los miembros del hogar."""
        return {
            member: self.debt_bucket_tracker.member_debt_summary(
                member, start_date, end_date
            )
            for member in self.members
        }

    # ====== MONTH — SAVING BUCKETS ======
    def add_saving_bucket(self, bucket: SavingBucket) -> UUID:
        bucket_id = self.saving_bucket_tracker.add_bucket(bucket)
        return bucket_id

    def deposit_to_saving_bucket(
        self, bucket_id: UUID, member_name: str, amount_cents: int, date=None
    ) -> None:
        self.validate_member_exist(member_name)
        self.saving_bucket_tracker.deposit(bucket_id, amount_cents, member_name, date)

    def withdraw_from_bucket(
        self, bucket_id: UUID, member_name: str, amount_cents: int, date=None
    ) -> None:
        self.validate_member_exist(member_name)
        self.saving_bucket_tracker.withdraw(bucket_id, amount_cents, member_name, date)

    def get_saving_status_by_member(
        self, member_name: str, start_date: date, end_date: date
    ) -> dict:
        """Resumen de ahorro de un miembro en el período: detalle por bucket + totales."""
        self.validate_member_exist(member_name)
        return self.saving_bucket_tracker.member_saving_summary(
            member_name, start_date, end_date
        )

    def get_saving_requirement_by_member(self, member_name: str) -> int:
        """Cuánto exigirían las metas del miembro este mes (informativo, snapshot de hoy)."""
        return self.saving_bucket_tracker.total_required_contribution_by_member(
            member_name
        )

    def get_all_savings_summary(
        self, start_date: date, end_date: date | None = None
    ) -> dict:
        """Resumen de ahorro de todos los miembros del hogar."""
        return {
            member: self.saving_bucket_tracker.member_saving_summary(
                member, start_date, end_date
            )
            for member in self.members
        }

    # ====== MONTH — NEW MONTH ======

    def reset_for_new_month(self):
        """Reinicia el estado mutable del período. Miembros, categorías.
        También se reinicia el estado de ExpenseTracker para evitar acumulación de
        movimientos pasados. DebtBucketTracker y SavingBucketTracker NO se reinician:
        la deuda y el ahorro son household-scoped y cruzan meses."""
        self.expense_tracker = ExpenseTracker()
        self._agreed_contributions = {}
        self._agreed_percentages = {}

        self._income_entries = list()

    # ====== QUERIES — MIEMBROS ======

    def get_member_names(self) -> list[str]:
        """Devuelve los nombres de miembros registrados en el núcleo familiar"""
        return list(self.members.keys())

    def get_incomes(self) -> dict[str, int]:
        """Ingreso mensual vivo de cada miembro (céntimos)"""
        return {name: member.monthly_income for name, member in self.members.items()}

    # ====== QUERIES — PLANNING ======

    def get_budget_categories(self) -> dict[str, BudgetCategory]:
        """Retorna todas las categoría con presupuesto activas"""
        return self.budget.get_budget_categories()

    def get_active_categories(self) -> list[str]:
        """Lista categorías activas"""
        return self.budget.get_category_names()

    def get_category_planned_amount(self, category: str) -> int:
        """Obtiene presupuesto asignado a una categoría"""
        return self.budget.get_planned_amount(category)

    def get_total_incomes(self):
        """Calcula el ingreso total mensual del hogar.

        Los ingresos extra quedaron fuera del cálculo al retirarse: sumarlos aquí
        movía el presupuesto a mitad de mes y repartía entre todos el extra que
        cobraba uno solo. Vuelven cuando el presupuesto sepa de dueños.
        """
        self.validate_has_members()
        self.validate_total_incomes_positive()

        incomes = list(self.get_incomes().values())

        total = FinanceCalculator.sum_values(incomes)
        return total

    def get_total_budgeted(self):
        """Obtiene total presupuestado (cents)"""
        return self.budget.get_total_budgeted()

    def get_unbudgeted_income(self) -> int:
        """Ingreso sin destino: total de ingresos menos lo presupuestado en
        categorías raíz. Negativo significa que las categorías piden más de
        lo que entra — categorías con porcentaje incluidas, porque su
        `planned_amount` ya se mantiene al día en cada cambio de ingreso.

        No lanza ni bloquea nada: detecta el número, no decide qué hacer con
        él. Avisar es responsabilidad de quien llame (UI/CLI), como ya pasa
        con `missing_money`. Es una pieza estrecha, pensada para el guard de
        P3 — la versión completa y visible del sobrante es la tarea P6.
        """
        return self.get_total_incomes() - self.get_total_budgeted()

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
        category_budget = self.get_category_planned_amount(category)
        total = self.get_total_incomes()
        pct_basis = (category_budget * 10000) // total
        return pct_basis

    def get_percentages_by_method(self, method: MetodoReparto):
        """Calcula el porcentaje de reparto sobre los ingresos vivos"""
        self.validate_has_members()
        self.validate_total_incomes_positive()

        income_map = self.get_incomes()

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
                # El guard mira si el dict tiene contenido, no si el atributo
                # existe: __init__ ya lo crea vacío, así que un hasattr aquí
                # nunca salta y CUSTOM devolvía {} en silencio.
                if not self._custom_splits:
                    raise ValueError(
                        "Método CUSTOM requiere llamar a set_custom_splits() primero"
                    )
                return self._custom_splits

        return percentages

    def get_weights_for(
        self, participants: list[str], method: MetodoReparto
    ) -> dict[str, int]:
        """Traduce un método de reparto a pesos concretos, en basis points ×100.

        El método llega como argumento: **el hogar no impone el suyo**. Cada gasto
        puede repartirse distinto, y quién elige el método de un gasto es el borde.
        Aquí solo se traduce, porque los ingresos y los splits viven en el hogar.

        Los porcentajes del hogar cubren a todos sus miembros; un gasto que
        comparten dos de tres solo puede usar la parte que les toca, renormalizada
        a 10000. Sin renormalizar, el trozo del ausente no lo paga nadie y el
        settlement deja al pagador con un crédito que no reclama a nadie.

        Raises:
            ValueError: si algún participante no es miembro del hogar.
        """
        if method == MetodoReparto.EQUAL:
            return FinanceCalculator.calculate_equal_percentage(
                {name: 1 for name in participants}
            )

        if method == MetodoReparto.CUSTOM:
            source = self.get_percentages_by_method(MetodoReparto.CUSTOM)
        else:
            source = self.get_incomes()

        missing = [name for name in participants if name not in source]
        if missing:
            raise ValueError(
                f"Participantes que no son miembros del hogar: {sorted(missing)}"
            )

        return FinanceCalculator.calculate_percentage_based_on_weight_of_income(
            {name: source[name] for name in participants}
        )

    def get_category_billable(self, category_name: str) -> int:
        """Obtiene el monto billable de una categoría (planificado - planificado de hijas)"""
        return self.budget.get_category_billable(category_name=category_name)

    def get_children(self, category_name: str) -> list[str]:
        """Obtiene nombres de categorías hijas de una categoría padre"""
        return self.budget.get_children(category_name)

    def get_root_categories(self) -> list[str]:
        """Obtiene nombres de categorías raíz (sin padre)"""
        return self.budget.get_root_categories()

    def get_current_contributions(self) -> dict:
        """
        Calcula contribuciones para cada categoría.
        Utiliza el método propio de la categoría, o el método de reparto
        del núcleo para categorías con method = None.

        Returns:
            dict: Por cada categoría:
                - planned: presupuesto planificado (céntimos)
                - contributions: {nombre_miembro: contribución (céntimos)}
                - total_assigned: suma de contributions
        """

        summary = {}
        billable = {}

        for cat_name, budget_category in self.budget.get_budget_categories().items():
            billable[cat_name] = self.budget.get_category_billable(
                category_name=cat_name
            )
            contributions = self.get_contribution(category_name=cat_name)

            summary[cat_name] = {
                "planned": billable[cat_name],
                "contributions": contributions,
                "total_assigned": sum(contributions.values()),
            }

        return summary

    def get_contribution(
        self,
        category_name: str,
        method: MetodoReparto | None = None,
        custom_splits: dict[str, int] | None = None,
    ) -> dict[str, int]:
        """
        Calcula la contribución para un presupuesto.
        Devuelve un dict[member_name:contribution]
        """
        self.validate_category_exist(category=category_name)
        budget_category = self.budget.get_budget_category(name=category_name)
        participants = budget_category.participants
        if method is None:
            method = budget_category.method or self.method

        billable = self.budget.get_category_billable(category_name=category_name)

        if method == MetodoReparto.CUSTOM:
            source = (
                custom_splits
                or budget_category.custom_splits
                or self.get_percentages_by_method(MetodoReparto.CUSTOM)
            )
            return FinanceCalculator.calculate_contribution_from_custom_splits(
                source, billable
            )

        if method == MetodoReparto.EQUAL:
            weight_map = {name: 1 for name in participants}
        else:
            incomes = self.get_incomes()
            missing = [name for name in participants if name not in incomes]
            if missing:
                raise ValueError(
                    f"Participantes que no son miembros del hogar: {sorted(missing)}"
                )
            weight_map = {name: incomes[name] for name in participants}

        return FinanceCalculator.calculate_contribution_from_incomes(
            weight_map, billable
        )

    def get_contributions_by_category(self) -> dict[str, dict[str, int]]:
        """El reparto vigente en su forma mínima: {categoría: {miembro: céntimos}}.

        Es lo que se congela y lo que se persiste. `planned` y `total_assigned`
        se quedan fuera a propósito: el primero ya vive en budget_categories y el
        segundo es la suma de la fila, y dos copias del mismo dato se descuadran.
        """
        return {
            cat: self.get_contribution(cat) for cat in self.budget.get_category_names()
        }

    def preview_with_forced_method(
        self, method: MetodoReparto, custom_splits: dict[str, int] | None = None
    ) -> dict[str, dict[str, int]]:
        """Cómo quedaría el reparto si TODAS las categorías usaran `method`,
        sin tocar el método propio de ninguna. Solo lectura: no muta nada."""
        return {
            cat: self.get_contribution(cat, method=method, custom_splits=custom_splits)
            for cat in self.budget.get_category_names()
        }

    def apply_method_to_all_categories(self, method: MetodoReparto) -> None:
        """Aplica `method` a cada categoría existente, sobrescribiendo la suya.

        A diferencia de `preview_with_forced_method`, esto muta de verdad.
        Reutiliza la validación que ya vive en Budget/BudgetCategory categoría
        por categoría — una CUSTOM sin splits propios lanza igual que ya hacía.
        """
        for cat_name in self.budget.get_category_names():
            self.budget.set_split_method(cat_name, method)

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

    # ====== QUERIES — MONTH ======
    def recalculate_reserve(self):
        """Recalcula la categoría auto-calculada (reserva) según ingresos y presupuestos actuales"""
        reserve_cat = self.budget.get_auto_calculated_category()
        total_incomes = self.get_total_incomes()
        current_reserve = self.get_category_planned_amount(reserve_cat.name)
        other_budgeted = self.get_total_budgeted() - current_reserve

        new_reserve_amount = reserve_cat.calculate_own_budget(
            total_incomes, other_budgeted
        )
        self.budget.set_planned_amount(reserve_cat.name, new_reserve_amount)

    def get_member_owed_total(self, member_name: str) -> int:
        """Cuánto acordó pagar el miembro"""
        member_name = normalize_name(member_name)
        self.validate_member_exist(member_name)
        contributions = self.get_agreed_contributions()
        total = sum(by_member[member_name] for by_member in contributions.values())
        return total

    def get_member_paid_total(self, member_name: str) -> int:
        """Total gastado por un miembro"""
        member_name = normalize_name(member_name)
        return self.expense_tracker.get_total_spent(member=member_name)

    def get_member_balance(self, member_name: str) -> int:
        """Balance: pagado - acordado (negativo = debe, positivo = pagó de más)"""
        member_name = normalize_name(member_name)
        self.validate_member_exist(member_name)
        owed = self.get_member_owed_total(member_name)
        paid = self.get_member_paid_total(member_name)

        return paid - owed

    def get_category_spent(self, category_name: str) -> int:
        """Total gastado en una categoría y en las que cuelgan de ella.

        En una hoja no hay hijas, así que es su propio gasto.
        """
        subtree = [category_name] + self.get_children(category_name)
        return self.expense_tracker.get_total_spent(categories=subtree)

    def get_total_spent(self) -> int:
        """Obtiene total gastado (consulta ExpenseTracker)"""
        return self.expense_tracker.get_total_spent()

    def get_category_remaining(self, category_name: str) -> int:
        """Presupuesto restante: planificado menos gastado, contando el subárbol.

        Puede salir negativo: gastar por encima del techo es información, no un
        error, así que no se limita.
        """
        budgeted = self.budget.get_planned_amount(category_name)
        spent = self.get_category_spent(category_name)
        return budgeted - spent

    def get_total_remaining(self) -> int:
        """Calcula total restante: presupuesto total - total gastado"""
        budgeted = self.get_total_budgeted()
        spent = self.get_total_spent()
        return budgeted - spent

    def get_bucket_by_id(self, bucket_id: UUID) -> SavingBucket:
        return self.saving_bucket_tracker.get_bucket_by_id(bucket_id)

    def get_all_buckets(self) -> dict[UUID, SavingBucket]:
        return self.saving_bucket_tracker.get_all_buckets()

    def get_buckets_by_member(self, member_name: str) -> dict[UUID, SavingBucket]:
        return self.saving_bucket_tracker.get_bucket_by_member(member_name)

    def get_shared_buckets(self, member_name: str) -> dict[UUID, SavingBucket]:
        return self.saving_bucket_tracker.get_shared_buckets(member_name)

    def get_savings_total_shared(self) -> int:
        return self.saving_bucket_tracker.get_total_shared()

    def get_savings_shared_by_period(self, start_date: date, end_date: date) -> dict:
        return self.saving_bucket_tracker.get_shared_by_period(start_date, end_date)

    # ====== VALIDATORS ======

    def validate_has_members(self):
        """Valida que hay miembros registrados"""
        if not self.members:
            raise ValueError("No hay miembros registrados")

    def validate_total_incomes_positive(self):
        """Valida que el ingreso total es mayor a 0"""
        incomes = list(self.get_incomes().values())

        total = FinanceCalculator.sum_values(incomes)
        if total <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos > 0")

    def _validate_all_members_have_split(self, splits: dict[str, int]):
        """Valida que todos los miembros tienen asignado un porcentaje"""
        for name in self.members:
            if name not in splits:
                raise ValueError(f"Falta el porcentaje para el miembro: {name}")

    def _validate_splits_add_up(self, splits: dict[str, int]):
        """Valida que los porcentajes suman 100%.

        Se lanza en vez de normalizar a propósito. Ajustar un 70/40 a 63.6/36.4
        dejaría el acuerdo congelado distinto de lo que el usuario escribió, y
        son el mismo dato: se guardan en la misma fila. Que lo corrija él.

        Sin esta validación el fallo llegaba desde FinanceCalculator con un
        mensaje sobre el "monto presupuestado", que no dice qué hay que arreglar.
        """
        total = sum(splits.values())
        if total != 10000:
            raise ValueError(
                f"Los porcentajes deben sumar 100%, suman {total / 100:.2f}%"
            )

    def validate_category_exist(self, category: str):
        """Valida que una categoría existe en el presupuesto"""
        return self.budget._validate_category_exists(category)

    def validate_member_exist(self, member_name: str):
        """Valida que un miembro existe en el hogar"""
        member_name = normalize_name(member_name)
        if member_name not in self.members:
            raise ValueError(f"{member_name} no existe en el hogar")
