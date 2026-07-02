from src.models.household import Household
from src.utils.text import normalize_name


class SummaryService:
    @staticmethod
    def get_registration_summary(household: Household):
        """Resumen de fase REGISTRATION: miembros e ingresos"""
        household.validate_has_members()
        household.validate_total_incomes_positive()
        member_incomes = {
            name: m.monthly_income for name, m in household.members.items()
        }
        total_incomes = household.get_total_incomes()
        return {
            "members": list(household.members.keys()),
            "member_incomes": member_incomes,
            "total_household_income": total_incomes,
        }

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
        debts = household.get_member_debts()
        saving_goals = household.get_saving_goals()
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
        paid = household.expense_tracker.get_total_spent_by_member(member_name)
        balance = household.get_member_balance(member_name)

        # Acordado vs pagado
        agreed_contributions = household.get_agreed_contributions()
        by_category = {}

        for cat_name, cat_data in agreed_contributions.items():
            contribution = cat_data["contributions"][member_name]
            paid_in_category = (
                household.expense_tracker.get_total_spent_by_member_and_category(
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
            "debt": household._member_debts.get(member_name, 0),
            "saving_goal": household._saving_goals.get(member_name, 0),
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
                "total": 100000,   # parte de reserva sin asignar a categoría/ahorro/deuda
                "by_member": {
                    "amanda": 60000,
                    "heri":   40000
                }
            }
        }
        """

        categories = household.get_active_categories()
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
        total = {
            "total_budgeted": total_budgeted,
            "total_spent": total_spent,
            "total_remaining": total_remaining,
        }

        # Categoría {Presupuestado + Gastado + faltante por pagar} + {missing_money}
        by_category = {}
        for cat in categories:
            by_category[cat] = {
                "budget": household.budget.get_category_budget(cat),
                "spent": household.get_category_spent(cat),
                "remaining": household.get_category_remaining(cat),
            }
        by_member = {
            member: SummaryService.get_member_status(
                household=household, member_name=member
            )
            for member in members
        }

        return {
            "totals": total,
            "by_category": by_category,
            "by_member": by_member,
            "missing_money": {
                "total": missing_money,
                "by_member": missing_money_by_member,
            },
        }
