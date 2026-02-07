class Participante:
    """Representa a una persona con su ingreso base mensual."""

    def __init__(self, name: str):

        if not name or not name.strip():
            raise ValueError("Nombre no puede estar vacío")

        # ====== Atributos ======
        self.name: str = name
        self.monthly_income: float = 0.0  # TODO: Convertir monthly_income a lista cuando necesite histórico

    # Suma ingresos
    def add_incomes(self, income: float) -> None:
        if income < 0:  
            raise ValueError("Ingreso no puede ser negativo")
        self.monthly_income += income



# ====================================================
# Zona de pruebas
# ====================================================
if __name__ == "__main__":

