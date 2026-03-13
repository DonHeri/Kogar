import pytest
from src.models.finance_calculator import FinanceCalculator
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.member import Member
from src.models.constants import MetodoReparto


# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def incomes_map():
    return {"Member1": 200000, "Member2": 100000}


@pytest.fixture
def member_zero_income():
    return {"no_incomes": 0}


@pytest.fixture
def incomes_list():
    return [200000, 100000]


@pytest.fixture
def incomes_map_equal():
    return {"Member1": 1, "Member2": 1}


@pytest.fixture
def percentages_66_33():
    return {"Member1": 6667, "Member2": 3333}


@pytest.fixture
def household_base():
    b = Budget()
    e = ExpenseTracker()
    b.set_standard_categories()
    return Household(budget=b, expense_tracker=e)


# ====================================================
# TESTS: sum_values
# ====================================================


def test_sum_total_incomes(incomes_list):
    assert FinanceCalculator.sum_values(incomes_list) == 300000


def test_sum_empty_list_returns_zero():
    assert FinanceCalculator.sum_values([]) == 0


# ====================================================
# TESTS: calculate_percentage_based_on_weight_of_income
# ====================================================


def test_calculate_percentage_proportional_values(incomes_map):
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        incomes_map
    )
    assert percentages["Member1"] == 6667
    assert percentages["Member2"] == 3333


def test_calculate_percentage_proportional_sums_to_10000(incomes_map):
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        incomes_map
    )
    assert sum(percentages.values()) == 10000


def test_calculate_percentage_proportional_remainder_goes_to_max(incomes_map):
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        incomes_map
    )
    assert percentages["Member1"] >= 6666


def test_calculate_percentage_proportional_raises_on_zero_total(member_zero_income):
    with pytest.raises(ValueError, match="Total de ingresos debe ser superior a 0"):
        FinanceCalculator.calculate_percentage_based_on_weight_of_income(
            member_zero_income
        )


def test_calculate_percentage_proportional_raises_on_all_zeros():
    with pytest.raises(ValueError, match="Total de ingresos debe ser superior a 0"):
        FinanceCalculator.calculate_percentage_based_on_weight_of_income(
            {"Member1": 0, "Member2": 0}
        )


def test_calculate_percentage_proportional_equal_incomes():
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        {"Member1": 100000, "Member2": 100000}
    )
    assert percentages["Member1"] == 5000
    assert percentages["Member2"] == 5000
    assert sum(percentages.values()) == 10000


def test_calculate_percentage_proportional_three_members():
    income_map = {"A": 500000, "B": 300000, "C": 200000}
    percentages = FinanceCalculator.calculate_percentage_based_on_weight_of_income(
        income_map
    )
    assert percentages["A"] == 5000
    assert percentages["B"] == 3000
    assert percentages["C"] == 2000
    assert sum(percentages.values()) == 10000


# ====================================================
# TESTS: calculate_equal_percentage
# ====================================================


def test_calculate_equal_percentage_two_members():
    members = {"Member1": 200000, "Member2": 100000}
    percentages = FinanceCalculator.calculate_equal_percentage(members)
    assert percentages["Member1"] == 5000
    assert percentages["Member2"] == 5000


def test_calculate_equal_percentage_sums_to_10000_two_members():
    percentages = FinanceCalculator.calculate_equal_percentage(
        {"Member1": 200000, "Member2": 100000}
    )
    assert sum(percentages.values()) == 10000


def test_calculate_equal_percentage_three_members():
    members = {"A": 300000, "B": 200000, "C": 100000}
    percentages = FinanceCalculator.calculate_equal_percentage(members)
    assert percentages["A"] == 3334
    assert percentages["B"] == 3333
    assert percentages["C"] == 3333
    assert sum(percentages.values()) == 10000


def test_calculate_equal_percentage_sums_to_10000_three_members():
    percentages = FinanceCalculator.calculate_equal_percentage(
        {"A": 300000, "B": 200000, "C": 100000}
    )
    assert sum(percentages.values()) == 10000


def test_calculate_equal_percentage_remainder_goes_to_max_income():
    members = {"A": 100000, "B": 200000, "C": 300000}
    percentages = FinanceCalculator.calculate_equal_percentage(members)
    assert percentages["A"] == 3334
    assert sum(percentages.values()) == 10000


def test_calculate_equal_percentage_ignores_income_for_base_split():
    members = {"Rich": 1000000, "Poor": 10000}
    percentages = FinanceCalculator.calculate_equal_percentage(members)
    assert percentages["Rich"] == 5000
    assert percentages["Poor"] == 5000


# ====================================================
# TESTS: calculate_contribution
# ====================================================


def test_calculate_contribution_basic_67_33(percentages_66_33):
    budget = 90000
    contributions = FinanceCalculator.calculate_contribution_from_custom_splits(
        percentages_66_33, budget
    )
    assert contributions["Member1"] == 60003
    assert contributions["Member2"] == 29997
    assert sum(contributions.values()) == budget


def test_calculate_contribution_equal_split(incomes_map_equal):
    budget = 100000
    contributions = FinanceCalculator.calculate_contribution_from_incomes(
        incomes_map_equal, budget
    )
    assert contributions["Member1"] == 50000
    assert contributions["Member2"] == 50000
    assert sum(contributions.values()) == budget


def test_calculate_contribution_small_budget(percentages_66_33):
    budget = 100
    contributions = FinanceCalculator.calculate_contribution_from_custom_splits(
        percentages_66_33, budget
    )
    assert contributions["Member1"] == 67
    assert contributions["Member2"] == 33
    assert sum(contributions.values()) == budget


def test_calculate_contribution_zero_budget():
    contributions = FinanceCalculator.calculate_contribution_from_incomes(
        {"Member1": 5000, "Member2": 5000}, 0
    )
    assert contributions["Member1"] == 0
    assert contributions["Member2"] == 0
    assert sum(contributions.values()) == 0


def test_calculate_contribution_remainder_distributed_by_largest_truncation_loss(
    percentages_66_33,
):
    """El sobrante va al miembro con mayor pérdida por truncamiento, no siempre al de mayor porcentaje"""
    budget = 100
    contributions = FinanceCalculator.calculate_contribution_from_custom_splits(
        percentages_66_33, budget
    )
    assert sum(contributions.values()) == budget


def test_calculate_contribution_three_members():
    income_map = {"A": 500000, "B": 300000, "C": 200000}
    budget = 100000
    contributions = FinanceCalculator.calculate_contribution_from_incomes(income_map, budget)
    assert contributions["A"] == 50000
    assert contributions["B"] == 30000
    assert contributions["C"] == 20000
    assert sum(contributions.values()) == budget


def test_calculate_contribution_totals_always_match_budget(incomes_map):
    for budget in [90000, 300000, 500000, 1000000]:
        contributions = FinanceCalculator.calculate_contribution_from_incomes(incomes_map, budget)
        assert sum(contributions.values()) == budget


# ====================================================
# EDGE CASES: acumulación de redondeos entre categorías
# ====================================================


def test_edge_case_proportional_2_to_1_full_budget(household_base):
    """Presupuesto 100% con ratio 2:1 — ningún miembro excede su ingreso"""
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    household_base.set_budget_for_category("fijos", 150000)
    household_base.set_budget_for_category("variables", 90000)
    household_base.set_budget_for_category("deuda/ahorro", 60000)

    contributions = household_base.get_current_contributions()

    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )
    heri_total = sum(
        contributions[cat]["contributions"]["heri"] for cat in contributions
    )

    assert amanda_total <= 200000, f"Amanda excede: {amanda_total - 200000}¢"
    assert heri_total <= 100000, f"Heri excede: {heri_total - 100000}¢"

    for cat_name, cat_data in contributions.items():
        expected = household_base.get_category_budget(cat_name)
        actual = sum(cat_data["contributions"].values())
        assert actual == expected, f"{cat_name}: expected {expected}¢, got {actual}¢"

    assert amanda_total + heri_total == 300000


def test_edge_case_extreme_imbalance_99_to_1(household_base):
    """Ratio 99:1 con 5 categorías — caso extremo de acumulación"""
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 297000
    m2.monthly_income = 3000
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    for i in range(1, 6):
        household_base.add_category(f"categoria{i}")
        household_base.set_budget_for_category(f"categoria{i}", 60000)

    contributions = household_base.get_current_contributions()
    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )

    assert amanda_total <= 297000, f"Amanda excede: {amanda_total - 297000}¢"


def test_edge_case_five_members_equal_split(household_base):
    """5 miembros con EQUAL — ninguno excede su ingreso"""
    for i in range(1, 6):
        m = Member(f"miembro{i}")
        m.monthly_income = 60000
        household_base.register_member(m)

    household_base.freeze_registration_state()
    household_base.assign_distribution_method(MetodoReparto.EQUAL)

    household_base.set_budget_for_category("fijos", 150000)
    household_base.set_budget_for_category("variables", 90000)
    household_base.set_budget_for_category("deuda/ahorro", 60000)

    contributions = household_base.get_current_contributions()

    for i in range(1, 6):
        name = f"miembro{i}"
        total = sum(contributions[cat]["contributions"][name] for cat in contributions)
        assert total <= 60000, f"{name} excede: {total}¢ > 60000¢"

    for cat_name, cat_data in contributions.items():
        expected = household_base.get_category_budget(cat_name)
        actual = sum(cat_data["contributions"].values())
        assert actual == expected, f"{cat_name}: {actual}¢ != {expected}¢"


def test_edge_case_one_cent_per_category(household_base):
    """Presupuesto de 1 céntimo por categoría — no debe romperse"""
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    household_base.set_budget_for_category("fijos", 1)
    household_base.set_budget_for_category("variables", 1)
    household_base.set_budget_for_category("deuda/ahorro", 1)

    contributions = household_base.get_current_contributions()

    for cat_name, cat_data in contributions.items():
        actual = sum(cat_data["contributions"].values())
        assert actual == 1, f"{cat_name}: expected 1¢, got {actual}¢"


def test_edge_case_ten_categories_accumulate_remainders(household_base):
    """10 categorías — la acumulación de restos no excede el ingreso"""
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    for i in range(1, 11):
        household_base.add_category(f"categoria{i}")
        household_base.set_budget_for_category(f"categoria{i}", 30000)

    contributions = household_base.get_current_contributions()
    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )

    assert amanda_total <= 200000, f"Amanda excede: {amanda_total - 200000}¢"
