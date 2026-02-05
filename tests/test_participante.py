from src.models.participante import Participante
import pytest


@pytest.fixture
def base_member():
    return Participante("Default", 1500.0)


def test_create_valid_member(base_member):
    """Verifica que la creación de la instancia de Participante sea correcta"""

    # Assert
    assert base_member.name == "Default"
    assert base_member.monthly_income == 1500.0


""" def test_calculate_contribution_percentage(base_member):
    #Verifica que el porcentaje calculado sea correcto
    # Arrange: 1500 de 3000 debe ser exactamente el 50%
    total_incomes = 3000
    expected_percentage = 50.0

    # Act
    result = base_member.calculate_contribution_percentage(total_incomes)

    # Assert
    assert result == expected_percentage """


# Raises
def test_name_empty_raises_error():
    """
    Verifica que se lance un ValueError si el nombre está vacío.
    """
    with pytest.raises(ValueError, match="Nombre no puede estar vacío"):
        Participante("", 1000)


def test_incorrect_monthly_income_raises_error():
    """
    Verifica que se lance un ValueError si el ingreso es negativo o 0.
    """
    with pytest.raises(ValueError, match="Ingresos deben ser superiores o igual a 0"):
        Participante("Default", -500)


# Verifica que ingreso de 0 también lance error.
""" 
def test_monthly_income_zero_raises_error():
    with pytest.raises(ValueError, match="Ingresos deben ser superiores o igual a 0"):
        Participante("Juan", 0)
"""

# Verifica que se lance error si total_incomes es 0.
""" 
def test_total_incomes_zero_raises_error(base_member):
    
    with pytest.raises(ValueError, match="El total de ingresos debe ser mayor a 0"):
        base_member.calculate_contribution_percentage(0) 
"""
