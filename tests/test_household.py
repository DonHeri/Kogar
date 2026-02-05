import pytest
from src.models.participante import Participante
from src.models.household import Household


@pytest.fixture
def base_member_1():
    return Participante("Default", 1500.0)


@pytest.fixture
def base_member_2():
    return Participante("Default", 1300.0)


def test_register_member_adds_members_to_household(base_member_1):
    """Verifica que se ingresen las instancias de los participantes en la lista de miembros"""
    household = Household()

    household.register_member(base_member_1)

    assert base_member_1 in household.members


def test_household_total_incomes_is_correct(base_member_1, base_member_2):
    """Verifica cálculos del total de ingresos"""
    # Arrange
    expected_total = 2800.0
    household = Household()
    household.register_member(base_member_1)
    household.register_member(base_member_2)

    # Act
    total = household.calculate_total_incomes()

    # assert
    assert expected_total == total
