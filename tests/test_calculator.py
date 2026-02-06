import pytest
from src.models.calculadora import Calculator
from src.models.participante import Participante

@pytest.fixture
def base_member_1():
    return Participante("Default")

@pytest.fixture
def base_member_2():
    return Participante("Default")

@pytest.fixture
def base_calculator():
    return Calculator()

def test_household_total_incomes_is_correct(base_member_1, base_member_2,base_calculator):
    """ Verifica cálculos del total de ingresos"""
    # Arrange
    expected_total = 2800.0
    base_member_1.monthly_income = 1500
    base_member_2.monthly_income = 1300
    
    # Act
    total = base_calculator.sum_total_incomes([base_member_1,base_member_2])

    # assert
    assert expected_total == total
 
    
def test_member_proportional_share_calculation(base_member_1,base_member_2):
    """ Verifica aporte proporcional en base al salario """
    
    #FIXME Terminar
    
    # Arrange
    expected_percentage_member_1 = 1500/2800
    expected_percentage_member_2 = 1300/2800
    calculator = Calculator()
    
    # Act
  
    
    pass
    