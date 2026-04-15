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

    assert "proporcional" in values
    assert "igual" in values
    assert "custom" in values
    assert len(values) == 3


def test_metodo_reparto_enum_members_exist():
    """Test: Los miembros del enum existen y tienen valores correctos"""
    assert MetodoReparto.PROPORTIONAL.value == "proporcional"
    assert MetodoReparto.EQUAL.value == "igual"
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

    assert "registro" in values
    assert "planificación" in values
    assert "transcurso_mes" in values
    assert "cierre" in values
    assert len(values) == 4


def test_phase_enum_members_exist():
    """Test: Los miembros del enum existen y tienen valores correctos"""
    assert Phase.REGISTRATION.value == "registro"
    assert Phase.PLANNING.value == "planificación"
    assert Phase.MONTH.value == "transcurso_mes"
    assert Phase.CLOSING.value == "cierre"
