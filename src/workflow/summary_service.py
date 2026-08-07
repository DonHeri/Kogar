from datetime import date

from src.models.household import Household
from src.models.period import Period
from src.utils.text import normalize_name
from src.workflow.settlement_calculator import SettlementCalculator


class SummaryService:
    @staticmethod
    def get_planning_summary(household: Household) -> dict:
        """
        Resumen completo de fase PLANNING con el método ya configurado.
        Incluye: miembros, ingresos, método, porcentajes, categorías, presupuestos, missing_money, preview de contribuciones.
        """
        household.validate_has_members()
        household.validate_total_incomes_positive()
        members = list(household.members.keys())
        total_incomes = household.get_total_incomes()
        categories = household.get_active_categories()
        debts = {
            name: household.get_debt_installment_by_member(name) for name in members
        }
        saving_goals = {
            name: household.get_saving_requirement_by_member(name) for name in members
        }
        total_budgeted = household.get_total_budgeted()

        missing_money_by_member = {
            name: household.get_reserve_contribution_by_member(name) for name in members
        }
        missing_money = sum(missing_money_by_member.values())

        percentages = household.get_percentages_by_method(household.method)

        contributions = household.get_current_contributions()

        member_incomes = {
            name: m.monthly_income for name, m in household.members.items()
        }

        return {
            "members": members,
            "member_incomes": member_incomes,
            "total_household_income": total_incomes,
            "distribution_method": household.method.value,
            "distribution_percentages": percentages,
            "categories": categories,
            "budget_by_category": {
                cat: household.budget.categories[cat].planned_amount
                for cat in categories
            },
            "debts": debts,
            "saving_goals": saving_goals,
            "total_budgeted": total_budgeted,
            "missing_money": {
                "total": missing_money,
                "by_member": missing_money_by_member,
            },
            "contributions_preview": contributions,
        }

    @staticmethod
    def get_member_status(household: Household, member_name: str) -> dict:
        """Retorna dict: {income, owed, paid, balance, contributions_by_category}"""
        member_name = normalize_name(member_name)
        household.validate_member_exist(member_name)
        # Totales
        member_income = household.members[member_name].monthly_income

        owed = household.get_member_owed_total(member_name)
        paid = household.expense_tracker.get_total_spent(member=member_name)
        balance = household.get_member_balance(member_name)

        # Acordado vs pagado
        agreed_contributions = household.get_agreed_contributions()
        by_category = {}

        for cat_name, by_member in agreed_contributions.items():
            contribution = by_member[member_name]
            paid_in_category = household.expense_tracker.get_total_spent(
                member=member_name, categories=[cat_name]
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
            "debt": household.get_debt_installment_by_member(member_name),
            "saving_goal": household.get_saving_requirement_by_member(member_name),
            "by_category": by_category,
        }

    @staticmethod
    def get_month_summary(household: Household):
        """
        Retorna resumen financiero completo del mes:

        {
            "totals": {
                "total_budgeted":  300000,   # céntimos presupuestados
                "total_spent":      95000,   # céntimos gastados
                "total_remaining": 205000    # céntimos restantes
            },
            "by_category": {                 # solo raíces; las hijas van dentro
                "fijos": {
                    "ceiling":     159000,   # techo de la raíz
                    "spent":        80000,   # gasto de todo su subárbol
                    "remaining":    79000,   # techo - gasto; puede ser negativo
                    "billable":     65000,   # lo que reparte por sí misma: techo − Σ hijas
                    "children": {
                        "alquiler": {
                            "ceiling":   80000,
                            "spent":     80000,
                            "remaining":     0
                        }
                    }
                }
            },
            "by_member": {
                "amanda": {
                    "income":  200000,
                    "owed":    200000,
                    "paid":     80000,
                    "balance": -120000,      # negativo = debe dinero
                    "debt": cuanto paga cada miembro de deuda,
                    "saving_goal": cuánto exigen sus metas de ahorro este mes (informativo),
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
                "total": 100000,   # lo que reserva reparte entre los miembros: como
                                    # absorbe todo lo no asignado, es el dinero del
                                    # período que aún no tiene destino
                "by_member": {
                    "amanda": 60000,
                    "heri":   40000
                }
            }
        }
        """

        members = household.members.keys()
        total_budgeted = household.get_total_budgeted()

        missing_money_by_member = {
            member: household.get_reserve_contribution_by_member(member)
            for member in members
        }
        missing_money = sum(missing_money_by_member.values())

        total_spent = household.get_total_spent()
        total_remaining = household.get_total_remaining()

        # Total presupuestado + total gastado + total restante
        totals = {
            "total_budgeted": total_budgeted,
            "total_spent": total_spent,
            "total_remaining": total_remaining,
        }

        # Solo raíces en el primer nivel: sus hijas van dentro, en "children".
        # Así sumar el primer nivel siempre cuadra con los totales, y una hija
        # llamada "spent" no puede pisar un campo del padre.
        by_category = {}

        for cat_name in household.get_root_categories():
            by_category[cat_name] = {
                "ceiling": household.get_category_planned_amount(cat_name),
                "spent": household.get_category_spent(cat_name),
                "remaining": household.get_category_remaining(cat_name),
                "billable": household.get_category_billable(cat_name),
                # Siempre presente, vacío si la raíz no tiene hijas: quien lo
                # recorra no necesita comprobar si la clave existe.
                "children": {
                    child: {
                        "ceiling": household.get_category_planned_amount(child),
                        "spent": household.get_category_spent(child),
                        "remaining": household.get_category_remaining(child),
                    }
                    for child in household.get_children(cat_name)
                },
            }

        by_member = {
            member: SummaryService.get_member_status(
                household=household, member_name=member
            )
            for member in members
        }

        return {
            "totals": totals,
            "by_category": by_category,
            "by_member": by_member,
            "missing_money": {
                "total": missing_money,
                "by_member": missing_money_by_member,
            },
        }

    @staticmethod
    def get_settlement_summary(household: Household) -> list[dict]:
        """
        Retorna resumen de liquidación de deudas entre miembros del hogar.
        Devuelve lista de transferencias mínimas para saldar deudas.
        Ejemplo:
            [
                {"from": "heri", "to": "amanda", "amount": 50000},
                {"from": "amanda", "to": "jose", "amount": 20000}
            ]
        """
        settlement_transfers: list[dict] = SettlementCalculator.calculate(
            household=household
        )
        return settlement_transfers

    @staticmethod
    def get_all_debts_summary(household: Household, period: Period) -> dict:
        """Retorna el resumen de deuda de todos los miembros del hogar."""
        start_date = period.start_date
        end_date: date | None = period.end_date
        return household.get_all_debts_summary(start_date=start_date, end_date=end_date)

    @staticmethod
    def get_debt_status(household: Household, member_name: str, period: Period) -> dict:
        """Retorna el resumen de deuda de un miembro específico del hogar."""
        member_name = normalize_name(member_name)
        household.validate_member_exist(member_name)
        start_date = period.start_date
        end_date: date | None = period.end_date

        return {
            "debt": household.get_debt_status_by_member(
                member_name=member_name, start_date=start_date, end_date=end_date
            )
        }

    @staticmethod
    def get_saving_status(
        household: Household, member_name: str, period: Period
    ) -> dict:
        """Retorna el resumen de ahorro de un miembro específico del hogar."""
        member_name = normalize_name(member_name)
        household.validate_member_exist(member_name)
        start_date = period.start_date
        end_date: date | None = period.end_date

        return {
            "saving": household.get_saving_status_by_member(
                member_name=member_name, start_date=start_date, end_date=end_date
            )
        }

    @staticmethod
    def get_all_savings_summary(household: Household, period: Period) -> dict:
        """Retorna el resumen de ahorro de todos los miembros del hogar."""
        start_date = period.start_date
        end_date: date | None = period.end_date
        return household.get_all_savings_summary(
            start_date=start_date, end_date=end_date
        )
