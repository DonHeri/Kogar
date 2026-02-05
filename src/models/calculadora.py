
class Calculator:

    def sum_total_incomes(self, members: list) -> float:
        """Calcula el total de ingresos entre los miembros"""
        return sum(member.monthly_income for member in members)

    #TODO calcular porcentajes según salario
    """ 
    Mi idea es que la calculadora solo saque los porcentajes
    Household coordina, aplica los porcentajes al total; y avisa a cada miembro su aporte.
    Luego pregunta quien se lleva el redondeo
    """