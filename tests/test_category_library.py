import pytest
from src.models.category_library import CategoryLibrary
from src.models.constants import CategoryBehavior


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


def test_add_category_adds_to_instance():
    """Test: add_category() agrega categoría a la instancia, no al dict de clase"""
    lib = CategoryLibrary()
    lib.add_category("nueva_categoria")

    assert lib.is_known("nueva_categoria")
    assert "nueva_categoria" not in CategoryLibrary.EXTENDED_CATEGORIES


def test_add_category_normalizes_name():
    """Test: add_category() normaliza el nombre antes de agregar"""
    lib = CategoryLibrary()
    lib.add_category("  OTRA CATEGORIA  ")

    assert lib.is_known("otra categoria")


def test_add_category_default_behavior_is_shared():
    lib = CategoryLibrary()
    lib.add_category("gimnasio")
    assert lib.get_default_behavior("gimnasio") == CategoryBehavior.SHARED


def test_add_category_accepts_custom_behavior():
    lib = CategoryLibrary()
    lib.add_category("retiro", CategoryBehavior.PERSONAL)
    assert lib.get_default_behavior("retiro") == CategoryBehavior.PERSONAL


# ====================================================
# TESTS: get_default_behavior
# ====================================================


def test_get_default_behavior_fijos_is_shared():
    assert CategoryLibrary().get_default_behavior("fijos") == CategoryBehavior.SHARED


def test_get_default_behavior_variables_is_personal():
    assert CategoryLibrary().get_default_behavior("variables") == CategoryBehavior.PERSONAL


def test_get_default_behavior_reserva_is_personal():
    assert CategoryLibrary().get_default_behavior("reserva") == CategoryBehavior.PERSONAL


def test_get_default_behavior_unknown_fallback_shared():
    assert CategoryLibrary().get_default_behavior("inventada") == CategoryBehavior.SHARED


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
    lib = CategoryLibrary()
    all_cats = lib.get_all_suggestions()

    assert "fijos" in all_cats  # Estándar
    assert "salud" in all_cats  # Extendida


def test_is_standard_returns_true_for_standard_category():
    """Test: is_standard() retorna True para categoría estándar"""
    assert CategoryLibrary.is_standard("fijos") is True
    assert CategoryLibrary.is_standard("variables") is True


def test_is_standard_returns_false_for_extended_category():
    """Test: is_standard() retorna False para categoría extendida"""
    assert CategoryLibrary.is_standard("salud") is False


def test_is_suggested_returns_true_for_extended_category():
    """Test: is_suggested() retorna True para categoría extendida"""
    assert CategoryLibrary.is_suggested("salud") is True
    assert CategoryLibrary.is_suggested("transporte") is True


def test_is_suggested_returns_false_for_standard_category():
    """Test: is_suggested() retorna False para categoría estándar"""
    assert CategoryLibrary.is_suggested("fijos") is False


def test_is_known_returns_true_for_standard_category():
    """Test: is_known() retorna True para categoría estándar"""
    assert CategoryLibrary().is_known("fijos") is True


def test_is_known_returns_true_for_extended_category():
    """Test: is_known() retorna True para categoría extendida"""
    assert CategoryLibrary().is_known("salud") is True


def test_is_known_returns_false_for_unknown_category():
    """Test: is_known() retorna False para categoría desconocida"""
    assert CategoryLibrary().is_known("inexistente") is False


def test_is_known_normalizes_input():
    """Test: is_known() normaliza input antes de verificar"""
    assert CategoryLibrary().is_known("  FIJOS  ") is True


def test_is_known_returns_true_for_custom_category():
    """Test: is_known() detecta categorías custom añadidas a la instancia"""
    lib = CategoryLibrary()
    lib.add_category("gimnasio")
    assert lib.is_known("gimnasio") is True


def test_custom_category_not_visible_in_other_instance():
    """Test: categoría custom de una instancia no contamina otra"""
    lib1 = CategoryLibrary()
    lib2 = CategoryLibrary()
    lib1.add_category("solo_en_lib1")
    assert lib2.is_known("solo_en_lib1") is False
