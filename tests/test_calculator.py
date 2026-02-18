import pytest
from src.models.calculator import Calculator



# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def incomes_map():
    """Dos miembros con ingresos diferentes"""
    m1 = "Member1"
    m2 = "Member2"
    income_m1 = 200000
    income_m2 = 100000
    return {m1: income_m1, m2: income_m2}


@pytest.fixture
def member_zero_income():
    """Miembro sin ingresos"""
    return {"no_incomes": 0}


@pytest.fixture
def incomes_list():
    """Una lista de ingresos:int en céntimos"""
    return [200000, 100000]


# ====================================================
# TESTS: sum_total_incomes
# ====================================================


def test_sum_total_incomes(incomes_list: list[int]):
    """Suma correcta de ingresos"""
    total = Calculator.sum_values(incomes_list)
    assert total == 300000


def test_sum_empty_dict_returns_zero():
    """Diccionario vacío devuelve 0"""
    assert Calculator.sum_values([]) == 0


# ====================================================
# TESTS: calculate_member_percentage
# ====================================================


def test_calculate_percentage(incomes_map):
    """Porcentajes correctos según ingresos"""
    percentages = Calculator.calculate_member_percentage(incomes_map)

    assert percentages["Member1"] == pytest.approx(6667, rel=1e-2)
    assert percentages["Member2"] == pytest.approx(3333, rel=1e-2)


def test_percentage_raises_on_zero_total(member_zero_income):
    """Error cuando total de ingresos es 0"""
    with pytest.raises(ValueError, match="Total de ingresos debe ser superior a 0"):
        Calculator.calculate_member_percentage(member_zero_income)


# ====================================================
# TESTS: calculate_contribution
# ====================================================

@pytest.fixture
def percentages_66_33():
    """Porcentajes 66.67% - 33.33% (×100)"""
    return {"Member1": 6667, "Member2": 3333}


@pytest.fixture
def percentages_50_50():
    """Porcentajes 50% - 50% (×100)"""
    return {"Member1": 5000, "Member2": 5000}


def test_calculate_contribution_basic_67_33(percentages_66_33):
    """Calcula contribuciones correctamente 66/33 split"""
    budget = 90000  # 900€
    contributions = Calculator.calculate_contribution(percentages_66_33, budget)

    assert contributions["Member1"] == 60003  # ~600€
    assert contributions["Member2"] == 29997  # ~300€
    assert sum(contributions.values()) == budget


def test_calculate_contribution_equal_split(percentages_50_50):
    """Calcula contribuciones correctamente 50/50 split"""
    budget = 100000  # 1000€
    contributions = Calculator.calculate_contribution(percentages_50_50, budget)

    assert contributions["Member1"] == 50000
    assert contributions["Member2"] == 50000
    assert sum(contributions.values()) == budget


def test_calculate_contribution_small_budget(percentages_66_33):
    """Maneja presupuestos pequeños con redondeo"""
    budget = 100  # 1€
    contributions = Calculator.calculate_contribution(percentages_66_33, budget)

    # 100 * 6667 // 10000 = 66
    # 100 * 3333 // 10000 = 33
    # Diferencia = 100 - 99 = 1 → se asigna a Member1
    assert contributions["Member1"] == 67
    assert contributions["Member2"] == 33
    assert sum(contributions.values()) == budget


def test_calculate_contribution_zero_budget():
    """Maneja presupuesto cero"""
    percentages = {"Member1": 5000, "Member2": 5000}
    contributions = Calculator.calculate_contribution(percentages, 0)

    assert contributions["Member1"] == 0
    assert contributions["Member2"] == 0
    assert sum(contributions.values()) == 0


def test_calculate_contribution_assigns_remainder_to_max(percentages_66_33):
    """Asigna céntimo sobrante al miembro con mayor aporte"""
    budget = 100  # Presupuesto que genera sobrante
    contributions = Calculator.calculate_contribution(percentages_66_33, budget)

    # El céntimo sobrante va a Member1 (66% > 33%)
    assert contributions["Member1"] > (budget * 6667 // 10000)
    assert sum(contributions.values()) == budget


def test_calculate_contribution_with_three_members():
    """Calcula correctamente con 3 miembros"""
    percentages = {"A": 5000, "B": 3000, "C": 2000}  # 50%, 30%, 20%
    budget = 100000  # 1000€
    contributions = Calculator.calculate_contribution(percentages, budget)

    # A: 1000 * 0.50 = 500€ = 50000
    # B: 1000 * 0.30 = 300€ = 30000
    # C: 1000 * 0.20 = 200€ = 20000
    assert contributions["A"] == 50000
    assert contributions["B"] == 30000
    assert contributions["C"] == 20000
    assert sum(contributions.values()) == budget


def test_calculate_contribution_totals_match_budget(incomes_map):
    """Total de contribuciones siempre = budget"""
    percentages = Calculator.calculate_member_percentage(incomes_map)
    budgets = [90000, 300000, 500000, 1000000]

    for budget in budgets:
        contributions = Calculator.calculate_contribution(percentages, budget)
        assert sum(contributions.values()) == budget