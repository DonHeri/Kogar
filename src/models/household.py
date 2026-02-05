from src.models.participante import Participante
from src.models.calculadora import Calculator


class Household:

    def __init__(self) -> None:
        # TODO  luego ira un .cargar() que devolverá un dict si no hay datos
        self.members = []
        self.calculator = Calculator()

    def test_register_member(self):
        """Datos de usuarios para probar el software"""
        # Datos de TEST
        self.members.append(Participante("Amanda", 1400))
        self.members.append(Participante("Heri", 1300))

    def register_member(self, member):
        """Crear instancias de miembros de la unidad e incorporar en dict de miembros"""
        self.members.append(member)

    def calculate_total_incomes(self):
        """Calcula el total de ingresos entre los miembros"""
        
        # TODO agregar manejo de error por si suma <= 0 - en `participante.py` gestiono que ingresos no sean < 0
        return self.calculator.sum_total_incomes(self.members) 
        
    def calcultate_proportion_member(self):
        pass
    
    
    
if __name__ == "__main__":
    unidad = Household()
    unidad.test_register_member()

    unidad.calculate_total_incomes()
