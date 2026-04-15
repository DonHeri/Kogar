from datetime import datetime

import pytest

from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.utils.currency import to_cents

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def tracker():
    """ExpenseTracker vacío"""
    return ExpenseTracker()


@pytest.fixture
def expense_rent():
    """Gasto: Amanda - fijos - 900€"""
    return Expense("Amanda", "fijos", to_cents(900.0), "Alquiler")


@pytest.fixture
def expense_groceries():
    """Gasto: Heri - variables - 120€"""
    return Expense("Heri", "variables", to_cents(120.0), "Supermercado")


@pytest.fixture
def expense_utilities():
    """Gasto: Amanda - fijos - 80€"""
    return Expense("Amanda", "fijos", to_cents(80.0), "Luz")


@pytest.fixture
def expense_leisure():
    """Gasto: Heri - ocio - 45.50€"""
    return Expense("Heri", "ocio", to_cents(45.50), "Cine")


@pytest.fixture
def tracker_with_expenses(
    tracker, expense_rent, expense_groceries, expense_utilities, expense_leisure
):
    """Tracker con 4 gastos registrados"""
    tracker.add_expense(expense_rent)
    tracker.add_expense(expense_groceries)
    tracker.add_expense(expense_utilities)
    tracker.add_expense(expense_leisure)
    return tracker


# ====================================================
# TESTS: Creación de ExpenseTracker
# ====================================================


def test_expense_tracker_creation_valid():
    """Test: Crear un tracker válido"""
    tracker = ExpenseTracker()

    assert isinstance(tracker.expenses, list)
    assert len(tracker.expenses) == 0


# ====================================================
# TESTS: Storage - add_expense
# ====================================================


def test_add_expense_stores_single_expense(tracker, expense_rent):
    """Test: Añadir un gasto lo almacena correctamente"""
    tracker.add_expense(expense_rent)

    assert len(tracker.expenses) == 1
    assert tracker.expenses[0] == expense_rent


def test_add_expense_stores_multiple_expenses(tracker, expense_rent, expense_groceries):
    """Test: Añadir múltiples gastos los almacena en orden"""
    tracker.add_expense(expense_rent)
    tracker.add_expense(expense_groceries)

    assert len(tracker.expenses) == 2
    assert tracker.expenses[0] == expense_rent
    assert tracker.expenses[1] == expense_groceries


# ====================================================
# TESTS: Storage - get_all_expenses
# ====================================================


def test_get_all_expenses_returns_copy(tracker, expense_rent):
    """Test: get_all_expenses retorna una copia, no la lista original"""
    tracker.add_expense(expense_rent)

    expenses = tracker.get_all_expenses()

    assert expenses is not tracker.expenses
    assert expenses == tracker.expenses


def test_get_all_expenses_empty_tracker(tracker):
    """Test: get_all_expenses retorna lista vacía si no hay gastos"""
    expenses = tracker.get_all_expenses()

    assert expenses == []
    assert isinstance(expenses, list)


def test_get_all_expenses_returns_all_expenses(tracker_with_expenses):
    """Test: get_all_expenses retorna todos los gastos"""
    expenses = tracker_with_expenses.get_all_expenses()

    assert len(expenses) == 4


# ====================================================
# TESTS: Filters - get_expenses_by_category
# ====================================================


def test_get_expenses_by_category_returns_matching_expenses(tracker_with_expenses):
    """Test: Filtra gastos por categoría correctamente"""
    fijos = tracker_with_expenses.get_expenses_by_category("fijos")

    assert len(fijos) == 2
    assert all(e.category == "fijos" for e in fijos)


def test_get_expenses_by_category_returns_empty_if_no_match(tracker_with_expenses):
    """Test: Retorna lista vacía si no hay gastos en esa categoría"""
    inexistente = tracker_with_expenses.get_expenses_by_category("inexistente")

    assert inexistente == []


def test_get_expenses_by_category_empty_tracker(tracker):
    """Test: Retorna vacío en tracker sin gastos"""
    result = tracker.get_expenses_by_category("fijos")

    assert result == []


# ====================================================
# TESTS: Filters - get_expenses_by_member
# ====================================================


def test_get_expenses_by_member_returns_matching_expenses(tracker_with_expenses):
    """Test: Filtra gastos por miembro correctamente"""
    amanda_expenses = tracker_with_expenses.get_expenses_by_member("Amanda")

    assert len(amanda_expenses) == 2
    assert all(e.member == "amanda" for e in amanda_expenses)  # stored as lowercase


def test_get_expenses_by_member_returns_empty_if_no_match(tracker_with_expenses):
    """Test: Retorna lista vacía si el miembro no tiene gastos"""
    inexistente = tracker_with_expenses.get_expenses_by_member("Inexistente")

    assert inexistente == []


def test_get_expenses_by_member_empty_tracker(tracker):
    """Test: Retorna vacío en tracker sin gastos"""
    result = tracker.get_expenses_by_member("Amanda")

    assert result == []


# ====================================================
# TESTS: Aggregations - get_total_spent
# ====================================================


def test_get_total_spent_sums_all_expenses(tracker_with_expenses):
    """Test: get_total_spent suma todos los gastos en céntimos"""
    total = tracker_with_expenses.get_total_spent()

    # 900 + 120 + 80 + 45.50 = 1145.50€ = 114550 céntimos
    assert total == 114550


def test_get_total_spent_empty_tracker(tracker):
    """Test: Retorna 0 si no hay gastos"""
    total = tracker.get_total_spent()

    assert total == 0


def test_get_total_spent_single_expense(tracker, expense_rent):
    """Test: Funciona correctamente con un solo gasto"""
    tracker.add_expense(expense_rent)

    total = tracker.get_total_spent()

    assert total == 90000  # 900€


# ====================================================
# TESTS: Aggregations - get_total_spent_by_category
# ====================================================


def test_get_total_spent_by_category_sums_matching_expenses(tracker_with_expenses):
    """Test: Suma solo gastos de la categoría especificada"""
    fijos_total = tracker_with_expenses.get_total_spent_by_category("fijos")

    # 900 + 80 = 980€ = 98000 céntimos
    assert fijos_total == 98000


def test_get_total_spent_by_category_returns_zero_if_no_match(tracker_with_expenses):
    """Test: Retorna 0 si no hay gastos en esa categoría"""
    inexistente = tracker_with_expenses.get_total_spent_by_category("inexistente")

    assert inexistente == 0


def test_get_total_spent_by_category_empty_tracker(tracker):
    """Test: Retorna 0 en tracker sin gastos"""
    result = tracker.get_total_spent_by_category("fijos")

    assert result == 0


# ====================================================
# TESTS: Aggregations - get_total_spent_by_member
# ====================================================


def test_get_total_spent_by_member_sums_matching_expenses(tracker_with_expenses):
    """Test: Suma solo gastos del miembro especificado"""
    amanda_total = tracker_with_expenses.get_total_spent_by_member("Amanda")

    # 900 + 80 = 980€ = 98000 céntimos
    assert amanda_total == 98000


def test_get_total_spent_by_member_returns_zero_if_no_match(tracker_with_expenses):
    """Test: Retorna 0 si el miembro no tiene gastos"""
    inexistente = tracker_with_expenses.get_total_spent_by_member("Inexistente")

    assert inexistente == 0


def test_get_total_spent_by_member_empty_tracker(tracker):
    """Test: Retorna 0 en tracker sin gastos"""
    result = tracker.get_total_spent_by_member("Amanda")

    assert result == 0


# ====================================================
# TESTS: Breakdowns - get_category_breakdown
# ====================================================


def test_get_category_breakdown_returns_dict_with_all_categories(tracker_with_expenses):
    """Test: Retorna diccionario con todas las categorías y sus totales"""
    breakdown = tracker_with_expenses.get_category_breakdown()

    assert isinstance(breakdown, dict)
    assert len(breakdown) == 3  # fijos, variables, ocio
    assert "fijos" in breakdown
    assert "variables" in breakdown
    assert "ocio" in breakdown


def test_get_category_breakdown_calculates_totals_correctly(tracker_with_expenses):
    """Test: Los totales por categoría son correctos"""
    breakdown = tracker_with_expenses.get_category_breakdown()

    assert breakdown["fijos"] == 98000  # 900 + 80
    assert breakdown["variables"] == 12000  # 120
    assert breakdown["ocio"] == 4550  # 45.50


def test_get_category_breakdown_empty_tracker(tracker):
    """Test: Retorna diccionario vacío si no hay gastos"""
    breakdown = tracker.get_category_breakdown()

    assert breakdown == {}


def test_get_category_breakdown_single_expense(tracker, expense_rent):
    """Test: Funciona con un solo gasto"""
    tracker.add_expense(expense_rent)

    breakdown = tracker.get_category_breakdown()

    assert breakdown == {"fijos": 90000}


# ====================================================
# TESTS: Breakdowns - get_member_breakdown
# ====================================================


def test_get_member_breakdown_returns_dict_with_all_members(tracker_with_expenses):
    """Test: Retorna diccionario con todos los miembros y sus totales"""
    breakdown = tracker_with_expenses.get_member_breakdown()

    assert isinstance(breakdown, dict)
    assert len(breakdown) == 2  # amanda, heri
    assert "amanda" in breakdown  # stored as lowercase
    assert "heri" in breakdown


def test_get_member_breakdown_calculates_totals_correctly(tracker_with_expenses):
    """Test: Los totales por miembro son correctos"""
    breakdown = tracker_with_expenses.get_member_breakdown()

    assert breakdown["amanda"] == 98000  # 900 + 80 (stored as lowercase)
    assert breakdown["heri"] == 16550  # 120 + 45.50


def test_get_member_breakdown_empty_tracker(tracker):
    """Test: Retorna diccionario vacío si no hay gastos"""
    breakdown = tracker.get_member_breakdown()

    assert breakdown == {}


def test_get_member_breakdown_single_expense(tracker, expense_rent):
    """Test: Funciona con un solo gasto"""
    tracker.add_expense(expense_rent)

    breakdown = tracker.get_member_breakdown()

    assert breakdown == {"amanda": 90000}  # stored as lowercase


# ====================================================
# TESTS: Integration - Múltiples operaciones
# ====================================================


def test_tracker_handles_many_expenses_for_same_category(tracker):
    """Test: Maneja múltiples gastos de la misma categoría"""
    tracker.add_expense(Expense("Amanda", "fijos", to_cents(100.0)))
    tracker.add_expense(Expense("Heri", "fijos", to_cents(200.0)))
    tracker.add_expense(Expense("Amanda", "fijos", to_cents(300.0)))

    total = tracker.get_total_spent_by_category("fijos")

    assert total == 60000  # 600€


def test_tracker_handles_same_member_multiple_categories(tracker):
    """Test: Maneja un miembro con gastos en múltiples categorías"""
    tracker.add_expense(Expense("Amanda", "fijos", to_cents(100.0)))
    tracker.add_expense(Expense("Amanda", "variables", to_cents(50.0)))
    tracker.add_expense(Expense("Amanda", "ocio", to_cents(30.0)))

    amanda_total = tracker.get_total_spent_by_member("Amanda")

    assert amanda_total == 18000  # 180€


def test_filters_do_not_modify_original_list(tracker_with_expenses):
    """Test: Los filtros no modifican la lista original"""
    original_count = len(tracker_with_expenses.expenses)

    fijos = tracker_with_expenses.get_expenses_by_category("fijos")
    fijos.clear()

    assert len(tracker_with_expenses.expenses) == original_count
