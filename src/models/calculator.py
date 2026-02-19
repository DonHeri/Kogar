


class Calculator:

    @staticmethod
    def sum_values(values: list[int]) -> int:
        """Suma una lista de valores numéricos de forma genérica."""
        return sum(values)

    # En Calculator
    @staticmethod
    def calculate_member_percentage(income_map: dict[str, int]) -> dict[str, int]:
        """
        Recibe ingresos y el total ya calculado
        Devuelve porcentajes × 100 (6667 = 66.67%)
        """
        total = sum(income_map.values())

        if total <= 0:
            raise ValueError("Total de ingresos debe ser superior a 0")

        return {
            name: round((income * 10000) / total) for name, income in income_map.items()
        }

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
        if sum(contributions.values()) != budget_amount: #TODO validador temporal 
            raise ValueError(
                "El total asignado en contribution es diferente al monto presupuestado"
            )

        return contributions
