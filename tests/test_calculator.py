import pytest
from src.models.calculadora import Calculator
from src.models.participante import Participante


# ====================================================
# FIXTURES
# ====================================================

@pytest.fixture
def members_with_incomes():
    """Dos miembros con ingresos diferentes"""
    m1 = Participante("Member1")
    m2 = Participante("Member2")
    m1.monthly_income = 2000.0
    m2.monthly_income = 1000.0
    return {m1.name: m1, m2.name: m2}


@pytest.fixture
def member_zero_income():
    """Miembro sin ingresos"""
    return Participante("NoIncome")


# ====================================================
# TESTS: sum_total_incomes
# ====================================================

def test_sum_total_incomes(members_with_incomes):
    """Suma correcta de ingresos"""
    total = Calculator.sum_total_incomes(members_with_incomes)
    assert total == 3000.0


def test_sum_empty_dict_returns_zero():
    """Diccionario vacío devuelve 0"""
    assert Calculator.sum_total_incomes({}) == 0.0


# ====================================================
# TESTS: calculate_member_percentage
# ====================================================

def test_calculate_percentage(members_with_incomes):
    """Porcentajes correctos según ingresos"""
    percentages = Calculator.calculate_member_percentage(members_with_incomes)
    
    assert percentages["Member1"] == pytest.approx(66.67, rel=1e-2)
    assert percentages["Member2"] == pytest.approx(33.33, rel=1e-2)


def test_percentage_raises_on_zero_total(member_zero_income):
    """Error cuando total de ingresos es 0"""
    members = {member_zero_income.name: member_zero_income}
    
    with pytest.raises(ValueError, match="Total de ingresos debe ser > 0"):
        Calculator.calculate_member_percentage(members)