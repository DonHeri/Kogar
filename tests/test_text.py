"""Tests para módulo text (normalización y formateo de nombres)"""

import pytest
from src.utils.text import normalize_name, format_name


# ====================================================
# TESTS: normalize_name()
# ====================================================
def test_normalize_name_converts_to_lowercase():
    """normalize_name convierte a minúsculas"""
    assert normalize_name("Amanda") == "amanda"
    assert normalize_name("HERI") == "heri"


def test_normalize_name_strips_whitespace():
    """normalize_name elimina espacios al inicio y final"""
    assert normalize_name("  Amanda  ") == "amanda"
    assert normalize_name("\tHeri\n") == "heri"


def test_normalize_name_handles_multiple_words():
    """normalize_name maneja nombres compuestos"""
    assert normalize_name("Juan Carlos") == "juan carlos"
    assert normalize_name("MARÍA JOSÉ") == "maría josé"


def test_normalize_name_raises_if_empty_string():
    """normalize_name lanza ValueError si el nombre está vacío"""
    with pytest.raises(ValueError, match="Nombre no puede estar vacío"):
        normalize_name("")


def test_normalize_name_raises_if_only_whitespace():
    """normalize_name lanza ValueError si solo contiene espacios"""
    with pytest.raises(ValueError, match="Nombre no puede estar vacío"):
        normalize_name("   ")


def test_normalize_name_raises_if_not_string():
    """normalize_name lanza ValueError si no es string"""
    with pytest.raises(ValueError, match="El nombre debe ser texto"):
        normalize_name(123)

    with pytest.raises(ValueError, match="El nombre debe ser texto"):
        normalize_name(None)


# ====================================================
# TESTS: format_name()
# ====================================================
def test_format_name_title_cases_single_word():
    """format_name aplica Title Case a una palabra"""
    assert format_name("amanda") == "Amanda"
    assert format_name("heri") == "Heri"


def test_format_name_title_cases_multiple_words():
    """format_name aplica Title Case a nombres compuestos"""
    assert format_name("juan carlos") == "Juan Carlos"
    assert format_name("maría josé") == "María José"


def test_format_name_from_uppercase():
    """format_name maneja entrada en mayúsculas"""
    assert format_name("AMANDA") == "Amanda"


def test_format_name_from_mixed_case():
    """format_name normaliza entrada con mayúsculas/minúsculas mezcladas"""
    assert format_name("aMaNdA") == "Amanda"
