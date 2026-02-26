from src.models.category_library import CategoryLibrary
import pytest


# ====== normalize ======
def test_normalize_whitespace():
    assert CategoryLibrary.normalize("  fijos  ") == "fijos"


def test_normalize_case():
    assert CategoryLibrary.normalize("VARIABLES") == "variables"


def test_normalize_empty_raises():
    with pytest.raises(ValueError):
        CategoryLibrary.normalize("   ")
