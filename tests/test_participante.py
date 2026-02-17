import pytest
from src.models.participante import Participante


# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def base_member():
    return Participante("Default")


# ====================================================
# TESTS: Creación de participante
# ====================================================


def test_create_valid_member(base_member):
    """Crea participante correctamente con valores iniciales"""
    assert base_member.name == "Default"
    assert base_member.monthly_income == 0


def test_create_member_empty_name_raises_error():
    """Lanza error si nombre está vacío"""
    with pytest.raises(ValueError, match="Nombre no puede estar vacío"):
        Participante("")


def test_create_member_whitespace_name_raises_error():
    """Lanza error si nombre es solo espacios"""
    with pytest.raises(ValueError, match="Nombre no puede estar vacío"):
        Participante("   ")


# ====================================================
# TESTS: add_incomes
# ====================================================


def test_add_incomes_updates_correctly(base_member):
    """Suma ingresos correctamente"""
    base_member.add_incomes(300.0)
    base_member.add_incomes(400.0)

    assert base_member.monthly_income == 70000


def test_add_incomes_zero_is_valid(base_member):
    """Permite agregar ingreso de 0"""
    base_member.add_incomes(0.0)

    assert base_member.monthly_income == 0


def test_add_negative_income_raises_error(base_member):
    """Lanza error con ingreso negativo"""
    with pytest.raises(ValueError, match="Ingreso no puede ser negativo"):
        base_member.add_incomes(-500)
