import pytest
from src.models.member import Member
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
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
    b = Budget()
    e = ExpenseTracker()
    b.set_standard_categories()  # o add_category manual
    return Household(budget=b, expense_tracker=e)


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

    base_household.set_member_income(member_zero_income.name, 50000)  # 500€ en céntimos

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
    with pytest.raises(ValueError, match="No hay miembros registrados"):
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
# TESTS: preview_budget_contribution_summary
# ====================================================


def test_preview_budget_contribution_summary_returns_all_categories(
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
    summary = base_household.preview_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

    # Assert
    assert isinstance(summary, dict)
    assert "fijos" in summary
    assert "variables" in summary
    assert "deuda" in summary
    assert "ahorro" in summary


def test_preview_budget_contribution_summary_structure(
    base_household, members_with_incomes
):
    """Estructura de resumen es correcta"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 900.0)

    summary = base_household.preview_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

    # Cada categoría tiene la estructura correcta
    assert "planned" in summary["fijos"]
    assert "contributions" in summary["fijos"]
    assert "total_assigned" in summary["fijos"]
    assert isinstance(summary["fijos"]["contributions"], dict)


def test_preview_budget_contribution_summary_totals_match_budgets(
    base_household, members_with_incomes
):
    """Total asignado = presupuesto para cada categoría"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 900.0)
    base_household.budget.set_budget("variables", 300.0)

    summary = base_household.preview_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

    # Para cada categoría: total_assigned = planned
    for cat_name, cat_data in summary.items():
        if cat_data["planned"] > 0:  # Solo si tiene presupuesto
            assert cat_data["total_assigned"] == cat_data["planned"]


def test_preview_budget_contribution_summary_is_iterable(
    base_household, members_with_incomes
):
    """Resumen es iterable y accesible por categoría"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 900.0)
    base_household.budget.set_budget("variables", 300.0)

    summary = base_household.preview_budget_contribution_summary(
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


def test_preview_budget_contribution_summary_with_zero_budgets(
    base_household, members_with_incomes
):
    """Maneja correctamente categorías con presupuesto 0"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    # Algunos presupuestos en 0
    base_household.budget.set_budget("fijos", 900.0)
    # variables, deuda y ahorro quedan en 0

    summary = base_household.preview_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

    # Categorías con 0 no deben generar error
    assert summary["variables"]["planned"] == 0
    assert summary["variables"]["total_assigned"] == 0


# ====================================================
# TESTS: VALIDATORS
# ====================================================


def test_validate_members_exist_raises_if_empty(base_household):
    """Validador lanza error si no hay miembros"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household._validate_has_members()


def test_validate_members_exist_passes_if_members(household_with_members):
    """Validador pasa sin error si hay miembros"""
    # No debe lanzar excepción
    household_with_members._validate_has_members()


def test_validate_total_incomes_positive_raises_if_zero(
    base_household, member_zero_income
):
    """Validador lanza error si ingresos son 0"""
    base_household.register_member(member_zero_income)
    with pytest.raises(ValueError, match="Al menos un miembro debe tener ingresos > 0"):
        base_household._validate_total_incomes_positive()


def test_validate_total_incomes_positive_passes_if_positive(household_with_members):
    """Validador pasa sin error si ingresos > 0"""
    # No debe lanzar excepción
    household_with_members._validate_total_incomes_positive()


def test_validate_all_members_have_split_raises_if_missing(household_with_members):
    """Validador lanza error si falta un miembro en splits"""
    with pytest.raises(
        ValueError, match="Falta el porcentaje para el miembro: Member2"
    ):
        household_with_members._validate_all_members_have_split({"Member1": 50.0})


def test_validate_all_members_have_split_passes_if_all_present(household_with_members):
    """Validador pasa sin error si todos los miembros están presentes"""
    # No debe lanzar excepción
    household_with_members._validate_all_members_have_split(
        {"Member1": 60.0, "Member2": 40.0}
    )


# ====================================================
# TESTS: PLANNING - Budget assignment
# ====================================================


def test_set_budget_for_category(household_with_members):
    """set_budget_for_category asigna presupuesto correctamente"""
    household_with_members.budget.set_standard_categories()
    household_with_members.set_budget_for_category("fijos", 5000)

    assert household_with_members.get_category_budget("fijos") == 500000


def test_set_budget_for_category_normalizes_input(household_with_members):
    """set_budget_for_category normaliza la entrada (mayúsculas)"""
    household_with_members.budget.set_standard_categories()
    household_with_members.set_budget_for_category("FIJOS", 3000)

    assert household_with_members.get_category_budget("fijos") == 300000


def test_set_budget_for_category_raises_if_nonexistent(household_with_members):
    """set_budget_for_category lanza ValueError si categoría no existe"""
    household_with_members.budget.set_standard_categories()

    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_members.set_budget_for_category("inexistente", 2000)


def test_set_budget_for_category_multiple(household_with_members):
    """Puedo asignar presupuesto a múltiples categorías"""
    household_with_members.budget.set_standard_categories()
    household_with_members.set_budget_for_category("fijos", 3000)
    household_with_members.set_budget_for_category("variables", 2000)

    assert household_with_members.get_category_budget("fijos") == 300000
    assert household_with_members.get_category_budget("variables") == 200000


# ====================================================
# TESTS: PLANNING - Planning Summary
# ====================================================


def test_get_planning_summary_basic(household_with_members):
    """get_planning_summary retorna estructura completa"""
    household_with_members.budget.set_standard_categories()
    household_with_members.set_budget_for_category("fijos", 3000)

    summary = household_with_members.get_planning_summary()

    assert isinstance(summary, dict)
    assert summary["members"] == ["Member1", "Member2"]
    assert summary["total_household_income"] == 300000
    assert summary["total_budgeted"] == 300000
    assert summary["loose_money"] == 0


def test_get_planning_summary_includes_distribution_method(household_with_members):
    """get_planning_summary incluye método de distribución"""
    household_with_members.budget.set_standard_categories()
    household_with_members.set_budget_for_category("fijos", 5000)

    summary = household_with_members.get_planning_summary()

    assert summary["distribution_method"] == MetodoReparto.PROPORTIONAL.value


def test_get_planning_summary_with_loose_money(household_with_members):
    """get_planning_summary calcula dinero suelto correctamente"""
    household_with_members.budget.set_standard_categories()
    household_with_members.set_budget_for_category("fijos", 2000)

    summary = household_with_members.get_planning_summary()

    # Total: 300000, Presupuestado: 200000, Suelto: 100000
    assert summary["total_budgeted"] == 200000
    assert summary["loose_money"] == 100000


def test_get_planning_summary_includes_contributions_preview(household_with_members):
    """get_planning_summary incluye preview de contribuciones"""
    household_with_members.budget.set_standard_categories()
    household_with_members.set_budget_for_category("fijos", 6000)

    summary = household_with_members.get_planning_summary()

    assert "contributions_preview" in summary
    assert "fijos" in summary["contributions_preview"]
    contributions = summary["contributions_preview"]["fijos"]["contributions"]
    assert sum(contributions.values()) == 600000


def test_get_planning_summary_raises_if_no_members(base_household):
    """get_planning_summary lanza ValueError si no hay miembros"""
    with pytest.raises(ValueError, match="No hay miembros"):
        base_household.get_planning_summary()


def test_get_planning_summary_with_multiple_budgets(household_with_members):
    """get_planning_summary con múltiples categorías presupuestadas"""
    household_with_members.budget.set_standard_categories()
    household_with_members.set_budget_for_category("fijos", 3000)
    household_with_members.set_budget_for_category("variables", 2000)
    household_with_members.set_budget_for_category("deuda", 1000)

    summary = household_with_members.get_planning_summary()

    assert summary["categories"] == ["fijos", "variables", "deuda", "ahorro"]
    assert summary["total_budgeted"] == 600000
    assert summary["loose_money"] == -300000  # Presupuestó más de lo que tiene


def test_get_planning_summary_percentages_sum_to_10000(household_with_members):
    """get_planning_summary percentages siempre suman 10000 (100%)"""
    household_with_members.budget.set_standard_categories()
    household_with_members.set_budget_for_category("fijos", 5000)

    summary = household_with_members.get_planning_summary()

    total_pct = sum(summary["distribution_percentages"].values())
    assert total_pct == 10000


# ====================================================
# TESTS: Category management
# ====================================================


def test_add_category_creates_in_budget(base_household):
    """Test: add_category() agrega categoría al budget"""
    base_household.add_category("educacion")

    assert "educacion" in base_household.get_active_categories()


def test_remove_category_deletes_from_budget(base_household):
    """Test: remove_category() elimina categoría del budget"""
    base_household.remove_category("fijos")

    assert "fijos" not in base_household.get_active_categories()


def test_set_standard_categories_populates_budget(base_household):
    """Test: set_standard_categories() establece categorías en budget"""
    # base_household ya tiene set_standard_categories() en fixture, pero testeamos explícitamente
    household = Household(Budget(), ExpenseTracker())
    household.set_standard_categories()

    categories = household.get_active_categories()
    assert "fijos" in categories
    assert "variables" in categories
    assert "ahorro" in categories
    assert "deuda" in categories


def test_get_active_categories_returns_list(base_household):
    """Test: get_active_categories() retorna lista de categorías"""
    categories = base_household.get_active_categories()

    assert isinstance(categories, list)
    assert len(categories) > 0


def test_get_category_budget_returns_amount(household_with_members):
    """Test: get_category_budget() retorna monto asignado"""
    household_with_members.set_budget_for_category("fijos", 1000)

    amount = household_with_members.get_category_budget("fijos")
    assert amount == 100000  # 1000€ = 100000 céntimos


# ====================================================
# TESTS: Distribution method assignment
# ====================================================


def test_assign_distribution_method_sets_method(household_with_members):
    """Test: assign_distribution_method() establece método de reparto"""
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)

    assert household_with_members.method == MetodoReparto.EQUAL


def test_assign_distribution_method_changes_percentages(household_with_members):
    """Test: assign_distribution_method() cambia los porcentajes de contribución"""
    # Por defecto usa PROPORTIONAL
    pct_proportional = household_with_members.get_percentages_by_method(
        MetodoReparto.PROPORTIONAL
    )

    # Cambiar a EQUAL
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    pct_equal = household_with_members.get_percentages_by_method(MetodoReparto.EQUAL)

    # Los porcentajes deben ser diferentes
    assert pct_proportional != pct_equal


# ====================================================
# TESTS: Coordinación Budget vs ExpenseTracker (MONTH phase)
# ====================================================


def test_register_expense_adds_to_tracker(household_with_members):
    """Test: register_expense() almacena en ExpenseTracker"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 1000)

    expense = Expense("Member1", "fijos", 25000, "Test expense")
    household_with_members.register_expense(expense)

    assert len(household_with_members.expense_tracker.expenses) == 1
    assert household_with_members.expense_tracker.expenses[0] == expense


def test_register_expense_validates_member_exists(household_with_members):
    """Test: register_expense() valida que el miembro existe"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 1000)

    expense = Expense("NonExistent", "fijos", 25000)

    with pytest.raises(ValueError, match="no existe en el hogar"):
        household_with_members.register_expense(expense)


def test_register_expense_validates_category_exists(household_with_members):
    """Test: register_expense() valida que la categoría existe"""
    from src.models.expense import Expense

    expense = Expense("Member1", "nonexistent", 25000)

    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_members.register_expense(expense)


def test_get_category_spent_returns_zero_when_no_expenses(household_with_members):
    """Test: get_category_spent() retorna 0 cuando no hay gastos"""
    household_with_members.set_budget_for_category("fijos", 1000)

    spent = household_with_members.get_category_spent("fijos")

    assert spent == 0


def test_get_category_spent_sums_expenses_for_category(household_with_members):
    """Test: get_category_spent() suma gastos de una categoría"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 1000)

    expense1 = Expense("Member1", "fijos", 25000)
    expense2 = Expense("Member2", "fijos", 15000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)

    spent = household_with_members.get_category_spent("fijos")

    assert spent == 40000


def test_get_category_spent_only_counts_matching_category(household_with_members):
    """Test: get_category_spent() solo cuenta gastos de la categoría solicitada"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 1000)
    household_with_members.set_budget_for_category("variables", 500)

    expense1 = Expense("Member1", "fijos", 25000)
    expense2 = Expense("Member2", "variables", 15000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)

    spent_fijos = household_with_members.get_category_spent("fijos")

    assert spent_fijos == 25000


def test_get_total_spent_returns_zero_when_no_expenses(household_with_members):
    """Test: get_total_spent() retorna 0 cuando no hay gastos"""
    household_with_members.set_budget_for_category("fijos", 1000)

    total_spent = household_with_members.get_total_spent()

    assert total_spent == 0


def test_get_total_spent_sums_all_expenses(household_with_members):
    """Test: get_total_spent() suma todos los gastos de todas las categorías"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 1000)
    household_with_members.set_budget_for_category("variables", 500)

    expense1 = Expense("Member1", "fijos", 25000)
    expense2 = Expense("Member2", "variables", 15000)
    expense3 = Expense("Member1", "fijos", 10000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)
    household_with_members.register_expense(expense3)

    total_spent = household_with_members.get_total_spent()

    assert total_spent == 50000


def test_get_category_remaining_when_no_expenses(household_with_members):
    """Test: get_category_remaining() retorna presupuesto completo si no hay gastos"""
    household_with_members.set_budget_for_category("fijos", 1000)

    remaining = household_with_members.get_category_remaining("fijos")

    assert remaining == 100000  # 1000€ = 100000 céntimos


def test_get_category_remaining_calculates_correctly(household_with_members):
    """Test: get_category_remaining() calcula presupuesto - gastado correctamente"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 1000)  # 100000 cents

    expense = Expense("Member1", "fijos", 25000)  # 250€
    household_with_members.register_expense(expense)

    remaining = household_with_members.get_category_remaining("fijos")

    assert remaining == 75000  # 100000 - 25000


def test_get_category_remaining_can_be_negative(household_with_members):
    """Test: get_category_remaining() puede ser negativo (sobregasto)"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 1000)  # 100000 cents

    expense = Expense("Member1", "fijos", 150000)  # 1500€ (más del presupuesto)
    household_with_members.register_expense(expense)

    remaining = household_with_members.get_category_remaining("fijos")

    assert remaining == -50000  # 100000 - 150000


def test_get_total_remaining_when_no_expenses(household_with_members):
    """Test: get_total_remaining() retorna presupuesto total si no hay gastos"""
    household_with_members.set_budget_for_category("fijos", 1000)
    household_with_members.set_budget_for_category("variables", 500)

    total_remaining = household_with_members.get_total_remaining()

    assert total_remaining == 150000  # 1500€


def test_get_total_remaining_calculates_correctly(household_with_members):
    """Test: get_total_remaining() calcula total presupuestado - total gastado"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 1000)  # 100000
    household_with_members.set_budget_for_category("variables", 500)  # 50000

    expense1 = Expense("Member1", "fijos", 25000)
    expense2 = Expense("Member2", "variables", 10000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)

    total_remaining = household_with_members.get_total_remaining()

    assert total_remaining == 115000  # 150000 - 35000


def test_get_total_remaining_can_be_negative(household_with_members):
    """Test: get_total_remaining() puede ser negativo (sobregasto total)"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 500)  # 50000

    expense = Expense("Member1", "fijos", 75000)  # Más del presupuesto
    household_with_members.register_expense(expense)

    total_remaining = household_with_members.get_total_remaining()

    assert total_remaining == -25000  # 50000 - 75000
