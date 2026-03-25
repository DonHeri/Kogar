import pytest
from datetime import datetime
from src.models.member import Member
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.saving_tracker import SavingTracker
from src.models.constants import MetodoReparto, SavingDestination


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
    s = SavingTracker()
    b.set_standard_categories()
    return Household(
        budget=b, expense_tracker=e, saving_tracker=s, method=MetodoReparto.EQUAL
    )


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
    with pytest.raises(ValueError, match="noexiste no existe en el hogar"):
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

    assert percentages["member1"] == 6667
    assert percentages["member2"] == 3333


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

    assert percentages["member1"] == 5000
    assert percentages["member2"] == 5000


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
    household_with_members.set_custom_splits({"member1": 70.0, "member2": 30.0})

    percentages = household_with_members.get_percentages_by_method(
        method=MetodoReparto.CUSTOM
    )

    assert percentages["member1"] == 7000
    assert percentages["member2"] == 3000


def test_get_percentages_custom_raises_if_splits_not_set(household_with_members):
    """Método CUSTOM lanza error si no se llamó set_custom_splits() antes"""
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
    household_with_members.set_custom_splits({"member1": 55.55, "member2": 44.45})

    assert household_with_members._custom_splits["member1"] == 5555
    assert household_with_members._custom_splits["member2"] == 4445


def test_set_custom_splits_stores_all_members(household_with_members):
    """Almacena splits para todos los miembros del hogar"""
    household_with_members.set_custom_splits({"member1": 60.0, "member2": 40.0})

    assert "member1" in household_with_members._custom_splits
    assert "member2" in household_with_members._custom_splits


def test_set_custom_splits_raises_if_no_members(base_household):
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household.set_custom_splits({"member1": 50.0, "member2": 50.0})


def test_set_custom_splits_raises_if_member_missing_from_splits(household_with_members):
    """Lanza error si falta un miembro en el dict de splits"""
    with pytest.raises(
        ValueError, match="Falta el porcentaje para el miembro: member2"
    ):
        household_with_members.set_custom_splits({"member1": 100.0})


def test_set_custom_splits_overwrites_previous(household_with_members):
    """Una segunda llamada sobreescribe los splits anteriores"""
    household_with_members.set_custom_splits({"member1": 70.0, "member2": 30.0})
    household_with_members.set_custom_splits({"member1": 40.0, "member2": 60.0})

    assert household_with_members._custom_splits["member1"] == 4000
    assert household_with_members._custom_splits["member2"] == 6000


# ====================================================
# TESTS: preview_budget_contribution_summary
# ====================================================


def test_preview_budget_contribution_summary_returns_all_categories(
    base_household, members_with_incomes
):
    """Retorna contribuciones para TODAS las categorías"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 90000)
    base_household.budget.set_budget("variables", 30000)
    base_household.budget.set_budget("reserva", 30000)

    summary = base_household.preview_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

    assert isinstance(summary, dict)
    assert "fijos" in summary
    assert "variables" in summary
    assert "reserva" in summary


def test_preview_budget_contribution_summary_structure(
    base_household, members_with_incomes
):
    """Estructura de resumen es correcta"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 90000)

    summary = base_household.preview_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

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

    base_household.budget.set_budget("fijos", 90000)
    base_household.budget.set_budget("variables", 30000)

    summary = base_household.preview_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

    for cat_name, cat_data in summary.items():
        if cat_data["planned"] > 0:
            assert cat_data["total_assigned"] == cat_data["planned"]


def test_preview_budget_contribution_summary_is_iterable(
    base_household, members_with_incomes
):
    """Resumen es iterable y accesible por categoría"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 90000)
    base_household.budget.set_budget("variables", 30000)

    summary = base_household.preview_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

    count = 0
    for cat_name, cat_data in summary.items():
        if cat_data["planned"] > 0:
            count += 1
            assert isinstance(cat_data["contributions"], dict)
            assert "member1" in cat_data["contributions"]
            assert "member2" in cat_data["contributions"]

    assert count >= 2


def test_preview_budget_contribution_summary_with_zero_budgets(
    base_household, members_with_incomes
):
    """Maneja correctamente categorías con presupuesto 0"""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    base_household.budget.set_budget("fijos", 90000)

    summary = base_household.preview_budget_contribution_summary(
        method=MetodoReparto.PROPORTIONAL
    )

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
    household_with_members._validate_total_incomes_positive()


def test_validate_all_members_have_split_raises_if_missing(household_with_members):
    """Validador lanza error si falta un miembro en splits"""
    with pytest.raises(
        ValueError, match="Falta el porcentaje para el miembro: member2"
    ):
        household_with_members._validate_all_members_have_split({"member1": 50.0})


def test_validate_all_members_have_split_passes_if_all_present(household_with_members):
    """Validador pasa sin error si todos los miembros están presentes"""
    household_with_members._validate_all_members_have_split(
        {"member1": 60.0, "member2": 40.0}
    )


# ====================================================
# TESTS: PLANNING - Budget assignment
# ====================================================


def test_set_budget_for_category(household_with_members):
    """set_budget_for_category asigna presupuesto correctamente"""
    household_with_members.set_budget_for_category("fijos", 200000)

    assert household_with_members.get_category_budget("fijos") == 200000


def test_set_budget_for_category_normalizes_input(household_with_members):
    """set_budget_for_category normaliza la entrada (mayúsculas)"""
    household_with_members.set_budget_for_category("FIJOS", 200000)

    assert household_with_members.get_category_budget("fijos") == 200000


def test_set_budget_for_category_raises_if_nonexistent(household_with_members):
    """set_budget_for_category lanza ValueError si categoría no existe"""
    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_members.set_budget_for_category("inexistente", 200000)


def test_set_budget_for_category_multiple(household_with_members):
    """Puedo asignar presupuesto a múltiples categorías"""
    household_with_members.set_budget_for_category("fijos", 200000)
    household_with_members.set_budget_for_category("variables", 100000)

    assert household_with_members.get_category_budget("fijos") == 200000
    assert household_with_members.get_category_budget("variables") == 100000


# ====================================================
# TESTS: PLANNING - Planning Summary
# ====================================================


def test_get_planning_summary_basic(household_with_members):
    """get_planning_summary retorna estructura completa"""
    household_with_members.set_budget_for_category("fijos", 300000)

    summary = household_with_members.get_planning_summary()

    assert isinstance(summary, dict)
    assert summary["members"] == ["member1", "member2"]
    assert summary["total_household_income"] == 300000

    assert summary["total_budgeted"] == 300000
    assert summary["missing_money"]["total"] == 0
    assert summary["debt"]["member1"] == 0
    assert summary["debt"]["member2"] == 0
    assert summary["saving_goal"]["member1"] == 0
    assert summary["saving_goal"]["member2"] == 0


def test_get_planning_summary_includes_distribution_method(household_with_members):
    """get_planning_summary incluye método de distribución"""
    household_with_members.set_budget_for_category("fijos", 200000)

    summary = household_with_members.get_planning_summary()

    assert summary["distribution_method"] == MetodoReparto.EQUAL.value


def test_get_planning_summary_with_missing_money(household_with_members):
    """get_planning_summary calcula missing_money correctamente"""
    household_with_members.set_budget_for_category("fijos", 200000)

    summary = household_with_members.get_planning_summary()

    # Total: 300000, Presupuestado: 200000, Suelto: 100000
    assert summary["total_budgeted"] == 200000
    assert summary["missing_money"]["total"] == 100000


def test_get_planning_summary_includes_contributions_preview(household_with_members):
    """get_planning_summary incluye preview de contribuciones"""
    household_with_members.set_budget_for_category(
        "fijos", 200000
    )  # <= 300000 ingresos

    summary = household_with_members.get_planning_summary()

    assert "contributions_preview" in summary
    assert "fijos" in summary["contributions_preview"]
    contributions = summary["contributions_preview"]["fijos"]["contributions"]
    assert sum(contributions.values()) == 200000

def test_get_planning_summary_includes_debts(household_with_members):
    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)
    household_with_members.set_budget_for_category("reserva", 0)
    
    summary = household_with_members.get_planning_summary()
    
    assert summary["missing_money"]["total"] == 150000
    
    pass

def test_get_planning_summary_raises_if_no_members(base_household):
    """get_planning_summary lanza ValueError si no hay miembros"""
    with pytest.raises(ValueError, match="No hay miembros"):
        base_household.get_planning_summary()


def test_get_planning_summary_returns_negative_missing_money_when_over_budget(
    household_with_members,
):
    """get_planning_summary permite over-budget y muestra missing_money negativo"""
    # Ingresos totales: 300000 — presupuesto: 600000
    household_with_members.set_budget_for_category("fijos", 300000)
    household_with_members.set_budget_for_category("variables", 200000)
    household_with_members.set_budget_for_category("reserva", 100000)

    summary = household_with_members.get_planning_summary()

    assert summary["missing_money"]["total"] == -300000


def test_get_planning_summary_percentages_sum_to_10000(household_with_members):
    """get_planning_summary percentages siempre suman 10000 (100%)"""
    household_with_members.set_budget_for_category(
        "fijos", 200000
    )  # <= 300000 ingresos

    summary = household_with_members.get_planning_summary()

    total_pct = sum(summary["distribution_percentages"].values())
    assert total_pct == 10000


# ====================================================
# TESTS: Category management
# ====================================================


def test_add_category_creates_in_budget(base_household):
    """add_category() agrega categoría al budget"""
    base_household.add_category("educacion")

    assert "educacion" in base_household.get_active_categories()


def test_remove_category_deletes_from_budget(base_household):
    """remove_category() elimina categoría del budget"""
    base_household.remove_category("fijos")

    assert "fijos" not in base_household.get_active_categories()


def test_set_standard_categories_populates_budget(base_household):
    """set_standard_categories() establece categorías en budget"""
    household = Household(Budget(), ExpenseTracker(), SavingTracker())
    household.set_standard_categories()

    categories = household.get_active_categories()
    assert "fijos" in categories
    assert "variables" in categories
    assert "reserva" in categories


def test_get_active_categories_returns_list(base_household):
    """get_active_categories() retorna lista de categorías"""
    categories = base_household.get_active_categories()

    assert isinstance(categories, list)
    assert len(categories) > 0


def test_get_category_budget_returns_amount(household_with_members):
    """get_category_budget() retorna monto asignado"""
    household_with_members.set_budget_for_category("fijos", 100000)

    amount = household_with_members.get_category_budget("fijos")
    assert amount == 100000


# ====================================================
# TESTS: get_registered_incomes
# ====================================================


def test_get_registered_incomes_raises_if_not_frozen(household_with_members):
    """Debe fallar si intentas obtener ingresos antes de congelarlos"""
    with pytest.raises(
        ValueError,
        match="Los ingresos no han sido congelados",
    ):
        household_with_members.get_registered_incomes()


# ====================================================
# TESTS: Distribution method assignment
# ====================================================


def test_assign_distribution_method_sets_method(household_with_members):
    """assign_distribution_method() establece método de reparto"""
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)

    assert household_with_members.method == MetodoReparto.EQUAL


def test_assign_distribution_method_changes_percentages(household_with_members):
    """assign_distribution_method() cambia los porcentajes de contribución"""
    pct_proportional = household_with_members.get_percentages_by_method(
        MetodoReparto.PROPORTIONAL
    )

    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    pct_equal = household_with_members.get_percentages_by_method(MetodoReparto.EQUAL)

    assert pct_proportional != pct_equal


# ====================================================
# TESTS: Coordinación Budget vs ExpenseTracker (MONTH phase)
# ====================================================


def test_register_expense_adds_to_tracker(household_with_members):
    """register_expense() almacena en ExpenseTracker"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)

    expense = Expense("member1", "fijos", 25000, "Test expense")
    household_with_members.register_expense(expense)

    assert len(household_with_members.expense_tracker.expenses) == 1
    assert household_with_members.expense_tracker.expenses[0] == expense


def test_register_expense_validates_member_exists(household_with_members):
    """register_expense() valida que el miembro existe"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)

    expense = Expense("NonExistent", "fijos", 25000)

    with pytest.raises(ValueError, match="no existe en el hogar"):
        household_with_members.register_expense(expense)


def test_register_expense_validates_category_exists(household_with_members):
    """register_expense() valida que la categoría existe"""
    from src.models.expense import Expense

    expense = Expense("member1", "nonexistent", 25000)

    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_members.register_expense(expense)


def test_get_category_spent_returns_zero_when_no_expenses(household_with_members):
    """get_category_spent() retorna 0 cuando no hay gastos"""
    household_with_members.set_budget_for_category("fijos", 100000)

    spent = household_with_members.get_category_spent("fijos")

    assert spent == 0


def test_get_category_spent_sums_expenses_for_category(household_with_members):
    """get_category_spent() suma gastos de una categoría"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)

    expense1 = Expense("member1", "fijos", 25000)
    expense2 = Expense("member2", "fijos", 15000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)

    spent = household_with_members.get_category_spent("fijos")

    assert spent == 40000


def test_get_category_spent_only_counts_matching_category(household_with_members):
    """get_category_spent() solo cuenta gastos de la categoría solicitada"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)

    expense1 = Expense("member1", "fijos", 25000)
    expense2 = Expense("member2", "variables", 15000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)

    spent_fijos = household_with_members.get_category_spent("fijos")

    assert spent_fijos == 25000


def test_get_total_spent_returns_zero_when_no_expenses(household_with_members):
    """get_total_spent() retorna 0 cuando no hay gastos"""
    household_with_members.set_budget_for_category("fijos", 100000)

    total_spent = household_with_members.get_total_spent()

    assert total_spent == 0


def test_get_total_spent_sums_all_expenses(household_with_members):
    """get_total_spent() suma todos los gastos de todas las categorías"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)

    expense1 = Expense("member1", "fijos", 25000)
    expense2 = Expense("member2", "variables", 15000)
    expense3 = Expense("member1", "fijos", 10000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)
    household_with_members.register_expense(expense3)

    total_spent = household_with_members.get_total_spent()

    assert total_spent == 50000


def test_get_category_remaining_when_no_expenses(household_with_members):
    """get_category_remaining() retorna presupuesto completo si no hay gastos"""
    household_with_members.set_budget_for_category("fijos", 100000)

    remaining = household_with_members.get_category_remaining("fijos")

    assert remaining == 100000


def test_get_category_remaining_calculates_correctly(household_with_members):
    """get_category_remaining() calcula presupuesto - gastado correctamente"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)

    expense = Expense("member1", "fijos", 25000)
    household_with_members.register_expense(expense)

    remaining = household_with_members.get_category_remaining("fijos")

    assert remaining == 75000


def test_get_category_remaining_can_be_negative(household_with_members):
    """get_category_remaining() puede ser negativo (sobregasto)"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)

    expense = Expense("member1", "fijos", 150000)
    household_with_members.register_expense(expense)

    remaining = household_with_members.get_category_remaining("fijos")

    assert remaining == -50000


def test_get_total_remaining_when_no_expenses(household_with_members):
    """get_total_remaining() retorna presupuesto total si no hay gastos"""
    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)

    total_remaining = household_with_members.get_total_remaining()

    assert total_remaining == 150000


def test_get_total_remaining_calculates_correctly(household_with_members):
    """get_total_remaining() calcula total presupuestado - total gastado"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)

    expense1 = Expense("member1", "fijos", 25000)
    expense2 = Expense("member2", "variables", 10000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)

    total_remaining = household_with_members.get_total_remaining()

    assert total_remaining == 115000


def test_get_total_remaining_can_be_negative(household_with_members):
    """get_total_remaining() puede ser negativo (sobregasto total)"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 50000)

    expense = Expense("member1", "fijos", 75000)
    household_with_members.register_expense(expense)

    total_remaining = household_with_members.get_total_remaining()

    assert total_remaining == -25000


# ====================================================
# TESTS: get_registration_summary
# ====================================================


def test_get_registration_summary_returns_correct_structure(household_with_members):
    """Debe retornar members, member_incomes, total_household_income"""
    summary = household_with_members.get_registration_summary()

    assert "members" in summary
    assert "member_incomes" in summary
    assert "total_household_income" in summary

    assert "member1" in summary["members"]
    assert "member2" in summary["members"]

    assert summary["member_incomes"]["member1"] == 200000
    assert summary["member_incomes"]["member2"] == 100000

    assert summary["total_household_income"] == 300000


# ====================================================
# TESTS: get_missing_money
# ====================================================


def test_get_missing_money_returns_difference_between_income_and_budget(
    household_with_members,
):
    """missing_money = ingresos totales - presupuesto total"""
    household_with_members.set_budget_for_category("fijos", 250000)

    loose_money = household_with_members.get_missing_money()

    assert missing_money == 50000


def test_get_missing_money_zero_when_budget_equals_income(household_with_members):
    """missing_money = 0 cuando presupuesto = ingresos"""
    household_with_members.set_budget_for_category("fijos", 300000)

    loose_money = household_with_members.get_missing_money()

    assert missing_money == 0


def test_get_missing_money_returns_negative_when_over_budget(household_with_members):
    """Over-budget devuelve missing_money negativo, no lanza excepción"""
    household_with_members.set_budget_for_category("fijos", 350000)

    loose = household_with_members.get_missing_money()

    assert missing == -50000


# ====================================================
# TESTS: get_member_owed_total()
# ====================================================


def test_get_member_owed_total_sums_all_category_contributions(household_with_members):
    """Debe sumar todas las contribuciones acordadas del miembro"""
    household_with_members.set_budget_for_category("fijos", 60000)
    household_with_members.set_budget_for_category("variables", 40000)
    household_with_members.set_budget_for_category("reserva", 20000)

    # Método reparto equitativo -> 120000 / 2 == 60000 por miembro
    household_with_members.assign_distribution_method(method=MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    owed = household_with_members.get_member_owed_total("member1")

    assert owed == 60000


def test_get_member_owed_total_normalizes_name(household_with_members):
    """Debe normalizar el nombre del miembro"""
    household_with_members.set_budget_for_category("fijos", 60000)
    household_with_members.assign_distribution_method(method=MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    owed = household_with_members.get_member_owed_total("MEMBER1")

    assert owed == 30000


def test_get_member_owed_total_raises_if_member_not_exists(household_with_members):
    """Debe fallar si el miembro no existe"""
    with pytest.raises(ValueError, match="no existe en el hogar"):
        household_with_members.get_member_owed_total("member3")


# ====================================================
# TESTS: get_member_balance()
# ====================================================


def test_get_member_balance_negative_when_owes_money(household_with_members):
    """Balance negativo cuando el miembro debe dinero (paid < owed)"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense = Expense("member1", "fijos", 20000, "Pago parcial")
    household_with_members.register_expense(expense)

    balance = household_with_members.get_member_balance("member1")

    # Balance = paid - owed = 20000 - 50000 = -30000
    assert balance == -30000


def test_get_member_balance_positive_when_paid_more(household_with_members):
    """Balance positivo cuando el miembro pagó de más (paid > owed)"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense = Expense("member1", "fijos", 80000, "Pagó de más")
    household_with_members.register_expense(expense)

    balance = household_with_members.get_member_balance("member1")

    # Balance = paid - owed = 80000 - 50000 = +30000
    assert balance == 30000


def test_get_member_balance_zero_when_paid_exact(household_with_members):
    """Balance cero cuando el miembro pagó exactamente lo acordado"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense = Expense("member1", "fijos", 50000, "Pagó exacto")
    household_with_members.register_expense(expense)

    balance = household_with_members.get_member_balance("member1")

    assert balance == 0


def test_get_member_balance_normalizes_name(household_with_members):
    """Debe normalizar el nombre del miembro"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense = Expense("member1", "fijos", 50000)
    household_with_members.register_expense(expense)

    balance = household_with_members.get_member_balance("MEMBER1")

    assert balance == 0


def test_get_member_balance_raises_if_member_not_exists(household_with_members):
    """Debe fallar si el miembro no existe"""
    with pytest.raises(ValueError, match="no existe en el hogar"):
        household_with_members.get_member_balance("member3")


# ====================================================
# TESTS: get_member_status()
# ====================================================


def test_get_member_status_returns_complete_structure(household_with_members):
    """Debe retornar dict con: income, owed, paid, balance, debt, saving_goal, by_category"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense1 = Expense("member1", "fijos", 30000)
    expense2 = Expense("member1", "variables", 10000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)

    status = household_with_members.get_member_status("member1")

    assert "income" in status
    assert "owed" in status
    assert "paid" in status
    assert "balance" in status
    assert "debt" in status
    assert "saving_goal" in status
    assert "by_category" in status

    assert status["income"] == 200000
    assert status["owed"] == 75000
    assert status["paid"] == 40000
    assert status["balance"] == -35000
    assert status["debt"] == 0
    assert status["saving_goal"] == 0


def test_get_member_status_paid_is_total_not_per_category(household_with_members):
    """CRÍTICO: 'paid' debe ser el total pagado, NO el paid de una categoría"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 60000)
    household_with_members.set_budget_for_category("variables", 40000)
    household_with_members.set_budget_for_category("reserva", 20000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense1 = Expense("member1", "fijos", 20000)
    expense2 = Expense("member1", "variables", 15000)
    expense3 = Expense("member1", "reserva", 5000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)
    household_with_members.register_expense(expense3)

    status = household_with_members.get_member_status("member1")

    # 'paid' debe ser la SUMA de todos los gastos (20000+15000+5000=40000)
    assert status["paid"] == 40000


def test_get_member_status_by_category_has_correct_structure(household_with_members):
    """'by_category' debe tener contribution, paid, remaining por categoría"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense1 = Expense("member1", "fijos", 30000)
    expense2 = Expense("member1", "variables", 10000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)

    status = household_with_members.get_member_status("member1")
    by_category = status["by_category"]

    assert "fijos" in by_category
    assert "variables" in by_category

    assert "contribution" in by_category["fijos"]
    assert "paid" in by_category["fijos"]
    assert "remaining" in by_category["fijos"]

    assert by_category["fijos"]["contribution"] == 50000
    assert by_category["fijos"]["paid"] == 30000
    assert by_category["fijos"]["remaining"] == 20000

    assert by_category["variables"]["contribution"] == 25000
    assert by_category["variables"]["paid"] == 10000
    assert by_category["variables"]["remaining"] == 15000


def test_get_member_status_normalizes_name(household_with_members):
    """Debe normalizar el nombre del miembro"""
    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    status = household_with_members.get_member_status("MEMBER1")

    assert status["income"] == 200000


def test_get_member_status_includes_debt_and_saving_goal(household_with_members):
    """debt y saving_goal deben reflejar los valores declarados en PLANNING"""
    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("reserva", 100000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.set_member_debt("member1", 20000)
    household_with_members.set_member_saving_goal("member1", 30000)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    status = household_with_members.get_member_status("member1")

    assert status["debt"] == 20000
    assert status["saving_goal"] == 30000


def test_get_member_status_raises_if_member_not_exists(household_with_members):
    """Debe fallar si el miembro no existe"""
    with pytest.raises(ValueError, match="no existe en el hogar"):
        household_with_members.get_member_status("member3")


# ====================================================
# TESTS: get_month_summary()
# ====================================================


def test_get_month_summary_returns_complete_structure(household_with_members):
    """Debe retornar dict con 'totals' y 'by_category'"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense = Expense("member1", "fijos", 30000)
    household_with_members.register_expense(expense)

    summary = household_with_members.get_month_summary()

    assert "totals" in summary
    assert "by_category" in summary

    assert "total_budgeted" in summary["totals"]
    assert "total_spent" in summary["totals"]
    assert "total_remaining" in summary["totals"]


def test_get_month_summary_includes_missing_money(household_with_members):
    """'missing_money' debe estar presente en el summary"""
    # Total income = 300000, budgeted = 200000 → missing = 100000
    household_with_members.set_budget_for_category("fijos", 200000)

    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    summary = household_with_members.get_month_summary()

    assert "missing_money" in summary
    assert summary["missing_money"]["total"] == 100000


def test_get_month_summary_calculates_correctly(household_with_members):
    """Los cálculos de 'totals' deben ser correctos"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense1 = Expense("member1", "fijos", 30000)
    expense2 = Expense("member2", "variables", 20000)
    household_with_members.register_expense(expense1)
    household_with_members.register_expense(expense2)

    summary = household_with_members.get_month_summary()

    assert summary["totals"]["total_budgeted"] == 150000
    assert summary["totals"]["total_spent"] == 50000
    assert summary["totals"]["total_remaining"] == 100000


def test_get_month_summary_by_category_has_correct_structure(household_with_members):
    """Cada categoría en 'by_category' debe tener budget, spent, remaining"""
    from src.models.expense import Expense

    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    expense = Expense("member1", "fijos", 25000)
    household_with_members.register_expense(expense)

    summary = household_with_members.get_month_summary()
    by_category = summary["by_category"]

    assert "fijos" in by_category
    assert "variables" in by_category

    assert "budget" in by_category["fijos"]
    assert "spent" in by_category["fijos"]
    assert "remaining" in by_category["fijos"]

    assert by_category["fijos"]["budget"] == 100000
    assert by_category["fijos"]["spent"] == 25000
    assert by_category["fijos"]["remaining"] == 75000

    assert by_category["variables"]["budget"] == 50000
    assert by_category["variables"]["spent"] == 0
    assert by_category["variables"]["remaining"] == 50000


# ====================================================
# TESTS: get_agreed_percentages() y get_agreed_contributions()
# ====================================================


def test_get_agreed_percentages_raises_if_not_frozen(household_with_members):
    """Debe fallar si finish_planning() no ha sido llamado"""
    household_with_members.freeze_registration_state()

    with pytest.raises(ValueError, match="Los porcentajes no han sido congelados"):
        household_with_members.get_agreed_percentages()


def test_get_agreed_percentages_returns_frozen_percentages(household_with_members):
    """Debe retornar los porcentajes congelados después de finish_planning()"""
    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    percentages = household_with_members.get_agreed_percentages()

    assert "member1" in percentages
    assert "member2" in percentages
    assert percentages["member1"] == 6667
    assert percentages["member2"] == 3333


def test_get_agreed_contributions_raises_if_not_frozen(household_with_members):
    """Debe fallar si finish_planning() no ha sido llamado"""
    household_with_members.freeze_registration_state()

    with pytest.raises(ValueError, match="Las contribuciones no han sido congeladas"):
        household_with_members.get_agreed_contributions()


def test_get_agreed_contributions_returns_frozen_contributions(household_with_members):
    """Debe retornar las contribuciones congeladas después de finish_planning()"""
    household_with_members.set_budget_for_category("fijos", 100000)
    household_with_members.set_budget_for_category("variables", 50000)
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.freeze_registration_state()
    household_with_members.freeze_planning_state()

    contributions = household_with_members.get_agreed_contributions()

    assert "fijos" in contributions
    assert "variables" in contributions
    assert contributions["fijos"]["contributions"]["member1"] == 50000
    assert contributions["fijos"]["contributions"]["member2"] == 50000
    assert contributions["variables"]["contributions"]["member1"] == 25000
    assert contributions["variables"]["contributions"]["member2"] == 25000


# ====================================================
# TESTS: set_budget_by_percentage
# ====================================================


def test_set_budget_by_percentage_basic(household_with_members):
    """Asigna presupuesto basado en porcentaje de ingresos totales"""
    # Ingresos totales: 300000 céntimos (3000€)
    # 50% = 150000 céntimos (1500€)
    pct_basis = 5000  # 50%
    household_with_members.set_budget_by_percentage(pct_basis, "fijos")

    assert household_with_members.budget.get_category_budget("fijos") == 150000


def test_set_budget_by_percentage_fractional(household_with_members):
    """Maneja correctamente porcentajes fraccionarios"""
    # 33.33% de 300000 = 99990 céntimos (floor division)
    pct_basis = 3333  # 33.33%
    household_with_members.set_budget_by_percentage(pct_basis, "variables")

    assert household_with_members.budget.get_category_budget("variables") == 99990


def test_set_budget_by_percentage_zero(household_with_members):
    """Asigna 0 cuando el porcentaje es 0"""
    pct_basis = 0  # 0%
    household_with_members.set_budget_by_percentage(pct_basis, "fijos")

    assert household_with_members.budget.get_category_budget("fijos") == 0


def test_set_budget_by_percentage_full(household_with_members):
    """Asigna el total de ingresos cuando el porcentaje es 100%"""
    # 100% de 300000 = 300000 céntimos
    pct_basis = 10000  # 100%
    household_with_members.set_budget_by_percentage(pct_basis, "reserva")

    assert household_with_members.budget.get_category_budget("reserva") == 300000


def test_set_budget_by_percentage_delegates_to_set_budget(household_with_members):
    """Delegación a set_budget_for_category preserva validaciones"""
    pct_basis = 5000
    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_members.set_budget_by_percentage(pct_basis, "categoria_falsa")


# ====================================================
# TESTS: get_budget_as_percentage
# ====================================================


def test_get_budget_as_percentage_basic(household_with_members):
    """Retorna porcentaje correcto del presupuesto sobre ingresos"""
    # Ingresos: 300000, Presupuesto: 150000 → 50% = 5000 basis
    household_with_members.set_budget_for_category("fijos", 150000)

    pct_basis = household_with_members.get_budget_as_percentage("fijos")

    assert pct_basis == 5000  # 50%


def test_get_budget_as_percentage_zero_budget(household_with_members):
    """Retorna 0 cuando el presupuesto de categoría es 0"""
    household_with_members.set_budget_for_category("variables", 0)

    pct_basis = household_with_members.get_budget_as_percentage("variables")

    assert pct_basis == 0


def test_get_budget_as_percentage_full_budget(household_with_members):
    """Retorna 10000 (100%) cuando presupuesto = ingresos totales"""
    # Ingresos totales: 300000
    household_with_members.set_budget_for_category("reserva", 300000)

    pct_basis = household_with_members.get_budget_as_percentage("reserva")

    assert pct_basis == 10000  # 100%


def test_get_budget_as_percentage_fractional_result(household_with_members):
    """Maneja correctamente resultados fraccionarios con floor division"""
    # 100000 / 300000 = 0.33333... → (100000 * 10000) // 300000 = 3333 basis
    household_with_members.set_budget_for_category("variables", 100000)

    pct_basis = household_with_members.get_budget_as_percentage("variables")

    assert pct_basis == 3333  # 33.33%


def test_get_budget_as_percentage_nonexistent_category(household_with_members):
    """Lanza error si la categoría no existe"""
    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_members.get_budget_as_percentage("categoria_falsa")


def test_get_budget_as_percentage_roundtrip_consistency(household_with_members):
    """set + get debe ser consistente (considerando floor division)"""
    household_with_members.set_budget_by_percentage(5000, "fijos")
    retrieved_pct = household_with_members.get_budget_as_percentage("fijos")

    assert retrieved_pct == 5000


# ====================================================
# TESTS: Savings y Loose Money
# ====================================================


def test_register_savings_deposit_delegates_to_tracker(household_with_members):
    """Test: registrar un depósito de ahorro funciona y actualiza el balance"""
    # Congelamos para que se creen las cuentas en el SavingTracker
    household_with_members.freeze_registration_state()

    household_with_members.register_savings_deposit(
        "member1", 5000, SavingDestination.PERSONAL, "Ahorro test", datetime.now()
    )

    summary = household_with_members.get_member_savings_summary("member1")
    assert summary["balance_personal"] == 5000


def test_register_savings_withdrawal_delegates_to_tracker(household_with_members):
    """Test: registrar un retiro de ahorro reduce el balance"""
    household_with_members.freeze_registration_state()
    household_with_members.register_savings_deposit(
        "member1", 10000, SavingDestination.SHARED, "Fondo común"
    )

    household_with_members.register_savings_withdrawal(
        "member1", 4000, SavingDestination.SHARED, "Gasto casa"
    )

    summary = household_with_members.get_member_savings_summary("member1")
    assert summary["balance_shared"] == 6000


def test_get_missing_money_by_member_with_equal_method(household_with_members):
    """Test: calcula el missing_money equitativamente por miembro"""
    household_with_members.assign_distribution_method(MetodoReparto.EQUAL)
    household_with_members.set_budget_for_category("fijos", 200000)
    # Ingresos 300000 - Presupuesto 200000 = Missing 100000. Mitad = 50000.

    loose_m1 = household_with_members.get_missing_money_by_member("member1")
    loose_m2 = household_with_members.get_missing_money_by_member("member2")

    assert loose_m1 == 50000
    assert loose_m2 == 50000


def test_get_missing_money_by_member_with_custom_method(household_with_members):
    """Test: calcula el missing_money según porcentajes custom por miembro"""
    household_with_members.set_custom_splits({"member1": 70.0, "member2": 30.0})
    household_with_members.assign_distribution_method(MetodoReparto.CUSTOM)
    household_with_members.set_budget_for_category("fijos", 200000)
    # Loose 100000. 70% = 70000.

    loose_m1 = household_with_members.get_missing_money_by_member("member1")
    assert loose_m1 == 70000


# ====================================================
# TESTS: validate_debt_and_saving_dont_exceed_capacity
# ====================================================


def test_validate_debt_and_saving_passes_within_reserva(household_with_members):
    """Deuda + ahorro dentro de la parte de reserva no lanza"""
    # EQUAL: reserva 120000 / 2 = 60000 por miembro
    household_with_members.set_budget_for_category("reserva", 120000)
    household_with_members.set_member_saving_goal("member1", 40000)
    household_with_members.set_member_debt("member1", 10000)

    # 40000 + 10000 = 50000 <= 60000 → OK
    household_with_members.validate_debt_and_saving_dont_exceed_capacity()


def test_validate_debt_and_saving_raises_when_exceeds_reserva(household_with_members):
    """Deuda + ahorro mayor que la parte de reserva del miembro lanza ValueError"""
    # EQUAL: reserva 120000 / 2 = 60000 por miembro
    household_with_members.set_budget_for_category("reserva", 120000)
    household_with_members.set_member_saving_goal("member1", 50000)
    household_with_members.set_member_debt("member1", 20000)

    # 50000 + 20000 = 70000 > 60000 → lanza
    with pytest.raises(ValueError, match="member1"):
        household_with_members.validate_debt_and_saving_dont_exceed_capacity()


def test_validate_debt_and_saving_no_reserva_raises_if_commitments(
    household_with_members,
):
    """Sin categoría reserva, cualquier compromiso supera capacidad 0"""
    household_with_members.set_member_saving_goal("member1", 1)

    with pytest.raises(ValueError, match="member1"):
        household_with_members.validate_debt_and_saving_dont_exceed_capacity()


def test_validate_debt_and_saving_ignores_missing_money(household_with_members):
    """La validación usa solo la parte de reserva, no missing_money"""
    # fijos presupuestado menor que ingresos → hay missing_money
    household_with_members.set_budget_for_category("fijos", 100000)
    # reserva = 0 (no presupuestado) → capacidad = 0
    household_with_members.set_member_saving_goal("member1", 1)

    # Aunque haya missing_money disponible, no computa como capacidad
    with pytest.raises(ValueError, match="member1"):
        household_with_members.validate_debt_and_saving_dont_exceed_capacity()
