class FinanceCalculator:
    @staticmethod
    def sum_values(values: list[int]) -> int:
        """Suma una lista de valores numéricos de forma genérica."""
        return sum(values)

    @staticmethod
    def calculate_percentage_based_on_weight_of_income(
        income_map: dict[str, int],
    ) -> dict[str, int]:
        """
        Devuelve porcentajes × 100 (5357 = 53.57%)
        Garantiza suma exacta = 10000
        """

        total = sum(income_map.values())

        if total <= 0:
            raise ValueError("Total de ingresos debe ser superior a 0")

        percentages = {}
        assigned = 0

        # Calcular todos con división entera
        for name, income in income_map.items():
            pct = (
                income * 10000
            ) // total  # income / total = 0.5357 -> 0.5357 * 10000 = 5357
            percentages[name] = pct
            assigned += pct

        # Diferencia al de mayor ingreso
        max_member = max(income_map, key=lambda k: income_map[k])
        percentages[max_member] += 10000 - assigned

        return percentages

    @staticmethod
    def calculate_equal_percentage(members: dict[str, int]) -> dict[str, int]:
        """
        Devuelve porcentajes equitativos para cada miembro (x100) -> 5000/5000 = 50%/50%
        Si existe descuadre, se aporta al de mayor ingreso

        Parámetros:
        members: Diccionario que contiene nombre de miembros y sus ingresos
        """
        num_members = len(members)
        base_pct = 10000 // num_members

        percentages = {name: base_pct for name in members}
        assigned = base_pct * num_members

        max_member = max(members, key=lambda k: members[k])
        percentages[max_member] += 10000 - assigned
        return percentages

    @staticmethod
    def calculate_contribution(
        percentages: dict[str, int], budget_amount: int
    ) -> dict[str, int]:
        """
        Aplica porcentaje que debe aportar cada miembro: percentages: dict[name_member,percentage]
        A un presupuesto: budget_amount
        """
        contributions = {}
        total_assigned = 0

        for member_name, percentage in percentages.items():
            member_contribution = (
                budget_amount * percentage // 10000
            )  # División entera para evitar float

            total_assigned += member_contribution
            contributions[member_name] = member_contribution

        # Diferencia siempre positiva por división entera
        diferencia = budget_amount - total_assigned

        # Diferencia al de mayor aporte
        if total_assigned != 0:
            max_member = max(percentages, key=lambda k: percentages[k])
            contributions[max_member] += diferencia

        # Para lanzar algún error si no cuadra
        if sum(contributions.values()) != budget_amount:  # TODO validador temporal
            raise ValueError(
                "El total asignado en contribution es diferente al monto presupuestado"
            )

        return contributions
