import pytest
from src.models.participante import Participante
from src.models.household import Household
from src.models.calculadora import Calculator


@pytest.fixture
def base_member_1():
    return Participante("Default")


@pytest.fixture
def base_member_2():
    return Participante("Default")


@pytest.fixture
def base_household():
    calculator = Calculator()
    return Household(calculator)


def test_create_valid_household(base_household):
    """Verifica correcta creación de instancia Household"""

    # Assert
    assert isinstance(base_household.members, dict)
    assert isinstance(base_household.calculator, Calculator)


def test_register_member_adds_members_to_household(base_member_1, base_household):
    """Verifica que se ingresen las instancias de los participantes en la lista de miembros"""

    base_household.register_member(base_member_1)

    assert base_member_1.name in base_household.members


def test_setter_incomes_is_correct(base_household, base_member_1):
    """Se cambian los ingresos correctamente"""
    # Arrange
    expected = 500.0
    base_household.members[base_member_1.name] = base_member_1

    # Act
    base_household.set_members_incomes(base_member_1.name, 500.0)

    # Assert
    assert base_member_1.monthly_income == expected


def test_household_total_incomes_is_correct(
    base_member_1, base_member_2, base_household
):
    """Verifica cálculos del total de ingresos"""
    # Arrange
    expected_total = 2800.0
    base_member_1.monthly_income = 1500
    base_member_2.monthly_income = 1300
    base_household.members = [base_member_1, base_member_2]

    # Act
    total = base_household.calculate_total_incomes()

    # assert
    assert expected_total == total
