from src.models.household import Household
from src.models.calculadora import Calculator

# Formatos
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"

# Colores
GREEN = "\033[32m"
CYAN = "\033[36m"
RED = "\033[31m"


def print_titulo(texto):
    ancho = len(texto) + 4
    print(f"\n{BOLD}{CYAN}" + "=" * ancho)
    print(f"| {texto.upper()} |")
    print("=" * ancho + f"{RESET}\n")


def print_option_row(label, valor):
    print(f"{BOLD}{CYAN}{label} - {RESET} {GREEN}{valor}{RESET}")


def menu():
    while True:
        print_option_row("[0]", "SALIR")
        print_option_row("[1]", "PRIMEROS PASOS")
        print_option_row("[2]", "NUEVO MES")
        print_option_row("[3]", "TABLA RESUMEN")
        print_option_row("[4]", "CERRAR MES")

        break


if __name__ == "__main__":
    # Uso real:
    # print_fila("Status", "Online")
    # print_fila("Database", "Connected")

    print_titulo("CLI Finanzas Pro")

    menu()

    # Crear instancias

    household = Household()

    # Registrar miembros
    """ 
    Aquí irá un while True: print("Presentación nombres [0]-Salir") -> Saber cantidad de miembros del household
    """
    household.test_register_member()

    # Introducir salarios
    # Se preguntaran ingresos total al principio de mes, luego ingresos extras sir surge
    household.test_incomes()

    total_incomes = household.total_incomes()
    print(total_incomes)

    print(household.obtain_percentages())  # FIXME Calcula y settea || TEMPORAL
    print(household.obtain_contribution_member())
