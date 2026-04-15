import pytest

from src.utils.currency import (
    format_percentage,
    to_cents,
    to_euros,
    to_percentage_basis,
)

# ====================================================
# TESTS: to_cents
# ====================================================


def test_to_cents_converts_euros_to_cents():
    """Convierte euros enteros a céntimos correctamente"""
    assert to_cents(1.0) == 100


def test_to_cents_converts_decimal_euros():
    """Convierte euros con decimales a céntimos redondeando correctamente"""
    assert to_cents(9.99) == 999


def test_to_cents_rounds_floating_point_noise():
    """Maneja ruido de punto flotante sin error de redondeo"""
    assert to_cents(0.1 + 0.2) == 30  # 0.30000000000000004 → 30


def test_to_cents_zero():
    """Cero euros → cero céntimos"""
    assert to_cents(0.0) == 0


def test_to_cents_large_amount():
    """Cantidades grandes se convierten correctamente"""
    assert to_cents(10000.0) == 1000000


def test_to_cents_returns_int():
    """El resultado es siempre entero"""
    assert isinstance(to_cents(3.50), int)


# ====================================================
# TESTS: to_euros
# ====================================================


def test_to_euros_formats_correctly():
    """Convierte céntimos a string con formato correcto"""
    assert to_euros(100) == "1.00€"


def test_to_euros_formats_decimals():
    """Céntimos no redondos se muestran con dos decimales"""
    assert to_euros(999) == "9.99€"


def test_to_euros_zero():
    """Cero céntimos → '0.00€'"""
    assert to_euros(0) == "0.00€"


def test_to_euros_large_amount():
    """Cantidades grandes se formatean correctamente"""
    assert to_euros(1000000) == "10000.00€"


def test_to_euros_returns_string():
    """El resultado es siempre string"""
    assert isinstance(to_euros(100), str)


def test_to_euros_includes_symbol():
    """El resultado siempre incluye el símbolo €"""
    assert to_euros(250).endswith("€")


# ====================================================
# TESTS: format_percentage
# ====================================================


def test_format_percentage_converts_correctly():
    """Convierte basis points a string de porcentaje"""
    assert format_percentage(5357) == "53.57%"


def test_format_percentage_round_number():
    """Porcentajes redondos se muestran con dos decimales"""
    assert format_percentage(5000) == "50.00%"


def test_format_percentage_zero():
    """Cero basis points → '0.00%'"""
    assert format_percentage(0) == "0.00%"


def test_format_percentage_full():
    """10000 basis points → '100.00%'"""
    assert format_percentage(10000) == "100.00%"


def test_format_percentage_returns_string():
    """El resultado es siempre string"""
    assert isinstance(format_percentage(5000), str)


def test_format_percentage_includes_symbol():
    """El resultado siempre incluye el símbolo %"""
    assert format_percentage(3333).endswith("%")


# ====================================================
# TESTS: to_percentage_basis
# ====================================================


def test_to_percentage_basis_converts_correctly():
    """Convierte porcentaje decimal a basis points correctamente"""
    assert to_percentage_basis(53.57) == 5357


def test_to_percentage_basis_round_number():
    """Porcentajes redondos se convierten sin error"""
    assert to_percentage_basis(50.0) == 5000


def test_to_percentage_basis_zero():
    """Cero porcentaje → cero basis points"""
    assert to_percentage_basis(0.0) == 0


def test_to_percentage_basis_full():
    """100% → 10000 basis points"""
    assert to_percentage_basis(100.0) == 10000


def test_to_percentage_basis_rounds_floating_point_noise():
    """Maneja ruido de punto flotante sin error de redondeo"""
    assert to_percentage_basis(33.33) == 3333


def test_to_percentage_basis_returns_int():
    """El resultado es siempre entero"""
    assert isinstance(to_percentage_basis(55.55), int)


# ====================================================
# TESTS: roundtrip
# ====================================================


def test_cents_roundtrip():
    """to_cents → to_euros es reversible para valores típicos"""
    original = 49.99
    assert to_euros(to_cents(original)) == "49.99€"


def test_percentage_roundtrip():
    """to_percentage_basis → format_percentage es reversible para valores típicos"""
    assert format_percentage(to_percentage_basis(66.67)) == "66.67%"
