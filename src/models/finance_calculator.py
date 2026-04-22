class FinanceCalculator:
    """Realiza cálculos financieros sin estado (métodos estáticos)"""

    # ====== AGGREGATION ======
    @staticmethod
    def sum_values(values: list[int]) -> int:
        """Suma una lista de valores numéricos"""
        return sum(values)

    # ====== PERCENTAGE CALCULATIONS (solo para display) ======
    @staticmethod
    def calculate_percentage_based_on_weight_of_income(
        income_map: dict[str, int],
    ) -> dict[str, int]:
        """
        Calcula porcentajes proporcionales al ingreso de cada miembro.
        Solo para display — los cálculos reales de contribución usan calculate_contribution_from_incomes.

        Retorna porcentajes × 100 (5357 = 53.57%)
        Garantiza suma exacta = 10000 usando largest remainder method.
        """
        total = sum(income_map.values())

        if total <= 0:
            raise ValueError("Total de ingresos debe ser superior a 0")

        percentages = {}
        remainders = {}
        assigned = 0

        for name, income in income_map.items():
            exact = income * 10000 / total
            floored = int(exact)
            percentages[name] = floored
            remainders[name] = exact - floored
            assigned += floored

        diferencia = 10000 - assigned
        for name in sorted(remainders, key=lambda k: remainders[k], reverse=True)[
            :diferencia
        ]:
            percentages[name] += 1

        return percentages

    @staticmethod
    def calculate_equal_percentage(members: dict[str, int]) -> dict[str, int]:
        """
        Calcula porcentajes equitativos (50/50, 33/33/33, etc.)
        Solo para display — los cálculos reales usan calculate_contribution_from_incomes.

        Retorna porcentajes × 100
        Garantiza suma exacta = 10000 usando largest remainder method.
        """
        num_members = len(members)
        base_exact = 10000 / num_members

        percentages = {}
        remainders = {}
        assigned = 0

        for name in members:
            floored = int(base_exact)
            percentages[name] = floored
            remainders[name] = base_exact - floored
            assigned += floored

        diferencia = 10000 - assigned
        for name in sorted(remainders, key=lambda k: remainders[k], reverse=True)[
            :diferencia
        ]:
            percentages[name] += 1

        return percentages

    @staticmethod
    def calculate_budget_from_percentages(
        total_incomes, percentages: dict[str, int]
    ) -> dict[str, int]:
        """
        Calcula presupuestos según porcentajes.
        Elimina acumulación de errores de redondeo entre porcentajes

        Returns:
            {
                "fijos": 100000,  # céntimos
                "variables": 50000,   # céntimos
                "reserva": 40000
            }
        """
        total_percentages = sum(percentages.values())

        if total_incomes <= 0:
            raise ValueError("Total de ingresos debe ser superior a 0")

        if total_percentages != 10000:
            raise ValueError("Los porcentajes deben sumar 100% (10000 basis points)")

        budgets = {}
        remainders = {}
        assigned = 0

        for category, pct in percentages.items():
            exact = total_incomes * pct / 10000
            floored = int(exact)
            remainders[category] = exact - floored
            budgets[category] = floored
            assigned += floored

        # Repartir restantes en el truncamiento
        diferencia = total_incomes - assigned

        for category in sorted(remainders, key=lambda k: remainders[k], reverse=True)[
            :diferencia
        ]:
            budgets[category] += 1

        if sum(budgets.values()) != total_incomes:
            raise ValueError(
                "El total asignado a presupuestos es distinto del total de ingresos"
            )

        return budgets

    # ====== CONTRIBUTION CALCULATIONS ======
    @staticmethod
    def calculate_contribution_from_incomes(
        income_map: dict[str, int], budget_amount: int
    ) -> dict[str, int]:
        """
        Calcula contribuciones directamente desde ingresos, sin porcentajes intermedios.
        Elimina acumulación de errores de redondeo entre categorías.

        Garantiza:
        - Suma exacta del presupuesto (sin pérdida de céntimos)
        - Ningún miembro excede su ingreso proporcional
        - Error máximo: 1 céntimo por categoría, no acumulable

        Returns:
            {
                "member_a": 100000,  # céntimos
                "member_b": 50000,   # céntimos
            }
        """
        total_income = sum(income_map.values())

        if total_income <= 0:
            raise ValueError("Total de ingresos debe ser superior a 0")

        contributions = {}
        remainders = {}
        assigned = 0

        for member, income in income_map.items():
            exact = budget_amount * income / total_income
            floored = int(exact)
            contributions[member] = floored
            remainders[member] = exact - floored
            assigned += floored

        # Distribuir céntimos sobrantes al que más perdió por truncamiento
        diferencia = budget_amount - assigned
        for member in sorted(remainders, key=lambda k: remainders[k], reverse=True)[
            :diferencia
        ]:
            contributions[member] += 1

        if sum(contributions.values()) != budget_amount:
            raise ValueError(
                "El total asignado en contribution es diferente al monto presupuestado"
            )

        return contributions

    @staticmethod
    def calculate_contribution_from_custom_splits(
        custom_splits: dict[str, int], budget_amount: int
    ) -> dict[str, int]:
        """
        Calcula contribuciones desde porcentajes custom (basis points × 100).
        Usado solo para MetodoReparto.CUSTOM donde el usuario define porcentajes explícitos.

        Garantiza suma exacta del presupuesto usando largest remainder method.

        Returns:
            {
                "member_a": 65000,  # céntimos
                "member_b": 35000,  # céntimos
            }
        """
        contributions = {}
        remainders = {}
        assigned = 0

        for member, pct in custom_splits.items():
            exact = budget_amount * pct / 10000
            floored = int(exact)
            contributions[member] = floored
            remainders[member] = exact - floored
            assigned += floored

        diferencia = budget_amount - assigned
        for member in sorted(remainders, key=lambda k: remainders[k], reverse=True)[
            :diferencia
        ]:
            contributions[member] += 1

        if sum(contributions.values()) != budget_amount:
            raise ValueError(
                "El total asignado en contribution es diferente al monto presupuestado"
            )

        return contributions
