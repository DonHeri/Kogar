import pytest
from src.models.participante import Participante
from src.models.household import Household
from src.models.calculadora import Calculator


@pytest.fixture
def base_member_1():
    return Participante("Default_1")


@pytest.fixture
def base_member_2():
    return Participante("Default_2")


@pytest.fixture
def base_household():
    return Household()


def test_create_valid_household(base_household):
    """Verifica correcta creación de instancia Household"""

    # Assert
    assert isinstance(base_household.members, dict)


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
    base_household.members = {"Default_1": base_member_1, "Default_2": base_member_2}

    # Act
    total = base_household.obtain_total_incomes()

    # assert
    assert expected_total == total

# Test workflow completo setup
""" 
def test_full_workflow_transition(base_household, base_member_1):
    # 1. Registro
    base_member_1.monthly_income = 2000.0
    base_household.register_member(base_member_1)
    
    # 2. Cierre de registro
    base_household.lock_registration()
    assert base_household.phase == Phase.PLANNING
    
    # 3. Planificación (Auto-cálculo de ahorro)
    # Si ingreso es 2000, fijos 1000 y variables 500 -> ahorro debe ser 500
    base_household.set_budget_plan(fijos=1000.0, variables=500.0)
    
    assert base_household.budget_plan.ahorro_deuda == 500.0
    assert base_household.phase == Phase.EXECUTION
"""