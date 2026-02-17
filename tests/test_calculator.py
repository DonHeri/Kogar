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
