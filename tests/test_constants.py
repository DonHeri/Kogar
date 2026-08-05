# tests/test_constants.py

import pytest
from src.models.constants import MetodoReparto, Phase

# ====================================================
# TESTS: MetodoReparto Enum
# ====================================================


def test_metodo_reparto_get_names_returns_all_names() -> None:
    """Test: get_names() retorna los nombres de todos los métodos de reparto"""
    names = MetodoReparto.get_names()

    assert "PROPORTIONAL" in names
    assert "EQUAL" in names
    assert "CUSTOM" in names
    assert len(names) == 3


def test_metodo_reparto_get_values_returns_all_values() -> None:
    """Test: get_values() retorna los valores de todos los métodos de reparto"""
    values = MetodoReparto.get_values()

    assert "proportional" in values
    assert "equal" in values
    assert "custom" in values
    assert len(values) == 3


def test_metodo_reparto_enum_members_exist() -> None:
    """Test: Los miembros del enum existen y tienen valores correctos"""
    assert MetodoReparto.PROPORTIONAL.value == "proportional"
    assert MetodoReparto.EQUAL.value == "equal"
    assert MetodoReparto.CUSTOM.value == "custom"


# ====================================================
# TESTS: Phase Enum
# ====================================================


def test_phase_get_names_returns_all_names() -> None:
    """Test: get_names() retorna los nombres de todas las fases"""
    names = Phase.get_names()

    assert "REGISTRATION" in names
    assert "PLANNING" in names
    assert "MONTH" in names
    assert "CLOSING" in names
    assert len(names) == 4


def test_phase_get_values_returns_all_values() -> None:
    """Test: get_values() retorna los valores de todas las fases"""
    values = Phase.get_values()

    assert "registration" in values
    assert "planning" in values
    assert "month" in values
    assert "closed" in values
    assert len(values) == 4


def test_phase_enum_members_exist() -> None:
    """Test: Los miembros del enum existen y tienen valores correctos"""
    assert Phase.REGISTRATION.value == "registration"
    assert Phase.PLANNING.value == "planning"
    assert Phase.MONTH.value == "month"
    assert Phase.CLOSING.value == "closed"


# ===============================================
# TESTS — Validación de fase
# ===============================================


def test_require_accepts_the_exact_phase() -> None:
    """Una mutación de PLANNING pasa si el período está en PLANNING"""
    Phase.PLANNING.require(Phase.PLANNING)


def test_require_rejects_any_other_phase() -> None:
    """La validación estricta no acepta una fase posterior"""
    with pytest.raises(ValueError, match="solo permitida en fase planning"):
        Phase.MONTH.require(Phase.PLANNING)


def test_require_at_least_allows_current_and_past() -> None:
    """Una consulta de PLANNING sigue disponible con el mes en marcha"""
    Phase.MONTH.require_at_least(Phase.PLANNING)


def test_require_at_least_allows_a_closed_period() -> None:
    """Cerrar el mes no puede dejar sus resúmenes inaccesibles"""
    Phase.CLOSING.require_at_least(Phase.MONTH)


def test_require_at_least_rejects_future_phases() -> None:
    """Lo que aún no ha ocurrido no se puede consultar"""
    with pytest.raises(ValueError, match="month o posterior"):
        Phase.PLANNING.require_at_least(Phase.MONTH)
