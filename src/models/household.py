from typing import Dict
from src.models.member import Member
from src.models.budget import Budget
from src.models.expense import Expense
from src.models.saving_tracker import SavingTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.finance_calculator import FinanceCalculator
from src.models.constants import MetodoReparto, SavingDestination, CategoryBehavior
from src.utils.currency import to_percentage_basis
from src.utils.text import normalize_name


class Household:
    def __init__(
        self,
        budget: Budget,
        expense_tracker: ExpenseTracker,
        saving_tracker: SavingTracker,
        method: MetodoReparto = MetodoReparto.PROPORTIONAL,
    ) -> None:

        self.members: Dict[str, Member] = {}
        self.budget = budget
        self.expense_tracker: ExpenseTracker = expense_tracker
        self.savings_tracker: SavingTracker = saving_tracker
        self.method: MetodoReparto = method
        self._custom_splits = {}
        self._registered_incomes = {}
        self._member_debts: dict[str, int] = {}  # {member_name: amount_cents}
        self._saving_goals: dict[str, int] = {}  # {member_name: amount_cents}
        self._agreed_percentages = {}
        self._agreed_contributions = {}

    # ====== MEMBERS MANAGEMENT ======
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

    # ====== REGISTRATION STATE (freeze/unfreeze) ======
    def freeze_registration_state(self):
        """Congela los ingresos registrados al pasar a fase PLANNING"""
        self._registered_incomes = {
            name: member.monthly_income for name, member in self.members.items()
        }
        for name in self.members:
            self.savings_tracker.create_account(
                name
            )  # ← solo cuando el registro es definitivo

    # ====== PLANNING - CATEGORY MANAGEMENT ======
    def add_category(self, name: str):
        """Agrega categoría y la propaga a Budget"""
        self.budget.add_category(name)

    def remove_category(self, name: str):
        """Elimina categoría"""
        self.budget.delete_budget_category(name)

    def set_standard_categories(self):
        self.budget.set_standard_categories()

    def get_active_categories(self) -> list[str]:
        """Lista categorías activas"""
        return self.budget.get_categories_list()

    def get_category_budget(self, name: str) -> int:
        """Obtiene presupuesto asignado a una categoría"""
        return self.budget.get_category_budget(name)

    # ====== PLANNING - BUDGET ASSIGNMENT ======
    def set_budget_for_category(self, category: str, amount_cents: int) -> None:
        """Asigna presupuesto a una categoría en fase PLANNING (céntimos)"""
        self.budget.set_budget(category, amount_cents)

    def set_budget_by_percentage(self, pct_basis: int, category: str):
        """Asigna presupuesto a una categoría con el porcentaje del total de ingresos"""
        total_incomes = self.get_total_incomes()
        amount_cents = (total_incomes * pct_basis) // 10000
        self.set_budget_for_category(category=category, amount_cents=amount_cents)

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

    # ====== PLANNING -  SET DEBT - Declarar deuda para cada miembro ======
    def set_member_debt(self, member_name: str, amount_cents: int) -> None:
        """Declara la deuda personal mensual de un miembro (PLANNING)"""
        self._validate_member_exist(member_name)
        self._member_debts[member_name] = amount_cents

    # ====== PLANNING -  SET SAVING GOAL  ======
    def set_member_saving_goal(self, member_name: str, amount_cents: int) -> None:
        """Declara el ahorro personal mensual de un miembro (PLANNING)"""
        self._validate_member_exist(member_name)
        self._saving_goals[member_name] = amount_cents  # (+=)

    # ====== PLANNING -  DISTRIBUTION CONFIGURATION ======
    def assign_distribution_method(self, method: MetodoReparto):
        """Establece método de reparto"""
        self.method = method

    def set_custom_splits(self, splits: dict[str, float]):
        """Define porcentajes de reparto personalizados (0-100)"""
        self._validate_has_members()
        self._validate_all_members_have_split(splits)

        self._custom_splits = {
            name: to_percentage_basis(pct) for name, pct in splits.items()
        }

    # ====== PLANNING STATE (freeze/unfreeze) ======
    def validate_debt_and_saving_dont_exceed_capacity(self):
        """
        Valida que los compromisos personales (deuda + ahorro) no superen
        la parte de 'reserva' que le corresponde a cada miembro.
        """
        contributions = self.get_current_contributions()

        reserva_contributions = {}
        if "reserva" in contributions:
            reserva_contributions = contributions["reserva"]["contributions"]

        for member in self.members:
            capacity = reserva_contributions.get(member, 0)
            debt = self._member_debts.get(member, 0)
            saving = self._saving_goals.get(member, 0)

            if (debt + saving) > capacity:
                raise ValueError(
                    f"Compromisos ({debt + saving}¢) de {member} superan su "
                    f"parte de reserva ({capacity}¢)"
                )

    def freeze_planning_state(self):
        """Congela el estado de planificación al pasar a fase MONTH"""
        self._agreed_percentages = self.get_percentages_by_method(self.method)
        self._agreed_contributions = self.get_current_contributions()

    # ====== SAVINGS (MONTH phase) ======
    def register_savings_deposit(
        self,
        member_name: str,
        amount_cents: int,
        destination: SavingDestination,
        description="",
        date=None,
    ):
        """"""
        self._validate_member_exist(member_name)

        self.savings_tracker.deposit(
            member_name=member_name,
            amount_cents=amount_cents,
            destination=destination,
            description=description,
            date=date,
        )

    def register_savings_withdrawal(
        self,
        member_name: str,
        amount_cents: int,
        destination: SavingDestination,
        description="",
        date=None,
    ):
        """"""
        self._validate_member_exist(member_name)

        self.savings_tracker.withdraw(
            member_name=member_name,
            amount_cents=amount_cents,
            destination=destination,
            description=description,
            date=date,
        )

    def get_member_savings_summary(self, member_name: str):
        """Retorna dict resumen:
        {
        "balance_total" : int -> total ahorrado por el miembro,
        "balance_personal": int -> total ahorrado por el miembro, destino PERSONAL,
        "balance_shared": int -> total ahorrado por el miembro, destino SHARED,
        "history": list[SavingEntry] -> Copia completa de movimientos del miembro,
        "actual_month": {
            "personal":int -> suma de ahorro personal del mes actual,
            "shared":int -> suma de ahorro compartido del mes actual
        }
        }
        """
        return self.savings_tracker.get_member_summary(member_name)

    # ====== EXPENSES (MONTH phase) ======
    def register_expense(self, expense: Expense):
        """Registra un gasto (almacena solo en ExpenseTracker)"""
        self._validate_member_exist(expense.member)
        self._validate_category_exist(expense.category)
        self.expense_tracker.add_expense(expense)

    # ====== QUERIES - REGISTRATION ======
    def get_registration_summary(self):
        """Resumen de fase REGISTRATION: miembros e ingresos"""
        self._validate_has_members()
        self._validate_total_incomes_positive()
        member_incomes = {name: m.monthly_income for name, m in self.members.items()}
        total_incomes = self.get_total_incomes()
        return {
            "members": list(self.members.keys()),
            "member_incomes": member_incomes,
            "total_household_income": total_incomes,
        }

    # ====== QUERIES - PLANNING ======
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
            else:
                # PROPORTIONAL y EQUAL ambos calculan desde ingresos directamente
                # La diferencia está en cómo se ponderan (por ingreso o igual)
                if method == MetodoReparto.EQUAL:
                    equal_income_map = {name: 1 for name in income_map}
                    contributions = (
                        FinanceCalculator.calculate_contribution_from_incomes(
                            equal_income_map, category.planned_amount
                        )
                    )
                else:
                    contributions = (
                        FinanceCalculator.calculate_contribution_from_incomes(
                            income_map, category.planned_amount
                        )
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

    def get_registered_incomes(self) -> dict[str, int]:
        """Obtiene ingresos congelados (disponible en PLANNING/MONTH)"""
        if not self._registered_incomes:
            raise ValueError(
                "Los ingresos no han sido congelados. Llama a finish_registration() primero."
            )
        return self._registered_incomes.copy()

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

    def get_category_behavior(self, category: str) -> CategoryBehavior:
        """Retorna el behavior de una categoría activa"""
        self._validate_category_exist(category)
        return self.budget.categories[category].behavior

    def get_member_debts(self):
        return self._member_debts

    def get_saving_goals(self):
        return self._saving_goals

    def get_total_budgeted(self):
        """Obtiene total presupuestado (cents)"""
        return self.budget.get_total_budgeted()

    def get_missing_money(self):
        """Calcula dinero no presupuestado (ingresos - total_budgeted).
        Puede ser negativo si el presupuesto supera los ingresos."""
        total_incomes = self.get_total_incomes()
        total_budgeted = self.budget.get_total_budgeted()
        return total_incomes - total_budgeted

    def get_missing_money_by_member(self, name: str) -> int:
        name = normalize_name(name)
        self._validate_member_exist(name)
        income_map = self._registered_incomes or {
            n: m.monthly_income for n, m in self.members.items()
        }
        missing_money = self.get_missing_money()

        if self.method == MetodoReparto.CUSTOM:
            return FinanceCalculator.calculate_contribution_from_custom_splits(
                self._custom_splits, missing_money
            )[name]
        elif self.method == MetodoReparto.EQUAL:
            equal_map = {n: 1 for n in income_map}
            return FinanceCalculator.calculate_contribution_from_incomes(
                equal_map, missing_money
            )[name]
        else:
            return FinanceCalculator.calculate_contribution_from_incomes(
                income_map, missing_money
            )[name]

    def get_planning_summary(self) -> dict:
        """
        Resumen completo de fase PLANNING con el método ya configurado.
        Incluye: miembros, ingresos, método, porcentajes, categorías, presupuestos, missing_money, preview de contribuciones.
        """
        self._validate_has_members()
        self._validate_total_incomes_positive()
        members = list(self.members.keys())
        total_incomes = self.get_total_incomes()
        categories = self.get_active_categories()
        debts = self.get_member_debts()
        saving_goals = self.get_saving_goals()
        total_budgeted = self.get_total_budgeted()
        missing_money = total_incomes - total_budgeted
        missing_money_by_member = {
            name: self.get_missing_money_by_member(name) for name in members
        }
        percentages = self.get_percentages_by_method(self.method)

        contributions = self.get_current_contributions()

        member_incomes = {name: m.monthly_income for name, m in self.members.items()}

        return {
            "members": members,
            "member_incomes": member_incomes,
            "total_household_income": total_incomes,
            "distribution_method": self.method.value,
            "distribution_percentages": percentages,
            "categories": categories,
            "budget_by_category": {
                cat: self.budget.categories[cat].planned_amount for cat in categories
            },
            "debt": debts,
            "saving_goal": saving_goals,
            "total_budgeted": total_budgeted,
            "missing_money": {
                "total": missing_money,
                "by_member": missing_money_by_member,
            },
            "contributions_preview": contributions,
        }

    # ====== QUERIES - MONTH ======
    def get_member_owed_total(self, member_name: str) -> int:
        """Cuánto acordó pagar el miembro"""
        member_name = normalize_name(member_name)
        self._validate_member_exist(member_name)
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
        self._validate_member_exist(member_name)
        owed = self.get_member_owed_total(member_name)
        paid = self.get_member_paid_total(member_name)

        return paid - owed

    def get_member_status(self, member_name: str) -> dict:
        """Retorna dict: {income, owed, paid, balance, contributions_by_category}"""
        member_name = normalize_name(member_name)
        self._validate_member_exist(member_name)
        # Totales
        member_income = self.members[member_name].monthly_income

        owed = self.get_member_owed_total(member_name)
        paid = self.expense_tracker.get_total_spent_by_member(member_name)
        balance = self.get_member_balance(member_name)

        # Acordado vs pagado
        agreed_contributions = self.get_agreed_contributions()
        by_category = {}

        for cat_name, cat_data in agreed_contributions.items():
            contribution = cat_data["contributions"][member_name]
            paid_in_category = (
                self.expense_tracker.get_total_spent_by_member_and_category(
                    member=member_name, category=cat_name
                )
            )

            by_category[cat_name] = {
                "contribution": contribution,
                "paid": paid_in_category,
                "remaining": contribution - paid_in_category,
            }

        return {
            "income": member_income,
            "owed": owed,
            "paid": paid,
            "balance": balance,
            "debt": self._member_debts.get(member_name, 0),
            "saving_goal": self._saving_goals.get(member_name, 0),
            "by_category": by_category,
        }

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

    def get_month_summary(self):
        """
        Retorna resumen financiero completo del mes:

        {
            "totals": {
                "total_budgeted":  300000,   # céntimos presupuestados
                "total_spent":      95000,   # céntimos gastados
                "total_remaining": 205000    # céntimos restantes
            },
            "by_category": {
                "fijos": {
                    "budget":    150000,
                    "spent":      80000,
                    "remaining":  70000
                }
            },
            "by_member": {
                "amanda": {
                    "income":  200000,
                    "owed":    200000,
                    "paid":     80000,
                    "balance": -120000,      # negativo = debe dinero
                    "debt": cuanto paga cada miembro de deuda,
                    "saving_goal": cuanto ahorra cada miembro,
                    "by_category": {
                        "fijos": {
                            "contribution": 100000,
                            "paid":          80000,
                            "remaining":     20000
                        }
                    }
                }
            },
            "missing_money": {
                "total": 0,
                "by_member": {
                    "amanda": 0,
                    "heri":   0
                }
            }
        }
        """

        categories = self.get_active_categories()
        members = self.members.keys()
        total_budgeted = self.get_total_budgeted()

        missing_money_total = self.get_missing_money()
        missing_money_by_member = {
            member: self.get_missing_money_by_member(member) for member in members
        }
        total_spent = self.get_total_spent()
        total_remaining = self.get_total_remaining()

        # Total presupuestado + total gastado + total restante
        total = {
            "total_budgeted": total_budgeted,
            "total_spent": total_spent,
            "total_remaining": total_remaining,
        }

        # Categoría {Presupuestado + Gastado + faltante por pagar} + {missing_money}
        by_category = {}
        for cat in categories:
            by_category[cat] = {
                "budget": self.budget.get_category_budget(cat),
                "spent": self.get_category_spent(cat),
                "remaining": self.get_category_remaining(cat),
            }
        by_member = {member: self.get_member_status(member) for member in members}

        return {
            "totals": total,
            "by_category": by_category,
            "by_member": by_member,
            "missing_money": {
                "total": missing_money_total,
                "by_member": missing_money_by_member,
            },
        }

    def get_settlement(self) -> list[dict]:
        """
        Calcula las transferencias mínimas para saldar deudas entre miembros.
        Solo opera sobre gastos con is_shared=True.

        Returns:
            list[dict]: [{"from": "heri", "to": "amanda", "amount": 50000}]
            Lista vacía si no hay gastos compartidos o todo está saldado.
        """
        income_map = self._registered_incomes or {
            name: m.monthly_income for name, m in self.members.items()
        }

        shared_paid = self.expense_tracker.get_shared_expenses_by_members()
        total_shared = sum(shared_paid.values())

        if total_shared == 0:
            return []

        # Cuánto debería pagar cada miembro según el método de reparto
        if self.method == MetodoReparto.CUSTOM:
            should_pay = FinanceCalculator.calculate_contribution_from_custom_splits(
                self._custom_splits, total_shared
            )
        elif self.method == MetodoReparto.EQUAL:
            equal_map = {name: 1 for name in income_map}
            should_pay = FinanceCalculator.calculate_contribution_from_incomes(
                equal_map, total_shared
            )
        else:
            should_pay = FinanceCalculator.calculate_contribution_from_incomes(
                income_map, total_shared
            )

        # balance positivo → acreedor (pagó de más)
        # balance negativo → deudor (pagó de menos)
        balances = {
            m: shared_paid.get(m, 0) - should_pay.get(m, 0)
            for m in self.members
        }

        creditors = sorted(
            [(m, b) for m, b in balances.items() if b > 0],
            key=lambda x: -x[1],
        )
        debtors = sorted(
            [(m, -b) for m, b in balances.items() if b < 0],
            key=lambda x: -x[1],
        )

        # Greedy: mayor deudor paga al mayor acreedor, actualizar y avanzar
        transfers = []
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            debtor_name, debt = debtors[i]
            creditor_name, credit = creditors[j]

            amount = min(debt, credit)
            transfers.append({
                "from": debtor_name, "to": creditor_name, "amount": amount
            })

            debt -= amount
            credit -= amount

            debtors[i] = (debtor_name, debt)
            creditors[j] = (creditor_name, credit)

            if debt == 0:
                i += 1
            if credit == 0:
                j += 1

        return transfers


            
    # ====== INTERNAL HELPERS ======
    def get_total_incomes(self):
        """Calcula el ingreso total mensual (usa datos congelados si están disponibles)"""
        self._validate_has_members()
        self._validate_total_incomes_positive()

        # Usar datos congelados si están disponibles (PLANNING/MONTH)
        if self._registered_incomes:
            incomes = list(self._registered_incomes.values())
        else:
            # Usar datos mutables solo en REGISTRATION
            incomes = [m.monthly_income for m in self.members.values()]

        total = FinanceCalculator.sum_values(incomes)
        return total

    def get_percentages_by_method(self, method: MetodoReparto):
        """Calcula el porcentaje de reparto (usa datos congelados si están disponibles)"""
        self._validate_has_members()
        self._validate_total_incomes_positive()

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

    # ====== VALIDATORS ======
    def _validate_has_members(self):
        """Valida que hay miembros registrados"""
        if not self.members:
            raise ValueError("No hay miembros registrados")

    def _validate_total_incomes_positive(self):
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

    def _validate_category_exist(self, category: str):
        """Valida que una categoría existe en el presupuesto"""
        return self.budget._validate_category_exists(category)

    def _validate_member_exist(self, member_name: str):
        """Valida que un miembro existe en el hogar"""
        member_name = normalize_name(member_name)
        if member_name not in self.members:
            raise ValueError(f"{member_name} no existe en el hogar")
