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
