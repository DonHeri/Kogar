import pytest
from datetime import datetime
from src.models.expense import Expense
from src.utils.currency import to_cents, to_euros


# ====================================================
# TESTS: Creación de Expense
# ====================================================


def test_expense_creation_valid():
    """Test: Crear un gasto válido almacena todos los atributos correctamente"""
    expense = Expense("Amanda", "fijos", 900.0, "Alquiler marzo")

    assert expense.member == "Amanda"
    assert expense.category == "fijos"
    assert expense.amount == to_cents(900.0)  # 90000 céntimos
    assert expense.description == "Alquiler marzo"
    assert isinstance(expense.date, datetime)


def test_expense_creation_without_description():
    """Test: Crear un gasto sin descripción usa string vacío por defecto"""
    expense = Expense("Heri", "variables", 45.50)

    assert expense.description == ""
    assert expense.member == "Heri"
    assert expense.amount == to_cents(45.50)


def test_expense_stores_amount_in_cents():
    """Test: El monto se almacena en céntimos internamente"""
    expense = Expense("Amanda", "fijos", 50.0)

    assert expense.amount == 5000  # 50€ = 5000 céntimos


def test_expense_date_is_datetime_object():
    """Test: La fecha es un objeto datetime, no string"""
    expense = Expense("Amanda", "fijos", 50.0)

    assert isinstance(expense.date, datetime)
    assert hasattr(expense.date, "year")
    assert hasattr(expense.date, "month")
    assert hasattr(expense.date, "day")


# ====================================================
# TESTS: Validaciones
# ====================================================


def test_expense_member_empty_raises_error():
    """Test: Crear gasto con member vacío lanza ValueError"""
    with pytest.raises(ValueError, match="member no puede estar vacío"):
        Expense("", "fijos", 100.0)


def test_expense_member_whitespace_raises_error():
    """Test: Crear gasto con member solo espacios lanza ValueError"""
    with pytest.raises(ValueError, match="member no puede estar vacío"):
        Expense("   ", "fijos", 100.0)


def test_expense_category_empty_raises_error():
    """Test: Crear gasto con category vacío lanza ValueError"""
    with pytest.raises(ValueError, match="category no puede estar vacío"):
        Expense("Amanda", "", 100.0)


def test_expense_category_whitespace_raises_error():
    """Test: Crear gasto con category solo espacios lanza ValueError"""
    with pytest.raises(ValueError, match="category no puede estar vacío"):
        Expense("Amanda", "   ", 100.0)


def test_expense_amount_zero_raises_error():
    """Test: Crear gasto con amount cero lanza ValueError"""
    with pytest.raises(ValueError, match="amount debe ser positivo"):
        Expense("Amanda", "fijos", 0.0)


def test_expense_amount_negative_raises_error():
    """Test: Crear gasto con amount negativo lanza ValueError"""
    with pytest.raises(ValueError, match="amount debe ser positivo"):
        Expense("Amanda", "fijos", -50.0)


# ====================================================
# TESTS: Properties de solo lectura
# ====================================================


def test_amount_property_returns_cents():
    """Test: Property amount retorna céntimos como int"""
    expense = Expense("Amanda", "fijos", 75.50)

    assert expense.amount == 7550
    assert isinstance(expense.amount, int)


def test_amount_property_is_readonly():
    """Test: Property amount es de solo lectura"""
    expense = Expense("Amanda", "fijos", 50.0)

    with pytest.raises(AttributeError):
        expense.amount = 10000


def test_date_property_returns_datetime():
    """Test: Property date retorna objeto datetime"""
    expense = Expense("Amanda", "fijos", 50.0)

    assert isinstance(expense.date, datetime)


def test_date_property_is_readonly():
    """Test: Property date es de solo lectura"""
    expense = Expense("Amanda", "fijos", 50.0)

    with pytest.raises(AttributeError):
        expense.date = datetime(2026, 1, 1)


# ====================================================
# TESTS: Métodos is_same_month / is_same_year
# ====================================================


def test_is_same_month_with_same_month_and_year():
    """Test: is_same_month retorna True si es el mismo mes y año"""
    expense = Expense("Amanda", "fijos", 50.0)
    expense._date = datetime(2026, 3, 15)

    assert expense.is_same_month(datetime(2026, 3, 1)) is True
    assert expense.is_same_month(datetime(2026, 3, 31)) is True


def test_is_same_month_with_different_month():
    """Test: is_same_month retorna False si es diferente mes"""
    expense = Expense("Amanda", "fijos", 50.0)
    expense._date = datetime(2026, 3, 15)

    assert expense.is_same_month(datetime(2026, 4, 15)) is False


def test_is_same_month_with_different_year():
    """Test: is_same_month retorna False si es diferente año (mismo mes)"""
    expense = Expense("Amanda", "fijos", 50.0)
    expense._date = datetime(2026, 3, 15)

    assert expense.is_same_month(datetime(2025, 3, 15)) is False


def test_is_same_month_without_parameter_uses_current_date():
    """Test: is_same_month sin parámetro compara con fecha actual"""
    expense = Expense("Amanda", "fijos", 50.0)
    # La fecha del expense es datetime.now(), así que debe ser True
    assert expense.is_same_month() is True


def test_is_same_year_with_same_year():
    """Test: is_same_year retorna True si es el mismo año"""
    expense = Expense("Amanda", "fijos", 50.0)
    expense._date = datetime(2026, 3, 15)

    assert expense.is_same_year(datetime(2026, 1, 1)) is True
    assert expense.is_same_year(datetime(2026, 12, 31)) is True


def test_is_same_year_with_different_year():
    """Test: is_same_year retorna False si es diferente año"""
    expense = Expense("Amanda", "fijos", 50.0)
    expense._date = datetime(2026, 3, 15)

    assert expense.is_same_year(datetime(2025, 3, 15)) is False


def test_is_same_year_without_parameter_uses_current_date():
    """Test: is_same_year sin parámetro compara con fecha actual"""
    expense = Expense("Amanda", "fijos", 50.0)
    # La fecha del expense es datetime.now(), así que debe ser True
    assert expense.is_same_year() is True


# ====================================================
# TESTS: Representación __repr__
# ====================================================


def test_repr_format():
    """Test: __repr__ muestra formato correcto con fecha dd/mm/yyyy"""
    expense = Expense("Amanda", "fijos", 900.0, "Alquiler")
    expense._date = datetime(2026, 3, 15)

    repr_str = repr(expense)

    assert "Amanda" in repr_str
    assert "fijos" in repr_str
    assert "900.00€" in repr_str
    assert "15/03/2026" in repr_str


def test_repr_without_description():
    """Test: __repr__ funciona sin descripción"""
    expense = Expense("Heri", "variables", 45.50)
    expense._date = datetime(2026, 3, 2)

    repr_str = repr(expense)

    assert "Heri" in repr_str
    assert "variables" in repr_str
    assert "45.50€" in repr_str
    assert "02/03/2026" in repr_str
