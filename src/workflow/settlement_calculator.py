from dataclasses import dataclass

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
        Entra todo gasto que no sea personal, incluido el que paga uno y
        consume otro.

        Returns:
            list[dict]: [{"from": "heri", "to": "amanda", "amount": 50000}]
            Lista vacía si no hay gastos compartidos o todo está saldado.
        """

        balances = {m: 0 for m in household.members}

        for expense in household.expense_tracker.expenses:
            # Un gasto no entra en el settlement cuando es personal (pagado y consumido por el mismo miembro)
            if expense.is_personal:
                continue

            # El gasto ya trae sus pesos: uno por participante y sumando 10000.
            # Cómo se decidieron —a partes iguales, por ingresos o a mano— es
            # asunto del borde. Aquí solo se reparte.
            should_pay = FinanceCalculator.calculate_contribution_from_custom_splits(
                expense.weights, expense.amount
            )

            # ====== balances ======
            # balance positivo → acreedor (pagó de más)
            # balance negativo → deudor (pagó de menos)
            for m, owed in should_pay.items():
                balances[m] -= owed
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
