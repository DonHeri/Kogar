from src.models.category_library import CategoryLibrary
import pytest


# ====================================================
# TESTS: normalize
# ====================================================


def test_normalize_whitespace():
    assert CategoryLibrary.normalize("  fijos  ") == "fijos"


def test_normalize_case():
    assert CategoryLibrary.normalize("VARIABLES") == "variables"


def test_normalize_empty_raises():
    with pytest.raises(ValueError, match="La categoría no puede estar vacía"):
        CategoryLibrary.normalize("   ")


def test_normalize_not_string_raises():
    """Test: normalize() lanza error si input no es string"""
    with pytest.raises(ValueError, match="La categoría debe ser texto"):
        CategoryLibrary.normalize(123)


# ====================================================
# TESTS: add_category
# ====================================================


def test_add_category_adds_to_extended():
    """Test: add_category() agrega categoría a EXTENDED_CATEGORIES"""
    CategoryLibrary.add_category("nueva_categoria")

    assert "nueva_categoria" in CategoryLibrary.EXTENDED_CATEGORIES


def test_add_category_normalizes_name():
    """Test: add_category() normaliza el nombre antes de agregar"""
    CategoryLibrary.add_category("  OTRA CATEGORIA  ")

    assert "otra categoria" in CategoryLibrary.EXTENDED_CATEGORIES


# ====================================================
# TESTS: Queries
# ====================================================


def test_get_standards_categories_returns_dict():
    """Test: get_standards_categories() retorna diccionario con categorías estándar"""
    standards = CategoryLibrary.get_standards_categories()

    assert "fijos" in standards
    assert "variables" in standards
    assert "reserva" in standards


def test_get_all_suggestions_includes_both():
    """Test: get_all_suggestions() incluye estándar + extendidas"""
    all_cats = CategoryLibrary.get_all_suggestions()

    assert "fijos" in all_cats  # Estándar
    assert "salud" in all_cats  # Extendida


def test_is_standard_returns_true_for_standard_category():
    """Test: is_standard() retorna True para categoría estándar"""
    assert CategoryLibrary.is_standard("fijos") is True
    assert CategoryLibrary.is_standard("variables") is True


def test_is_standard_returns_false_for_extended_category():
    """Test: is_standard() retorna False para categoría extendida"""
    assert CategoryLibrary.is_standard("salud") is False


def test_is_suggest_returns_true_for_extended_category():
    """Test: is_suggest() retorna True para categoría extendida"""
    assert CategoryLibrary.is_suggest("salud") is True
    assert CategoryLibrary.is_suggest("transporte") is True


def test_is_suggest_returns_false_for_standard_category():
    """Test: is_suggest() retorna False para categoría estándar"""
    assert CategoryLibrary.is_suggest("fijos") is False


def test_is_known_returns_true_for_standard_category():
    """Test: is_known() retorna True para categoría estándar"""
    assert CategoryLibrary.is_known("fijos") is True


def test_is_known_returns_true_for_extended_category():
    """Test: is_known() retorna True para categoría extendida"""
    assert CategoryLibrary.is_known("salud") is True


def test_is_known_returns_false_for_unknown_category():
    """Test: is_known() retorna False para categoría desconocida"""
    assert CategoryLibrary.is_known("inexistente") is False


def test_is_known_normalizes_input():
    """Test: is_known() normaliza input antes de verificar"""
    assert CategoryLibrary.is_known("  FIJOS  ") is True
