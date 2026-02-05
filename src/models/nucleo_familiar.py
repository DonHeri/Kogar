from participante import Participante


class Household:
    # Cantidad de miembros de la unidad familiar
    num_members = 0

    def __init__(self) -> None:
        self.members = (
            {}
        )  # TODO  luego ira un .cargar() que devolverá un dict si no hay datos

    def request_total_members(self):
        """
        Solicita y valida la cantidad de miembros del núcleo familiar.
        """
        # Usamos un nombre descriptivo en lugar de '_'
        try:
            count = 2
            # count = int(input("Introduce el número de miembros: "))
        except ValueError:
            # FIXME: Manejar el caso donde el usuario introduce texto en vez de números
            raise ValueError("La entrada debe ser un número entero.")

        if count <= 0:
            raise ValueError("Número de miembros debe ser superior a 0")

        # Asignación al atributo de la clase
        Household.num_members = count  # TODO test

    def register_member(self):
        """Crear instancias de miembros de la unidad e incorporar en dict de miembros"""

        # Datos de TEST
        self.members["Amanda"] = Participante("Amanda", 1400)
        self.members["Heri"] = Participante("Heri", 1300)

    # Para cuando quiera introducir los datos manual
    """  
     while i != Household.num_members: # TODO extraer a una función aparte
        name = input(f"Introduce nombre del miembro {i+1}: ")
        monthly_income = int(input("Introduce salario: "))
        self.members[name] = Participante(name, monthly_income)
        # Aumentar num participantes
        i += 1 
    """



if __name__ == "__main__":
    unidad = Household()
    unidad.request_total_members()
    unidad.register_member()

    print(unidad.members["Amanda"].__dict__)
    print(unidad.members["Heri"].__dict__)
