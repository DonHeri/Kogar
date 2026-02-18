import pytest
from src.models.participante import Participante
from src.models.household import Household
from src.models.budget import Budget

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def members_with_incomes():
    """Dos miembros con ingresos diferentes"""
    m1 = Participante("Member1")
    m2 = Participante("Member2")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    return {m1.name: m1, m2.name: m2}


@pytest.fixture
def member_zero_income():
    """Miembro sin ingresos"""
    return Participante("NoIncome")


@pytest.fixture
def base_household():
    
    return Household(Budget())


# ====================================================
# TESTS: Registro de miembros
# ====================================================


def test_create_valid_household(base_household):
    """Verifica correcta creación de instancia Household"""
    assert isinstance(base_household.members, dict)
    assert len(base_household.members) == 0


def test_register_member_adds_to_household(base_household, member_zero_income):
    """Verifica que se registre correctamente un miembro"""
    base_household.register_member(member_zero_income)

    assert member_zero_income.name in base_household.members
    assert base_household.members[member_zero_income.name] == member_zero_income


# ====================================================
# TESTS: set_members_incomes
# ====================================================


def test_set_members_incomes_updates_correctly(base_household, member_zero_income):
    """Actualiza ingresos de miembro existente"""
    base_household.register_member(member_zero_income)

    base_household.set_members_incomes(member_zero_income.name, 500.0)

    assert member_zero_income.monthly_income == 50000


def test_set_members_incomes_raises_if_member_not_exists(base_household):
    """Lanza error si el miembro no está registrado"""
    with pytest.raises(ValueError, match="NoExiste no existe en el hogar"):
        base_household.set_members_incomes("NoExiste", 500)


# ====================================================
# TESTS: get_total_incomes
# ====================================================


def test_get_total_incomes_calculates_correctly(base_household, members_with_incomes):
    """Calcula total de ingresos correctamente"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    total = base_household.get_total_incomes()

    assert total == 300000


def test_get_total_incomes_raises_if_no_members(base_household):
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household.get_total_incomes()


def test_get_total_incomes_raises_if_zero_incomes(base_household, member_zero_income):
    """Lanza error si todos los ingresos son 0"""
    base_household.register_member(member_zero_income)

    with pytest.raises(ValueError, match="Al menos un miembro debe tener ingresos > 0"):
        base_household.get_total_incomes()


# ====================================================
# TESTS: get_percentages
# ====================================================


def test_get_percentages_calculates_correctly(base_household, members_with_incomes):
    """Calcula porcentajes correctos según ingresos"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    percentages = base_household.get_percentages()

    assert percentages["Member1"] == 6667
    assert percentages["Member2"] == 3333


def test_get_percentages_raises_if_no_members(base_household):
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household.get_percentages()

# ====================================================
# TESTS: calculate_member_contribution_for_category
# ====================================================


def test_calculate_contribution_for_single_category(base_household, members_with_incomes):
    """Calcula contribuciones para UNA categoría específica"""
    # Setup
    for member in members_with_incomes.values():
        base_household.register_member(member)

    percentages = base_household.get_percentages()
    budget_fijos = 90000  # 900€

    # Act
    contributions = base_household.calculate_member_contribution_for_category(
        percentages, budget_fijos
    )

    # Assert
    assert isinstance(contributions, dict)
    assert "Member1" in contributions
    assert "Member2" in contributions
    assert sum(contributions.values()) == budget_fijos


def test_calculate_contribution_respects_income_proportions(
    base_household, members_with_incomes
):
    """Contribución refleja proporción de ingresos"""
    # Member1: 200000 (66.67%), Member2: 100000 (33.33%)
    for member in members_with_incomes.values():
        base_household.register_member(member)

    percentages = base_household.get_percentages()
    budget = 900000  # 9000€

    contributions = base_household.calculate_member_contribution_for_category(
        percentages, budget
    )

    # Member1 debe pagar ~66.67% de 9000 = ~6000€
    # Member2 debe pagar ~33.33% de 9000 = ~3000€
    assert contributions["Member1"] > contributions["Member2"]
    assert contributions["Member1"] > 590000  # ~5900€
    assert contributions["Member2"] < 310000  # ~3100€


def test_calculate_contribution_zero_budget(base_household, members_with_incomes):
    """Maneja presupuesto cero correctamente"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    percentages = base_household.get_percentages()

    contributions = base_household.calculate_member_contribution_for_category(
        percentages, 0
    )

    assert all(contrib == 0 for contrib in contributions.values())


# ====================================================
# TESTS: get_budget_contribution_summary
# ====================================================


def test_get_budget_contribution_summary_returns_all_categories(
    base_household, members_with_incomes
):
    """Retorna contribuciones para TODAS las categorías"""
    # Setup
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 900.0)
    base_household.budget.set_budget("variables", 300.0)
    base_household.budget.set_budget("deuda", 200.0)
    base_household.budget.set_budget("ahorro", 100.0)

    # Act
    summary = base_household.get_budget_contribution_summary()

    # Assert
    assert isinstance(summary, dict)
    assert "fijos" in summary
    assert "variables" in summary
    assert "deuda" in summary
    assert "ahorro" in summary


def test_get_budget_contribution_summary_structure(
    base_household, members_with_incomes
):
    """Estructura de resumen es correcta"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 900.0)

    summary = base_household.get_budget_contribution_summary()

    # Cada categoría tiene la estructura correcta
    assert "planned" in summary["fijos"]
    assert "contributions" in summary["fijos"]
    assert "total_assigned" in summary["fijos"]
    assert isinstance(summary["fijos"]["contributions"], dict)


def test_get_budget_contribution_summary_totals_match_budgets(
    base_household, members_with_incomes
):
    """Total asignado = presupuesto para cada categoría"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 900.0)
    base_household.budget.set_budget("variables", 300.0)

    summary = base_household.get_budget_contribution_summary()

    # Para cada categoría: total_assigned = planned
    for cat_name, cat_data in summary.items():
        if cat_data["planned"] > 0:  # Solo si tiene presupuesto
            assert cat_data["total_assigned"] == cat_data["planned"]


def test_get_budget_contribution_summary_is_iterable(
    base_household, members_with_incomes
):
    """Resumen es iterable y accesible por categoría"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 900.0)
    base_household.budget.set_budget("variables", 300.0)

    summary = base_household.get_budget_contribution_summary()

    # Puedo iterar y acceder sin problemas
    count = 0
    for cat_name, cat_data in summary.items():
        if cat_data["planned"] > 0:
            count += 1
            assert isinstance(cat_data["contributions"], dict)
            assert "Member1" in cat_data["contributions"]
            assert "Member2" in cat_data["contributions"]

    assert count >= 2


def test_get_budget_contribution_summary_with_zero_budgets(
    base_household, members_with_incomes
):
    """Maneja correctamente categorías con presupuesto 0"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    # Algunos presupuestos en 0
    base_household.budget.set_budget("fijos", 900.0)
    # variables, deuda y ahorro quedan en 0

    summary = base_household.get_budget_contribution_summary()

    # Categorías con 0 no deben generar error
    assert summary["variables"]["planned"] == 0
    assert summary["variables"]["total_assigned"] == 0