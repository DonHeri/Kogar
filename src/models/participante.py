class Participante:
    """Representa a una persona que aporta dinero al hogar."""

    def __init__(self, name: str, monthly_income: float): # TODO Participante debe saber; monthly_incomes? o solo nombre
                                                          # NOTE en el futuro extraer ingresos mensuales y que Participante solo se encargue de los datos del miembro 

        if not name or not name.strip():
            raise ValueError("Nombre no puede estar vacío")

        # Si no lo es, hacer: raise ValueError("El ingreso debe ser positivo")
        if monthly_income <= 0:
            raise ValueError("Ingresos deben ser superiores a 0")

        self.name = name
        self.monthly_income = monthly_income

    def calculate_contribution_percentage(self, total_incomes: float) -> float:
        """Calcula qué % de los ingresos totales representa esta persona."""

        if total_incomes <= 0:
            raise ValueError("El total de ingresos debe ser mayor a 0")

        return (self.monthly_income / total_incomes) * 100


if __name__ == "__main__":
    user_1 = Participante("Heri", 1200)
    user_2 = Participante("Amanda", 1400)
    total_incomes = user_1.monthly_income + user_2.monthly_income

    print(f"{user_1.calculate_contribution_percentage(total_incomes):.2f} %")
    print(f"{user_2.calculate_contribution_percentage(total_incomes):.2f} %")
