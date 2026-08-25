from dataclasses import dataclass

from src.models.constants import MetodoReparto
from src.models.finance_calculator import FinanceCalculator
from src.models.household import Household


@dataclass
class Transfer:  # TODO integrar en el settlement
    from_member_id: int
    to_member_id: int
    amount: int


class SettlementCalculator:
    @staticmethod
    def calculate(household: Household) -> list[dict]:
        """
        Calcula las transferencias mínimas para saldar deudas entre miembros.
        Solo opera sobre gastos con participants > 1.

        Returns:
            list[dict]: [{"from": "heri", "to": "amanda", "amount": 50000}]
            Lista vacía si no hay gastos compartidos o todo está saldado.
        """

        balances = {m: 0 for m in household.members}

        for expense in household.expense_tracker.expenses:
            if not expense.is_shared:
                continue

            participants = expense.participants

            if household.get_registered_incomes():
                incomes_map = {
                    m: household.get_registered_incomes()[m] for m in participants
                }
            else:
                # Usar datos mutables solo en REGISTRATION
                incomes_map = {
                    name: household.members[name].monthly_income
                    for name in participants
                }

            # Cuánto debería pagar cada miembro según el método de reparto
            if household.method == MetodoReparto.CUSTOM:
                should_pay = (
                    FinanceCalculator.calculate_contribution_from_custom_splits(
                        household.get_custom_splits(), expense.amount
                    )
                )
            elif household.method == MetodoReparto.EQUAL:
                equal_map = {name: 1 for name in incomes_map}
                should_pay = FinanceCalculator.calculate_contribution_from_incomes(
                    equal_map, expense.amount
                )
            else:
                should_pay = FinanceCalculator.calculate_contribution_from_incomes(
                    incomes_map, expense.amount
                )

            # ====== balances ======
            # balance positivo → acreedor (pagó de más)
            # balance negativo → deudor (pagó de menos)
            for m in participants:
                balances[m] -= should_pay.get(m, 0)
            balances[expense.member] += expense.amount

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
            transfers.append(
                {"from": debtor_name, "to": creditor_name, "amount": amount}
            )

            debt -= amount
            credit -= amount

            debtors[i] = (debtor_name, debt)
            creditors[j] = (creditor_name, credit)

            if debt == 0:
                i += 1
            if credit == 0:
                j += 1

        return transfers
