import pytest
from src.models.member import Member
from src.models.household import Household
from src.models.budget import Budget
from src.models.constants import MetodoReparto

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def members_with_incomes():
    """Dos miembros con ingresos diferentes"""
    m1 = Member("Member1")
    m2 = Member("Member2")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    return {m1.name: m1, m2.name: m2}


@pytest.fixture
def member_zero_income():
    """Miembro sin ingresos"""
    return Member("NoIncome")


@pytest.fixture
def base_household():
    return Household(Budget())


@pytest.fixture
def household_with_members(base_household, members_with_incomes):
    """Household ya configurado con dos miembros con ingresos"""
    for member in members_with_incomes.values():
        base_household.register_member(member)
    return base_household


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


def test_register_duplicate_member_raises(base_household, member_zero_income):
    """Lanza error si se intenta registrar un miembro ya existente"""
    base_household.register_member(member_zero_income)
    with pytest.raises(ValueError, match="ya está registrado en el hogar"):
        base_household.register_member(member_zero_income)


# ====================================================
# TESTS: set_member_income
# ====================================================


def test_set_members_incomes_updates_correctly(base_household, member_zero_income):
    """Actualiza ingresos de miembro existente"""
    base_household.register_member(member_zero_income)

    base_household.set_member_income(member_zero_income.name, 500.0)

    assert member_zero_income.monthly_income == 50000


def test_set_members_incomes_raises_if_member_not_exists(base_household):
    """Lanza error si el miembro no está registrado"""
    with pytest.raises(ValueError, match="NoExiste no existe en el hogar"):
        base_household.set_member_income("NoExiste", 500)


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
# TESTS: get_percentages_by_method — PROPORTIONAL
# ====================================================


def test_get_percentages_calculates_correctly(base_household, members_with_incomes):
    """Calcula porcentajes correctos según ingresos"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    percentages = base_household.get_percentages_by_method(
        method=MetodoReparto.PROPORTIONAL
    )

    assert percentages["Member1"] == 6667
    assert percentages["Member2"] == 3333


def test_get_percentages_proportional_sums_to_10000(household_with_members):
    """Suma total de porcentajes proporcionales = 10000 (100%)"""
    percentages = household_with_members.get_percentages_by_method(
        method=MetodoReparto.PROPORTIONAL
    )

    assert sum(percentages.values()) == 10000


def test_get_percentages_raises_if_no_members(base_household):
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household.get_percentages_by_method(method=MetodoReparto.PROPORTIONAL)


# ====================================================
# TESTS: get_percentages_by_method — EQUAL
# ====================================================
def test_get_percentages_equal_splits_evenly(household_with_members):
    """Método EQUAL asigna 50/50 con dos miembros"""
    percentages = household_with_members.get_percentages_by_method(
        method=MetodoReparto.EQUAL
    )

    assert percentages["Member1"] == 5000
    assert percentages["Member2"] == 5000


def test_get_percentages_equal_sums_to_10000(household_with_members):
    """Suma total de porcentajes iguales = 10000 (100%)"""
    percentages = household_with_members.get_percentages_by_method(
        method=MetodoReparto.EQUAL
    )

    assert sum(percentages.values()) == 10000


def test_get_percentages_equal_raises_if_no_members(base_household):
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household.get_percentages_by_method(method=MetodoReparto.EQUAL)


# ====================================================
# TESTS: get_percentages_by_method — CUSTOM
# ====================================================


def test_get_percentages_custom_returns_set_splits(household_with_members):
    """Método CUSTOM devuelve los splits definidos previamente"""
    household_with_members.set_custom_splits({"Member1": 70.0, "Member2": 30.0})

    percentages = household_with_members.get_percentages_by_method(
        method=MetodoReparto.CUSTOM
    )

    assert percentages["Member1"] == 7000
    assert percentages["Member2"] == 3000


def test_get_percentages_custom_raises_if_splits_not_set(household_with_members):
    """Método CUSTOM lanza error si no se llamó set_custom_splits() antes"""
    # Eliminamos el atributo si existiera (estado limpio)
    if hasattr(household_with_members, "_custom_splits"):
        del household_with_members._custom_splits

    with pytest.raises(
        ValueError,
        match=r"Método CUSTOM requiere llamar a set_custom_splits\(\) primero",
    ):
        household_with_members.get_percentages_by_method(method=MetodoReparto.CUSTOM)


def test_get_percentages_custom_raises_if_no_members(base_household):
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household.get_percentages_by_method(method=MetodoReparto.CUSTOM)


# ====================================================
# TESTS: set_custom_splits
# ====================================================


def test_set_custom_splits_converts_to_basis_points(household_with_members):
    """Convierte porcentajes float a basis points correctamente"""
    household_with_members.set_custom_splits({"Member1": 55.55, "Member2": 44.45})

    assert household_with_members._custom_splits["Member1"] == 5555
    assert household_with_members._custom_splits["Member2"] == 4445


def test_set_custom_splits_stores_all_members(household_with_members):
    """Almacena splits para todos los miembros del hogar"""
    household_with_members.set_custom_splits({"Member1": 60.0, "Member2": 40.0})

    assert "Member1" in household_with_members._custom_splits
    assert "Member2" in household_with_members._custom_splits


def test_set_custom_splits_raises_if_no_members(base_household):
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(
        ValueError, match="Registra a los miembros antes de asignar porcentajes"
    ):
        base_household.set_custom_splits({"Member1": 50.0, "Member2": 50.0})


def test_set_custom_splits_raises_if_member_missing_from_splits(household_with_members):
    """Lanza error si falta un miembro en el dict de splits"""
    with pytest.raises(
        ValueError, match="Falta el porcentaje para el miembro: Member2"
    ):
        household_with_members.set_custom_splits({"Member1": 100.0})


def test_set_custom_splits_overwrites_previous(household_with_members):
    """Una segunda llamada sobreescribe los splits anteriores"""
    household_with_members.set_custom_splits({"Member1": 70.0, "Member2": 30.0})
    household_with_members.set_custom_splits({"Member1": 40.0, "Member2": 60.0})

    assert household_with_members._custom_splits["Member1"] == 4000
    assert household_with_members._custom_splits["Member2"] == 6000


# ====================================================
# TESTS: calculate_member_contribution_for_category
# ====================================================


def test_calculate_contribution_for_single_category(
    base_household, members_with_incomes
):
    """Calcula contribuciones para UNA categoría específica"""
    # Setup
    for member in members_with_incomes.values():
        base_household.register_member(member)

    percentages = base_household.get_percentages_by_method(
        method=MetodoReparto.PROPORTIONAL
    )
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

    percentages = base_household.get_percentages_by_method(
        method=MetodoReparto.PROPORTIONAL
    )
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

    percentages = base_household.get_percentages_by_method(
        method=MetodoReparto.PROPORTIONAL
    )

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
    summary = base_household.get_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

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

    summary = base_household.get_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

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

    summary = base_household.get_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

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

    summary = base_household.get_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

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

    summary = base_household.get_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

    # Categorías con 0 no deben generar error
    assert summary["variables"]["planned"] == 0
    assert summary["variables"]["total_assigned"] == 0
