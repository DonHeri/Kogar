from datetime import date

from src.utils.dates import add_months


def test_add_months_within_same_year():
    assert add_months(date(2026, 3, 10), 2) == date(2026, 5, 10)


def test_add_months_crosses_year_forward():
    assert add_months(date(2025, 12, 20), 1) == date(2026, 1, 20)


def test_add_months_crosses_year_backward():
    assert add_months(date(2026, 1, 15), -1) == date(2025, 12, 15)


def test_add_months_clamps_to_shorter_month():
    """31 ene + 1 mes -> feb no tiene día 31, cae al último día del mes."""
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_add_months_clamps_on_leap_year():
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_add_months_zero_is_identity():
    assert add_months(date(2026, 6, 15), 0) == date(2026, 6, 15)


def test_add_months_large_jump_multiple_years():
    assert add_months(date(2026, 3, 10), 24) == date(2028, 3, 10)


def test_add_months_negative_large_jump():
    assert add_months(date(2026, 3, 10), -14) == date(2025, 1, 10)
