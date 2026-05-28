# tests/test_constants.py
from src.models.constants import MetodoReparto, Phase

# ====================================================
# TESTS: MetodoReparto Enum
# ====================================================


def test_metodo_reparto_get_names_returns_all_names():
    """Test: get_names() retorna los nombres de todos los métodos de reparto"""
    names = MetodoReparto.get_names()

    assert "PROPORTIONAL" in names
    assert "EQUAL" in names
    assert "CUSTOM" in names
    assert len(names) == 3


def test_metodo_reparto_get_values_returns_all_values():
    """Test: get_values() retorna los valores de todos los métodos de reparto"""
    values = MetodoReparto.get_values()

    assert "proportional" in values
    assert "equal" in values
    assert "custom" in values
    assert len(values) == 3


def test_metodo_reparto_enum_members_exist():
    """Test: Los miembros del enum existen y tienen valores correctos"""
    assert MetodoReparto.PROPORTIONAL.value == "proportional"
    assert MetodoReparto.EQUAL.value == "equal"
    assert MetodoReparto.CUSTOM.value == "custom"


# ====================================================
# TESTS: Phase Enum
# ====================================================


def test_phase_get_names_returns_all_names():
    """Test: get_names() retorna los nombres de todas las fases"""
    names = Phase.get_names()

    assert "REGISTRATION" in names
    assert "PLANNING" in names
    assert "MONTH" in names
    assert "CLOSING" in names
    assert len(names) == 4


def test_phase_get_values_returns_all_values():
    """Test: get_values() retorna los valores de todas las fases"""
    values = Phase.get_values()

    assert "registration" in values
    assert "planning" in values
    assert "month" in values
    assert "closed" in values
    assert len(values) == 4


def test_phase_enum_members_exist():
    """Test: Los miembros del enum existen y tienen valores correctos"""
    assert Phase.REGISTRATION.value == "registration"
    assert Phase.PLANNING.value == "planning"
    assert Phase.MONTH.value == "month"
    assert Phase.CLOSING.value == "closed"
