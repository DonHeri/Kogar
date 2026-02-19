import pytest
from src.models.finance_calculator import FinanceCalculator


# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def incomes_map():
    """Dos miembros con ingresos diferentes"""
    return {"Member1": 200000, "Member2": 100000}
    return {"Member1": 200000, "Member2": 100000}


@pytest.fixture
def member_zero_income():
    """Miembro sin ingresos"""
    return {"no_incomes": 0}


@pytest.fixture
def incomes_list():
    """Una lista de ingresos en céntimos"""
    """Una lista de ingresos en céntimos"""
    return [200000, 100000]


@pytest.fixture
def percentages_66_33():
    """Porcentajes 66.67% - 33.33% (×100)"""
    return {"Member1": 6667, "Member2": 3333}


@pytest.fixture
def percentages_50_50():
    """Porcentajes 50% - 50% (×100)"""
    return {"Member1": 5000, "Member2": 5000}


# ====================================================
# TESTS: sum_values
# ====================================================


def test_sum_total_incomes(incomes_list):
    """Suma correcta de ingresos"""
    assert FinanceCalculator.sum_values(incomes_list) == 300000


def test_sum_empty_list_returns_zero():
    """Lista vacía devuelve 0"""
    assert FinanceCalculator.sum_values([]) == 0


# ====================================================
# TESTS: calculate_percentage_based_on_weight_of_income
# ====================================================


def test_calculate_percentage_proportional_values(incomes_map):
    """Porcentajes correctos según peso de ingresos (200k/100k → 6667/3333)"""
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        incomes_map
    )

    assert percentages["Member1"] == 6667
    assert percentages["Member2"] == 3333


def test_calculate_percentage_proportional_sums_to_10000(incomes_map):
    """Suma exacta = 10000 garantizada por corrección de redondeo"""
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        incomes_map
    )

    assert sum(percentages.values()) == 10000


def test_calculate_percentage_proportional_remainder_goes_to_max(incomes_map):
    """El ajuste de redondeo se asigna al miembro con mayor ingreso"""
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        incomes_map
    )

    # Member1 tiene mayor ingreso, debe recibir el ajuste
    # Sin ajuste: 200000*10000//300000 = 6666, con ajuste = 6667
    assert percentages["Member1"] >= 6666


def test_calculate_percentage_proportional_raises_on_zero_total(member_zero_income):
    """Error cuando total de ingresos es 0"""
    with pytest.raises(ValueError, match="Total de ingresos debe ser superior a 0"):
        FinanceCalculator.calculate_percentage_based_on_weight_of_income(
            member_zero_income
        )


def test_calculate_percentage_proportional_raises_on_all_zeros():
    """Error cuando todos los miembros tienen ingreso 0"""
    with pytest.raises(ValueError, match="Total de ingresos debe ser superior a 0"):
        FinanceCalculator.calculate_percentage_based_on_weight_of_income(
            {"Member1": 0, "Member2": 0}
        )


def test_calculate_percentage_proportional_equal_incomes():
    """Ingresos iguales producen porcentajes iguales (50/50)"""
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        {"Member1": 100000, "Member2": 100000}
    )

    assert percentages["Member1"] == 5000
    assert percentages["Member2"] == 5000
    assert sum(percentages.values()) == 10000


def test_calculate_percentage_proportional_three_members():
    """Porcentajes correctos con tres miembros"""
    income_map = {"A": 500000, "B": 300000, "C": 200000}
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        income_map
    )

    assert percentages["A"] == 5000
    assert percentages["B"] == 3000
    assert percentages["C"] == 2000
    assert sum(percentages.values()) == 10000


# ====================================================
# TESTS: calculate_equal_percentage
# ====================================================


def test_calculate_equal_percentage_two_members():
    """Dos miembros reciben 50/50"""
    members = {"Member1": 200000, "Member2": 100000}
    percentages = FinanceCalculator.calculate_equal_percentage(members)

    assert percentages["Member1"] == 5000
    assert percentages["Member2"] == 5000


def test_calculate_equal_percentage_sums_to_10000_two_members():
    """Suma = 10000 con dos miembros"""
    percentages = FinanceCalculator.calculate_equal_percentage(
        {"Member1": 200000, "Member2": 100000}
    )

    assert sum(percentages.values()) == 10000


def test_calculate_equal_percentage_three_members():
    """Tres miembros: base 3333 cada uno, ajuste al de mayor ingreso"""
    members = {"A": 300000, "B": 200000, "C": 100000}
    percentages = FinanceCalculator.calculate_equal_percentage(members)

    # 10000 // 3 = 3333, assigned = 9999, diferencia = 1 → va a A (mayor ingreso)
    assert percentages["A"] == 3334
    assert percentages["B"] == 3333
    assert percentages["C"] == 3333
    assert sum(percentages.values()) == 10000


def test_calculate_equal_percentage_sums_to_10000_three_members():
    """Suma = 10000 con tres miembros (verifica corrección de redondeo)"""
    percentages = FinanceCalculator.calculate_equal_percentage(
        {"A": 300000, "B": 200000, "C": 100000}
    )

    assert sum(percentages.values()) == 10000


def test_calculate_equal_percentage_remainder_goes_to_max_income():
    """El ajuste de redondeo va al miembro con mayor ingreso, no al primero"""
    # C tiene mayor ingreso
    members = {"A": 100000, "B": 200000, "C": 300000}
    percentages = FinanceCalculator.calculate_equal_percentage(members)

    assert percentages["C"] == 3334
    assert sum(percentages.values()) == 10000


def test_calculate_equal_percentage_ignores_income_for_base_split():
    """La base es igual para todos independientemente del ingreso"""
    members = {"Rich": 1000000, "Poor": 10000}
    percentages = FinanceCalculator.calculate_equal_percentage(members)

    # Ambos deben tener el mismo base antes del ajuste de redondeo
    # Con 2 miembros no hay redondeo: 5000/5000
    assert percentages["Rich"] == 5000
    assert percentages["Poor"] == 5000


# ====================================================
# TESTS: calculate_contribution
# ====================================================


def test_calculate_contribution_basic_67_33(percentages_66_33):
    """Calcula contribuciones correctamente con split 66/33"""
    """Calcula contribuciones correctamente con split 66/33"""
    budget = 90000  # 900€
    contributions = FinanceCalculator.calculate_contribution(percentages_66_33, budget)

    assert contributions["Member1"] == 60003
    assert contributions["Member2"] == 29997
    assert contributions["Member1"] == 60003
    assert contributions["Member2"] == 29997
    assert sum(contributions.values()) == budget


def test_calculate_contribution_equal_split(percentages_50_50):
    """Calcula contribuciones correctamente con split 50/50"""
    """Calcula contribuciones correctamente con split 50/50"""
    budget = 100000  # 1000€
    contributions = FinanceCalculator.calculate_contribution(percentages_50_50, budget)

    assert contributions["Member1"] == 50000
    assert contributions["Member2"] == 50000
    assert sum(contributions.values()) == budget


def test_calculate_contribution_small_budget(percentages_66_33):
    """Maneja presupuestos pequeños con redondeo"""
    budget = 100  # 1€
    contributions = FinanceCalculator.calculate_contribution(percentages_66_33, budget)

    # 100 * 6667 // 10000 = 66
    # 100 * 3333 // 10000 = 33
    # Diferencia = 1 → va a Member1
    assert contributions["Member1"] == 67
    assert contributions["Member2"] == 33
    assert sum(contributions.values()) == budget


def test_calculate_contribution_zero_budget():
    """Maneja presupuesto cero sin errores"""
    contributions = FinanceCalculator.calculate_contribution(
        {"Member1": 5000, "Member2": 5000}, 0
    )

    assert contributions["Member1"] == 0
    assert contributions["Member2"] == 0
    assert sum(contributions.values()) == 0


def test_calculate_contribution_assigns_remainder_to_max(percentages_66_33):
    """El céntimo sobrante va al miembro con mayor porcentaje"""
    budget = 100
    contributions = FinanceCalculator.calculate_contribution(percentages_66_33, budget)

    assert contributions["Member1"] > (budget * 6667 // 10000)
    assert sum(contributions.values()) == budget


def test_calculate_contribution_three_members():
    """Calcula correctamente con 3 miembros sin redondeo"""
    percentages = {"A": 5000, "B": 3000, "C": 2000}
def test_calculate_contribution_three_members():
    """Calcula correctamente con 3 miembros sin redondeo"""
    percentages = {"A": 5000, "B": 3000, "C": 2000}
    budget = 100000  # 1000€
    contributions = FinanceCalculator.calculate_contribution(percentages, budget)

    assert contributions["A"] == 50000
    assert contributions["B"] == 30000
    assert contributions["C"] == 20000
    assert sum(contributions.values()) == budget


def test_calculate_contribution_totals_always_match_budget(incomes_map):
    """Total de contribuciones = budget para múltiples presupuestos"""
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        incomes_map
    )

    for budget in [90000, 300000, 500000, 1000000]:
        contributions = FinanceCalculator.calculate_contribution(percentages, budget)
        assert sum(contributions.values()) == budget
