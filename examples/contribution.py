@staticmethod
def calculate_percentage_based_on_weight_of_income(
    income_map: dict[str, int],
):
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
    # Calcular todos con división entera
    for name, income in income_map.items():
        exact = income * 10000 / total
        floored = int(exact)
        percentages[name] = floored
        remainders[name] = exact - floored
        assigned += floored

    diferencia = 10000 - assigned

    # La diferencia se asigna a quien más perdió al truncar
    for name in sorted(remainders, key=lambda k: remainders[k], reverse=True)[
        :diferencia
    ]:
        percentages[name] += 1

    return percentages


@staticmethod
def calculate_equal_percentage(members: dict[str, int]) -> dict[str, int]:
    """
    Calcula porcentajes equitativos (50/50, 33/33/33, etc.)
    Retorna porcentajes × 100
    Si existe descuadre de céntimos, se aporta al miembro con mayor ingreso
    """
    num_members = len(members)
    base_exact = 10000 / num_members
    print(num_members)
    print("base_exact", base_exact)
    print("-" * 40)
    percentages = {}
    remainders = {}
    assigned = 0

    for name, income in members.items():
        floored = int(base_exact)
        percentages[name] = floored
        remainders[name] = base_exact - floored
        assigned += floored
        print(floored)
        print(percentages)
        print(remainders)
        print(assigned)
        print("-" * 40)
    diferencia = 10000 - assigned

    # La diferencia se asigna a quien más perdió al truncar
    for name in sorted(remainders, key=lambda k: remainders[k], reverse=True)[
        :diferencia
    ]:
        percentages[name] += 1

    return percentages
    # max_member = max(members, key=lambda k: members[k])
    # percentages[max_member] += 10000 - assigned
    # return percentages


income_map = {"A": 149933, "B": 133333, "C": 145300}

print(calculate_equal_percentage(income_map))
