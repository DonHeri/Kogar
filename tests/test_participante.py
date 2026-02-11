from src.models.participante import Participante
import pytest


@pytest.fixture
def base_member():
    return Participante("Default")


def test_create_valid_member(base_member):
    """Verifica que la creación de la instancia de Participante sea correcta"""

    # Assert
    assert base_member.name == "Default"
    assert base_member.monthly_income == 0


def test_name_empty_raises_error():
    """
    Verifica que se lance un ValueError si el nombre está vacío.
    """
    with pytest.raises(ValueError, match="Nombre no puede estar vacío"):
        Participante("")


def test_add_incomes_is_correct(base_member):
    """Verifica que se agregan ingresos correctamente"""
    # Arrange:
    incomes_expected = 700.0

    # Act
    base_member.add_incomes(300.0)
    base_member.add_incomes(400.0)

    # Assert
    assert base_member.monthly_income == incomes_expected


def test_negative_income_raises_error(base_member):
    """
    Verifica que el sistema no permita ingresos menores o iguales a cero.
    """

    # Raise
    with pytest.raises(ValueError, match="Ingreso no puede ser negativo"):
        base_member.add_incomes(-500)
