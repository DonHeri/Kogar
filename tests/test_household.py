from datetime import datetime, date

import pytest

from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.debt_bucket import DebtBucket
from src.models.exceptions import CeilingBelowChildrenError
from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.member import Member
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.models.saving_bucket import SavingBucket
from src.workflow.budget_distribution_service import BudgetDistributionService
from src.workflow.summary_service import SummaryService
from tests.helpers import make_category


# Rango de período amplio para queries de deuda por fechas en tests.
_WIDE_START = date(2000, 1, 1)
_WIDE_END = date(2100, 1, 1)


def _set_budget(hh, category, amount):
    BudgetDistributionService.set_budget_for_category(hh, category, amount)


def _set_budget_by_percentages(hh, percentages):
    BudgetDistributionService.set_budget_by_percentages(hh, percentages)


def _add_debt(hh, owner, installment_cents, principal_cents=None):
    """Declara una deuda con la cuota indicada. principal grande por defecto para que
    next_installment == cuota mientras quede saldo. Retorna el bucket_id."""
    if principal_cents is None:
        principal_cents = installment_cents * 100
    return hh.add_debt_bucket(
        DebtBucket(
            debt_bucket_name=f"deuda-{owner}",
            principal_cents=principal_cents,
            owner=owner,
            installment_cents=installment_cents,
        )
    )


def _add_saving_bucket(hh, owners, goal_cents=None, deadline=None):
    """Crea y registra un bucket de ahorro. owners: str (personal) o list (compartido)."""
    if isinstance(owners, str):
        owners = [owners]
    return hh.add_saving_bucket(
        SavingBucket(
            saving_bucket_name=f"bucket-{'-'.join(owners)}",
            owners=owners,
            goal_cents=goal_cents,
            deadline=deadline,
        )
    )


# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def members_with_incomes() -> dict[str, Member]:
    """Dos miembros con ingresos diferentes"""
    m1 = Member("Member1")
    m2 = Member("Member2")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    return {m1.name: m1, m2.name: m2}


@pytest.fixture
def member_zero_income() -> Member:
    """Miembro sin ingresos"""
    return Member("NoIncome")


@pytest.fixture
def base_household():
    b = Budget()
    e = ExpenseTracker()
    s = SavingBucketTracker()
    d = DebtBucketTracker()
    return Household(
        budget=b,
        expense_tracker=e,
        saving_bucket_tracker=s,
        debt_bucket_tracker=d,
        method=MetodoReparto.EQUAL,
    )


@pytest.fixture
def base_household_with_standard_cats() -> Household:
    b = Budget()
    e = ExpenseTracker()
    s = SavingBucketTracker()
    d = DebtBucketTracker()
    b.set_standard_categories(["member1", "member2"])
    return Household(
        budget=b,
        expense_tracker=e,
        saving_bucket_tracker=s,
        debt_bucket_tracker=d,
        method=MetodoReparto.EQUAL,
    )


@pytest.fixture
def household_with_members_and_categories_with_different_split_method(
    base_household: Household, members_with_incomes: dict[str, Member]
):
    for member in members_with_incomes.values():
        base_household.register_member(member)

    participants = list(members_with_incomes.keys())
    base_household.add_category(
        "fijos", participants=participants, method=MetodoReparto.EQUAL
    )
    base_household.budget.set_planned_amount(category="fijos", amount_cents=100000)
    base_household.add_category(
        "variables", participants=participants, method=MetodoReparto.PROPORTIONAL
    )
    base_household.budget.set_planned_amount(category="variables", amount_cents=100000)
    return base_household


@pytest.fixture
def household_with_members_standard_categories(
    base_household_with_standard_cats: Household,
    members_with_incomes: dict[str, Member],
) -> Household:
    """Household ya configurado con dos miembros con ingresos"""
    for member in members_with_incomes.values():
        base_household_with_standard_cats.register_member(member)
    return base_household_with_standard_cats


@pytest.fixture
def household_with_members_and_child_categories(
    household_with_members_standard_categories: Household,
) -> Household:
    """Household con dos hijas (vivienda, suministros) colgando de fijos."""
    household_with_members_standard_categories.add_category("vivienda", parent="fijos")
    household_with_members_standard_categories.add_category(
        "suministros", parent="fijos"
    )
    return household_with_members_standard_categories


# ====================================================
# TESTS: Registro de miembros
# ====================================================


def test_create_valid_household(base_household_with_standard_cats: Household) -> None:
    """Verifica correcta creación de instancia Household"""
    assert isinstance(base_household_with_standard_cats.members, dict)
    assert len(base_household_with_standard_cats.members) == 0


def test_register_member_adds_to_household(
    base_household_with_standard_cats: Household, member_zero_income: Member
) -> None:
    """Verifica que se registre correctamente un miembro"""
    base_household_with_standard_cats.register_member(member_zero_income)

    assert member_zero_income.name in base_household_with_standard_cats.members
    assert (
        base_household_with_standard_cats.members[member_zero_income.name]
        == member_zero_income
    )


def test_register_duplicate_member_raises(
    base_household_with_standard_cats: Household, member_zero_income: Member
) -> None:
    """Lanza error si se intenta registrar un miembro ya existente"""
    base_household_with_standard_cats.register_member(member_zero_income)
    with pytest.raises(ValueError, match="ya está registrado en el hogar"):
        base_household_with_standard_cats.register_member(member_zero_income)


# ============================================================
# freeze_registration
# ============================================================
def test_freeze_registation_add_personal_bucket_by_member(
    household_with_members_standard_categories: Household,
) -> None:
    household_with_members_standard_categories.prepare_period()

    for name in ("member1", "member2"):
        default_bucket = household_with_members_standard_categories.saving_bucket_tracker.get_default_bucket_by_member(
            name
        )
        assert default_bucket is not None
        bucket = list(default_bucket.values())[0]
        assert bucket.is_default is True
        assert bucket.owners == [name]


def test_prepare_period_does_not_duplicate_default_bucket(
    household_with_members_standard_categories: Household,
) -> None:
    household_with_members_standard_categories.prepare_period()
    household_with_members_standard_categories.prepare_period()

    buckets = household_with_members_standard_categories.saving_bucket_tracker.get_bucket_by_member(
        "member1"
    )
    default_buckets = [b for b in buckets.values() if b.is_default]
    assert len(default_buckets) == 1


def test_prepare_period_with_existing_bucket_does_not_crash(
    household_with_members_standard_categories: Household,
) -> None:
    _add_saving_bucket(
        household_with_members_standard_categories, "member1", goal_cents=100000
    )

    household_with_members_standard_categories.prepare_period()

    buckets = household_with_members_standard_categories.saving_bucket_tracker.get_bucket_by_member(
        "member1"
    )
    default_buckets = [b for b in buckets.values() if b.is_default]
    assert len(default_buckets) == 1


# ====================================================
# TESTS: set_member_income
# ====================================================


def test_set_members_incomes_updates_correctly(
    base_household_with_standard_cats: Household, member_zero_income: Member
) -> None:
    """Actualiza ingresos de miembro existente"""
    base_household_with_standard_cats.register_member(member_zero_income)

    base_household_with_standard_cats.set_member_income(
        member_zero_income.name, 50000
    )  # 500€ en céntimos

    assert member_zero_income.monthly_income == 50000


def test_set_members_incomes_raises_if_member_not_exists(
    base_household_with_standard_cats: Household,
) -> None:
    """Lanza error si el miembro no está registrado"""
    with pytest.raises(ValueError, match="noexiste no existe en el hogar"):
        base_household_with_standard_cats.set_member_income("NoExiste", 500)


# ====================================================
# TESTS: get_total_incomes
# ====================================================


def test_get_total_incomes_calculates_correctly(
    base_household_with_standard_cats: Household,
    members_with_incomes: dict[str, Member],
) -> None:
    """Calcula total de ingresos correctamente"""
    for member in members_with_incomes.values():
        base_household_with_standard_cats.register_member(member)

    total = base_household_with_standard_cats.get_total_incomes()

    assert total == 300000


def test_get_total_incomes_raises_if_no_members(
    base_household_with_standard_cats: Household,
) -> None:
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household_with_standard_cats.get_total_incomes()


def test_get_total_incomes_raises_if_zero_incomes(
    base_household_with_standard_cats: Household, member_zero_income: Member
) -> None:
    """Lanza error si todos los ingresos son 0"""
    base_household_with_standard_cats.register_member(member_zero_income)

    with pytest.raises(ValueError, match="Al menos un miembro debe tener ingresos > 0"):
        base_household_with_standard_cats.get_total_incomes()


# ====================================================
# TESTS: get_percentages_by_method — PROPORTIONAL
# ====================================================


def test_get_percentages_calculates_correctly(
    base_household_with_standard_cats: Household,
    members_with_incomes: dict[str, Member],
) -> None:
    """Calcula porcentajes correctos según ingresos"""
    for member in members_with_incomes.values():
        base_household_with_standard_cats.register_member(member)

    percentages = base_household_with_standard_cats.get_percentages_by_method(
        method=MetodoReparto.PROPORTIONAL
    )

    assert percentages["member1"] == 6667
    assert percentages["member2"] == 3333


def test_get_percentages_proportional_sums_to_10000(
    household_with_members_standard_categories: Household,
) -> None:
    """Suma total de porcentajes proporcionales = 10000 (100%)"""
    percentages = household_with_members_standard_categories.get_percentages_by_method(
        method=MetodoReparto.PROPORTIONAL
    )

    assert sum(percentages.values()) == 10000


def test_get_percentages_raises_if_no_members(
    base_household_with_standard_cats: Household,
) -> None:
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household_with_standard_cats.get_percentages_by_method(
            method=MetodoReparto.PROPORTIONAL
        )


# ====================================================
# TESTS: get_percentages_by_method — EQUAL
# ====================================================
def test_get_percentages_equal_splits_evenly(
    household_with_members_standard_categories: Household,
) -> None:
    """Método EQUAL asigna 50/50 con dos miembros"""
    percentages = household_with_members_standard_categories.get_percentages_by_method(
        method=MetodoReparto.EQUAL
    )

    assert percentages["member1"] == 5000
    assert percentages["member2"] == 5000


def test_get_percentages_equal_sums_to_10000(
    household_with_members_standard_categories: Household,
) -> None:
    """Suma total de porcentajes iguales = 10000 (100%)"""
    percentages = household_with_members_standard_categories.get_percentages_by_method(
        method=MetodoReparto.EQUAL
    )

    assert sum(percentages.values()) == 10000


def test_get_percentages_equal_raises_if_no_members(
    base_household_with_standard_cats: Household,
) -> None:
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household_with_standard_cats.get_percentages_by_method(
            method=MetodoReparto.EQUAL
        )


# ====================================================
# TESTS: get_percentages_by_method — CUSTOM
# ====================================================


def test_get_percentages_custom_returns_set_splits(
    household_with_members_standard_categories: Household,
) -> None:
    """Método CUSTOM devuelve los splits definidos previamente"""
    household_with_members_standard_categories.set_custom_splits(
        {"member1": 7000, "member2": 3000}
    )

    percentages = household_with_members_standard_categories.get_percentages_by_method(
        method=MetodoReparto.CUSTOM
    )

    assert percentages["member1"] == 7000
    assert percentages["member2"] == 3000


def test_get_percentages_custom_raises_if_splits_not_set(
    household_with_members_standard_categories: Household,
) -> None:
    """Método CUSTOM lanza error si no se llamó set_custom_splits() antes.

    El hogar nace con el dict vacío, así que la condición real es que esté vacío,
    no que el atributo falte: borrarlo a mano probaba un estado imposible.
    """
    assert household_with_members_standard_categories.get_custom_splits() == {}

    with pytest.raises(
        ValueError,
        match=r"Método CUSTOM requiere llamar a set_custom_splits\(\) primero",
    ):
        household_with_members_standard_categories.get_percentages_by_method(
            method=MetodoReparto.CUSTOM
        )


def test_get_percentages_custom_raises_if_no_members(
    base_household_with_standard_cats: Household,
) -> None:
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household_with_standard_cats.get_percentages_by_method(
            method=MetodoReparto.CUSTOM
        )


# ====================================================
# TESTS: set_custom_splits
# ====================================================


def test_set_custom_splits_stores_basis_points_as_given(
    household_with_members_standard_categories: Household,
) -> None:
    """El dominio recibe basis points y no los toca.

    Convertir aquí obligaba a que la BD, que ya guarda basis points, entrara por
    otra puerta: rehidratar por esta los multiplicaba por 100 otra vez.
    """
    household_with_members_standard_categories.set_custom_splits(
        {"member1": 5555, "member2": 4445}
    )

    assert household_with_members_standard_categories._custom_splits["member1"] == 5555
    assert household_with_members_standard_categories._custom_splits["member2"] == 4445


def test_set_custom_splits_stores_all_members(
    household_with_members_standard_categories: Household,
) -> None:
    """Almacena splits para todos los miembros del hogar"""
    household_with_members_standard_categories.set_custom_splits(
        {"member1": 6000, "member2": 4000}
    )

    assert "member1" in household_with_members_standard_categories._custom_splits
    assert "member2" in household_with_members_standard_categories._custom_splits


def test_set_custom_splits_raises_if_no_members(
    base_household_with_standard_cats: Household,
) -> None:
    """Lanza error si no hay miembros registrados"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household_with_standard_cats.set_custom_splits(
            {"member1": 5000, "member2": 5000}
        )


def test_set_custom_splits_raises_if_member_missing_from_splits(
    household_with_members_standard_categories: Household,
) -> None:
    """Lanza error si falta un miembro en el dict de splits"""
    with pytest.raises(
        ValueError, match="Falta el porcentaje para el miembro: member2"
    ):
        household_with_members_standard_categories.set_custom_splits({"member1": 10000})


def test_set_custom_splits_overwrites_previous(
    household_with_members_standard_categories: Household,
) -> None:
    """Una segunda llamada sobreescribe los splits anteriores"""
    household_with_members_standard_categories.set_custom_splits(
        {"member1": 7000, "member2": 3000}
    )
    household_with_members_standard_categories.set_custom_splits(
        {"member1": 4000, "member2": 6000}
    )

    assert household_with_members_standard_categories._custom_splits["member1"] == 4000
    assert household_with_members_standard_categories._custom_splits["member2"] == 6000


def test_set_custom_splits_switches_the_method_to_custom(
    household_with_members_standard_categories: Household,
) -> None:
    """Definir porcentajes propios activa CUSTOM.

    Separarlo permitía guardar unos splits con el método en PROPORTIONAL: el
    reparto los ignoraba y el usuario no se enteraba de que su ajuste no hacía
    nada.
    """
    assert household_with_members_standard_categories.method != MetodoReparto.CUSTOM

    household_with_members_standard_categories.set_custom_splits(
        {"member1": 7000, "member2": 3000}
    )

    assert household_with_members_standard_categories.method == MetodoReparto.CUSTOM


# ====================================================
# TESTS: preview_with_forced_method
# ====================================================


def test_preview_with_forced_method_returns_all_categories(
    base_household_with_standard_cats: Household,
    members_with_incomes: dict[str, Member],
) -> None:
    """Retorna contribuciones para TODAS las categorías"""
    for member in members_with_incomes.values():
        base_household_with_standard_cats.register_member(member)

    base_household_with_standard_cats.budget.set_planned_amount("fijos", 90000)
    base_household_with_standard_cats.budget.set_planned_amount("variables", 30000)
    base_household_with_standard_cats.budget.set_planned_amount("reserva", 30000)

    summary = base_household_with_standard_cats.preview_with_forced_method(
        MetodoReparto.PROPORTIONAL
    )

    assert isinstance(summary, dict)
    assert "fijos" in summary
    assert "variables" in summary
    assert "reserva" in summary


def test_preview_with_forced_method_structure(
    base_household_with_standard_cats: Household,
    members_with_incomes: dict[str, Member],
) -> None:
    """Cada categoría mapea directo a {miembro: céntimos}, sin envoltorio"""
    for member in members_with_incomes.values():
        base_household_with_standard_cats.register_member(member)

    base_household_with_standard_cats.budget.set_planned_amount("fijos", 90000)

    summary = base_household_with_standard_cats.preview_with_forced_method(
        MetodoReparto.PROPORTIONAL
    )

    assert isinstance(summary["fijos"], dict)
    assert "member1" in summary["fijos"]
    assert "member2" in summary["fijos"]


def test_preview_with_forced_method_totals_match_billable(
    base_household_with_standard_cats: Household,
    members_with_incomes: dict[str, Member],
) -> None:
    """Lo repartido en cada categoría coincide con su facturable"""
    for member in members_with_incomes.values():
        base_household_with_standard_cats.register_member(member)

    base_household_with_standard_cats.budget.set_planned_amount("fijos", 90000)
    base_household_with_standard_cats.budget.set_planned_amount("variables", 30000)

    summary = base_household_with_standard_cats.preview_with_forced_method(
        MetodoReparto.PROPORTIONAL
    )

    for cat_name, contributions in summary.items():
        billable = base_household_with_standard_cats.get_category_billable(cat_name)
        if billable > 0:
            assert sum(contributions.values()) == billable


def test_preview_with_forced_method_is_iterable(
    base_household_with_standard_cats: Household,
    members_with_incomes: dict[str, Member],
) -> None:
    """Resumen es iterable y accesible por categoría"""
    for member in members_with_incomes.values():
        base_household_with_standard_cats.register_member(member)

    base_household_with_standard_cats.budget.set_planned_amount("fijos", 90000)
    base_household_with_standard_cats.budget.set_planned_amount("variables", 30000)

    summary = base_household_with_standard_cats.preview_with_forced_method(
        MetodoReparto.PROPORTIONAL
    )

    count = 0
    for cat_name, contributions in summary.items():
        billable = base_household_with_standard_cats.get_category_billable(cat_name)
        if billable > 0:
            count += 1
            assert isinstance(contributions, dict)
            assert "member1" in contributions
            assert "member2" in contributions

    assert count >= 2


def test_preview_with_forced_method_with_zero_budgets(
    base_household_with_standard_cats: Household,
    members_with_incomes: dict[str, Member],
) -> None:
    """Maneja correctamente categorías con presupuesto 0"""
    for member in members_with_incomes.values():
        base_household_with_standard_cats.register_member(member)

    base_household_with_standard_cats.budget.set_planned_amount("fijos", 90000)

    summary = base_household_with_standard_cats.preview_with_forced_method(
        MetodoReparto.PROPORTIONAL
    )

    assert sum(summary["variables"].values()) == 0


# ====================================================
# TESTS: VALIDATORS
# ====================================================


def test_validate_members_exist_raises_if_empty(
    base_household_with_standard_cats: Household,
) -> None:
    """Validador lanza error si no hay miembros"""
    with pytest.raises(ValueError, match="No hay miembros registrados"):
        base_household_with_standard_cats.validate_has_members()


def test_validate_members_exist_passes_if_members(
    household_with_members_standard_categories: Household,
) -> None:
    """Validador pasa sin error si hay miembros"""
    household_with_members_standard_categories.validate_has_members()


def test_validate_total_incomes_positive_raises_if_zero(
    base_household_with_standard_cats: Household, member_zero_income: Member
) -> None:
    """Validador lanza error si ingresos son 0"""
    base_household_with_standard_cats.register_member(member_zero_income)
    with pytest.raises(ValueError, match="Al menos un miembro debe tener ingresos > 0"):
        base_household_with_standard_cats.validate_total_incomes_positive()


def test_validate_total_incomes_positive_passes_if_positive(
    household_with_members_standard_categories: Household,
) -> None:
    """Validador pasa sin error si ingresos > 0"""
    household_with_members_standard_categories.validate_total_incomes_positive()


def test_validate_all_members_have_split_raises_if_missing(
    household_with_members_standard_categories: Household,
) -> None:
    """Validador lanza error si falta un miembro en splits"""
    with pytest.raises(
        ValueError, match="Falta el porcentaje para el miembro: member2"
    ):
        household_with_members_standard_categories._validate_all_members_have_split(
            {"member1": 50.0}
        )


def test_validate_all_members_have_split_passes_if_all_present(
    household_with_members_standard_categories: Household,
) -> None:
    """Validador pasa sin error si todos los miembros están presentes"""
    household_with_members_standard_categories._validate_all_members_have_split(
        {"member1": 60.0, "member2": 40.0}
    )


# ====================================================
# TESTS: PLANNING - Budget assignment
# ====================================================


def test_set_budget_for_category(
    household_with_members_standard_categories: Household,
) -> None:
    """set_budget_for_category asigna presupuesto correctamente"""
    _set_budget(household_with_members_standard_categories, "fijos", 200000)

    assert (
        household_with_members_standard_categories.get_category_planned_amount("fijos")
        == 200000
    )


def test_set_budget_for_child_category(
    household_with_members_standard_categories: Household,
) -> None:
    """Asigna presupuesto a una hija dentro del techo de su raíz."""
    _set_budget(household_with_members_standard_categories, "fijos", 40000)
    household_with_members_standard_categories.add_category("vivienda", parent="fijos")

    _set_budget(household_with_members_standard_categories, "vivienda", 30000)

    assert (
        household_with_members_standard_categories.get_category_planned_amount(
            "vivienda"
        )
        == 30000
    )


def test_set_budget_for_category_normalizes_input(
    household_with_members_standard_categories: Household,
) -> None:
    """set_budget_for_category normaliza la entrada (mayúsculas)"""
    _set_budget(household_with_members_standard_categories, "FIJOS", 200000)

    assert (
        household_with_members_standard_categories.get_category_planned_amount("fijos")
        == 200000
    )


def test_set_budget_for_category_raises_if_nonexistent(
    household_with_members_standard_categories: Household,
) -> None:
    """set_budget_for_category lanza ValueError si categoría no existe"""
    with pytest.raises(ValueError, match="debe estar creada"):
        _set_budget(household_with_members_standard_categories, "inexistente", 200000)


def test_set_budget_for_category_multiple(
    household_with_members_standard_categories: Household,
) -> None:
    """Puedo asignar presupuesto a múltiples categorías"""
    _set_budget(household_with_members_standard_categories, "fijos", 200000)
    _set_budget(household_with_members_standard_categories, "variables", 100000)

    assert (
        household_with_members_standard_categories.get_category_planned_amount("fijos")
        == 200000
    )
    assert (
        household_with_members_standard_categories.get_category_planned_amount(
            "variables"
        )
        == 100000
    )


def test_set_budget_for_category_reassign_doesnt_double_count(
    household_with_members_standard_categories: Household,
) -> None:
    _set_budget(household_with_members_standard_categories, "fijos", 40000)
    _set_budget(household_with_members_standard_categories, "fijos", 50000)
    reserva = household_with_members_standard_categories.get_category_planned_amount(
        "reserva"
    )

    assert reserva == (
        household_with_members_standard_categories.get_total_incomes() - 50000
    )


def test_set_budget_over_ceiling_raises_error(
    household_with_members_and_child_categories: Household,
) -> None:
    """Asignar a una hija por encima del techo de su raíz lanza error."""
    _set_budget(household_with_members_and_child_categories, "fijos", 50000)
    _set_budget(household_with_members_and_child_categories, "vivienda", 30000)

    with pytest.raises(
        ValueError, match="No se puede superar el techo de la categoría raíz"
    ):
        _set_budget(household_with_members_and_child_categories, "suministros", 30000)


def test_set_root_budget_below_children_raises_error(
    household_with_members_and_child_categories: Household,
) -> None:
    """Bajar el techo por debajo de lo repartido en sus hijas lanza error."""
    hh = household_with_members_and_child_categories
    _set_budget(hh, "fijos", 50000)
    _set_budget(hh, "vivienda", 30000)
    _set_budget(hh, "suministros", 10000)

    with pytest.raises(CeilingBelowChildrenError) as excinfo:
        _set_budget(hh, "fijos", 35000)

    assert excinfo.value.category == "fijos"
    assert excinfo.value.children_total_cents == 40000


def test_set_root_budget_equal_to_children_is_allowed(
    household_with_members_and_child_categories: Household,
) -> None:
    """El techo puede bajar hasta justo lo repartido: el facturable queda en 0."""
    hh = household_with_members_and_child_categories
    _set_budget(hh, "fijos", 50000)
    _set_budget(hh, "vivienda", 30000)
    _set_budget(hh, "suministros", 10000)

    _set_budget(hh, "fijos", 40000)

    assert hh.get_category_planned_amount("fijos") == 40000
    assert hh.budget.get_category_billable("fijos") == 0


def test_contributions_sum_matches_total_budgeted(
    household_with_members_standard_categories: Household,
) -> None:
    """Con hijas, lo repartido entre miembros sigue siendo lo presupuestado.

    Una hija se reparte por su cuenta, pero el padre solo reparte lo que no ha
    delegado, así que nadie paga dos veces por el mismo dinero.
    """

    _set_budget(household_with_members_standard_categories, "fijos", 40000)
    household_with_members_standard_categories.add_category("vivienda", parent="fijos")

    _set_budget(household_with_members_standard_categories, "vivienda", 30000)

    contributions = (
        household_with_members_standard_categories.get_total_contributions_by_member()
    )

    assert (
        sum(contributions.values())
        == household_with_members_standard_categories.get_total_budgeted()
    )


def test_two_categories_with_different_split_method(
    household_with_members_and_categories_with_different_split_method: Household,
):
    """Comprueba que cada categoría se ajusta a su método de reparto"""
    household = household_with_members_and_categories_with_different_split_method
    contributions = household.get_current_contributions()
    fijos = contributions["fijos"]["contributions"]
    variables = contributions["variables"]["contributions"]

    assert fijos["member1"] == 50000
    assert fijos["member2"] == 50000
    assert variables["member1"] > variables["member2"]


# ====================================================
# TESTS: techo en euros o en porcentaje (P3)
# ====================================================


def test_percentage_ceiling_stays_live_until_income_changes(
    base_household: Household, members_with_incomes: dict[str, Member]
) -> None:
    """Alquiler al 20% y agua a 35€ conviven; subir un sueldo mueve el alquiler y deja el agua quieta."""
    for member in members_with_incomes.values():
        base_household.register_member(member)

    participants = list(members_with_incomes.keys())
    base_household.add_category("alquiler", participants=participants)
    base_household.set_planned_percentage("alquiler", 2000)  # 20%
    base_household.add_category("agua", participants=participants)
    base_household.budget.set_planned_amount("agua", 3500)  # 35€ fijos

    # member1 200000¢ + member2 100000¢ = 300000¢; 20% = 60000¢
    assert base_household.get_category_planned_amount("alquiler") == 60000
    assert base_household.get_category_planned_amount("agua") == 3500

    base_household.set_member_income("member1", 400000)

    # 400000¢ + 100000¢ = 500000¢; 20% = 100000¢
    assert base_household.get_category_planned_amount("alquiler") == 100000
    assert base_household.get_category_planned_amount("agua") == 3500


def test_setting_a_fixed_amount_clears_the_percentage(base_household: Household) -> None:
    """Declarar un importe fijo pisa el porcentaje: deja de recalcularse en vivo."""
    member = Member("member1")
    member.monthly_income = 200000
    base_household.register_member(member)

    base_household.add_category("ocio", participants=["member1"])
    base_household.set_planned_percentage("ocio", 1000)  # 10% de 200000 = 20000
    assert base_household.get_category_planned_amount("ocio") == 20000

    base_household.budget.set_planned_amount("ocio", 5000)
    base_household.set_member_income("member1", 400000)

    assert base_household.get_category_planned_amount("ocio") == 5000


def test_unbudgeted_income_detects_percentage_driven_overshoot(
    base_household: Household,
) -> None:
    """Bajar un sueldo puede hacer que lo presupuestado supere el ingreso.
    No lanza nada — se detecta como un número negativo."""
    member = Member("member1")
    member.monthly_income = 100000
    base_household.register_member(member)

    base_household.add_category("alquiler", participants=["member1"])
    base_household.set_planned_percentage("alquiler", 5000)  # 50%
    base_household.add_category("seguro", participants=["member1"])
    base_household.budget.set_planned_amount("seguro", 40000)  # fijo

    # alquiler 50% de 100000 = 50000; + seguro 40000 = 90000 presupuestado
    assert base_household.get_unbudgeted_income() == 10000

    base_household.set_member_income("member1", 60000)

    # alquiler 50% de 60000 = 30000; + seguro (sigue fijo) 40000 = 70000
    # presupuestado contra 60000 de ingreso
    assert base_household.get_unbudgeted_income() == -10000


# ====================================================
# TESTS: PLANNING - Planning Summary
# ====================================================


def test_get_planning_summary_basic(
    household_with_members_standard_categories: Household,
) -> None:
    """get_planning_summary retorna estructura completa"""
    _set_budget(household_with_members_standard_categories, "fijos", 300000)

    summary = SummaryService.get_planning_summary(
        household_with_members_standard_categories
    )

    assert isinstance(summary, dict)
    assert summary["members"] == ["member1", "member2"]
    assert summary["total_household_income"] == 300000

    assert summary["total_budgeted"] == 300000
    assert summary["missing_money"]["total"] == 0
    assert summary["debts"]["member1"] == 0
    assert summary["debts"]["member2"] == 0
    assert summary["saving_goals"]["member1"] == 0
    assert summary["saving_goals"]["member2"] == 0


def test_get_planning_summary_includes_distribution_method(
    household_with_members_standard_categories: Household,
) -> None:
    """get_planning_summary incluye método de distribución"""
    _set_budget(household_with_members_standard_categories, "fijos", 200000)

    summary = SummaryService.get_planning_summary(
        household_with_members_standard_categories
    )

    assert summary["distribution_method"] == MetodoReparto.EQUAL.value


def test_get_planning_summary_with_missing_money(
    household_with_members_standard_categories: Household,
) -> None:
    """reserva autocalcula: total_budgeted siempre == total_incomes cuando hay reserva"""
    _set_budget(household_with_members_standard_categories, "fijos", 200000)

    summary = SummaryService.get_planning_summary(
        household_with_members_standard_categories
    )

    # fijos=200000, reserva autocalcula=100000 → total=300000 == total_incomes
    assert summary["total_budgeted"] == 300000
    assert summary["missing_money"]["total"] == 100000


def test_get_planning_summary_includes_contributions_preview(
    household_with_members_standard_categories: Household,
) -> None:
    """get_planning_summary incluye preview de contribuciones"""
    _set_budget(
        household_with_members_standard_categories, "fijos", 200000
    )  # <= 300000 ingresos

    summary = SummaryService.get_planning_summary(
        household_with_members_standard_categories
    )

    assert "contributions_preview" in summary
    assert "fijos" in summary["contributions_preview"]
    contributions = summary["contributions_preview"]["fijos"]["contributions"]
    assert sum(contributions.values()) == 200000


def test_get_planning_summary_includes_debts(
    household_with_members_standard_categories: Household,
) -> None:
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    # reserva autocalcula a 150000

    summary = SummaryService.get_planning_summary(
        household_with_members_standard_categories
    )

    assert summary["missing_money"]["total"] == 150000


def test_get_planning_summary_raises_if_no_members(
    base_household_with_standard_cats: Household,
) -> None:
    """get_planning_summary lanza ValueError si no hay miembros"""
    with pytest.raises(ValueError, match="No hay miembros"):
        SummaryService.get_planning_summary(base_household_with_standard_cats)


def test_get_planning_summary_returns_negative_missing_money_when_over_budget(
    household_with_members_standard_categories: Household,
) -> None:
    """set_budget_for_category bloquea presupuesto que supere los ingresos"""
    # Ingresos totales: 300000 — intentar presupuestar 500000
    _set_budget(household_with_members_standard_categories, "fijos", 300000)
    with pytest.raises(ValueError):
        _set_budget(household_with_members_standard_categories, "variables", 200000)


def test_get_planning_summary_percentages_sum_to_10000(
    household_with_members_standard_categories: Household,
) -> None:
    """get_planning_summary percentages siempre suman 10000 (100%)"""
    _set_budget(
        household_with_members_standard_categories, "fijos", 200000
    )  # <= 300000 ingresos

    summary = SummaryService.get_planning_summary(
        household_with_members_standard_categories
    )

    total_pct = sum(summary["distribution_percentages"].values())
    assert total_pct == 10000


# ====================================================
# TESTS: Category management
# ====================================================


def test_add_category_creates_in_budget(
    household_with_members_standard_categories: Household,
) -> None:
    """add_category() agrega categoría al budget"""
    household_with_members_standard_categories.add_category(
        "educacion", ["member1", "member2"]
    )

    assert (
        "educacion"
        in household_with_members_standard_categories.get_active_categories()
    )


def test_add_category_rejects_a_participant_outside_the_household(
    household_with_members_standard_categories: Household,
) -> None:
    """Budget no conoce a los miembros; el hogar sí, y para aquí el error."""
    with pytest.raises(ValueError, match="no existe en el hogar"):
        household_with_members_standard_categories.add_category(
            "educacion", ["fulanito"]
        )


def test_remove_category_deletes_from_budget(
    base_household_with_standard_cats: Household,
) -> None:
    """remove_category() elimina categoría del budget"""
    base_household_with_standard_cats.remove_category("fijos")

    assert "fijos" not in base_household_with_standard_cats.get_active_categories()


def test_set_standard_categories_populates_budget(
    base_household_with_standard_cats: Household,
) -> None:
    """set_standard_categories() establece categorías en budget"""
    household = Household(
        Budget(), ExpenseTracker(), SavingBucketTracker(), DebtBucketTracker()
    )
    household.register_member(Member("Member1"))
    household.set_standard_categories()

    categories = household.get_active_categories()
    assert "fijos" in categories
    assert "variables" in categories
    assert "reserva" in categories


def test_get_active_categories_returns_list(
    base_household_with_standard_cats: Household,
) -> None:
    """get_active_categories() retorna lista de categorías"""
    categories = base_household_with_standard_cats.get_active_categories()

    assert isinstance(categories, list)
    assert len(categories) > 0


def test_get_category_budget_returns_amount(
    household_with_members_standard_categories: Household,
) -> None:
    """get_category_budget() retorna monto asignado"""
    _set_budget(household_with_members_standard_categories, "fijos", 100000)

    amount = household_with_members_standard_categories.get_category_planned_amount(
        "fijos"
    )
    assert amount == 100000


# ====================================================
# TESTS: get_incomes
# ====================================================


def test_get_incomes_returns_live_values(
    household_with_members_standard_categories: Household,
) -> None:
    """get_incomes() devuelve el ingreso vivo, sin depender de ningún congelado"""
    incomes = household_with_members_standard_categories.get_incomes()

    assert set(incomes) == set(household_with_members_standard_categories.members)
    assert all(isinstance(value, int) for value in incomes.values())


# ====================================================
# TESTS: Distribution method assignment
# ====================================================


def test_set_distribution_method_sets_method(
    household_with_members_standard_categories: Household,
) -> None:
    """set_distribution_method() establece método de reparto"""
    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )

    assert household_with_members_standard_categories.method == MetodoReparto.EQUAL


def test_set_distribution_method_changes_percentages(
    household_with_members_standard_categories: Household,
) -> None:
    """set_distribution_method() cambia los porcentajes de contribución"""
    pct_proportional = (
        household_with_members_standard_categories.get_percentages_by_method(
            MetodoReparto.PROPORTIONAL
        )
    )

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    pct_equal = household_with_members_standard_categories.get_percentages_by_method(
        MetodoReparto.EQUAL
    )

    assert pct_proportional != pct_equal


# ====================================================
# TESTS: Coordinación Budget vs ExpenseTracker (MONTH phase)
# ====================================================


def test_register_expense_adds_to_tracker(
    household_with_members_standard_categories: Household,
) -> None:
    """register_expense() almacena en ExpenseTracker"""

    _set_budget(household_with_members_standard_categories, "fijos", 100000)

    expense = Expense(
        "member1", make_category("fijos"), 25000, ["member1"], "Test expense"
    )
    household_with_members_standard_categories.register_expense(expense)

    assert len(household_with_members_standard_categories.expense_tracker.expenses) == 1
    assert (
        household_with_members_standard_categories.expense_tracker.expenses[0]
        == expense
    )


def test_register_expense_validates_member_exists(
    household_with_members_standard_categories: Household,
) -> None:
    """register_expense() valida que el miembro existe"""

    _set_budget(household_with_members_standard_categories, "fijos", 100000)

    expense = Expense("NonExistent", make_category("fijos"), 25000, ["nonexistent"])

    with pytest.raises(ValueError, match="no existe en el hogar"):
        household_with_members_standard_categories.register_expense(expense)


def test_register_expense_validates_category_exists(
    household_with_members_standard_categories: Household,
) -> None:
    """register_expense() valida que la categoría existe"""

    expense = Expense("member1", make_category("nonexistent"), 25000, ["member1"])

    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_members_standard_categories.register_expense(expense)


def test_get_category_spent_returns_zero_when_no_expenses(
    household_with_members_standard_categories: Household,
) -> None:
    """get_category_spent() retorna 0 cuando no hay gastos"""
    _set_budget(household_with_members_standard_categories, "fijos", 100000)

    spent = household_with_members_standard_categories.get_category_spent("fijos")

    assert spent == 0


def test_get_category_spent_sums_expenses_for_category(
    household_with_members_standard_categories: Household,
) -> None:
    """get_category_spent() suma gastos de una categoría"""

    _set_budget(household_with_members_standard_categories, "fijos", 100000)

    expense1 = Expense("member1", make_category("fijos"), 25000, ["member1"])
    expense2 = Expense("member2", make_category("fijos"), 15000, ["member2"])
    household_with_members_standard_categories.register_expense(expense1)
    household_with_members_standard_categories.register_expense(expense2)

    spent = household_with_members_standard_categories.get_category_spent("fijos")

    assert spent == 40000


def test_get_category_spent_only_counts_matching_category(
    household_with_members_standard_categories: Household,
) -> None:
    """get_category_spent() solo cuenta gastos de la categoría solicitada"""

    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)

    expense1 = Expense("member1", make_category("fijos"), 25000, ["member1"])
    expense2 = Expense("member2", make_category("variables"), 15000, ["member2"])
    household_with_members_standard_categories.register_expense(expense1)
    household_with_members_standard_categories.register_expense(expense2)

    spent_fijos = household_with_members_standard_categories.get_category_spent("fijos")

    assert spent_fijos == 25000


def test_get_total_spent_returns_zero_when_no_expenses(
    household_with_members_standard_categories: Household,
) -> None:
    """get_total_spent() retorna 0 cuando no hay gastos"""
    _set_budget(household_with_members_standard_categories, "fijos", 100000)

    total_spent = household_with_members_standard_categories.get_total_spent()

    assert total_spent == 0


def test_get_total_spent_sums_all_expenses(
    household_with_members_standard_categories: Household,
) -> None:
    """get_total_spent() suma todos los gastos de todas las categorías"""

    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)

    expense1 = Expense("member1", make_category("fijos"), 25000, ["member1"])
    expense2 = Expense("member2", make_category("variables"), 15000, ["member2"])
    expense3 = Expense("member1", make_category("fijos"), 10000, ["member1"])
    household_with_members_standard_categories.register_expense(expense1)
    household_with_members_standard_categories.register_expense(expense2)
    household_with_members_standard_categories.register_expense(expense3)

    total_spent = household_with_members_standard_categories.get_total_spent()

    assert total_spent == 50000


def test_get_category_remaining_when_no_expenses(
    household_with_members_standard_categories: Household,
) -> None:
    """get_category_remaining() retorna presupuesto completo si no hay gastos"""
    _set_budget(household_with_members_standard_categories, "fijos", 100000)

    remaining = household_with_members_standard_categories.get_category_remaining(
        "fijos"
    )

    assert remaining == 100000


def test_get_category_remaining_calculates_correctly(
    household_with_members_standard_categories: Household,
) -> None:
    """get_category_remaining() calcula presupuesto - gastado correctamente"""

    _set_budget(household_with_members_standard_categories, "fijos", 100000)

    expense = Expense("member1", make_category("fijos"), 25000, ["member1"])
    household_with_members_standard_categories.register_expense(expense)

    remaining = household_with_members_standard_categories.get_category_remaining(
        "fijos"
    )

    assert remaining == 75000


def test_get_category_remaining_can_be_negative(
    household_with_members_standard_categories: Household,
) -> None:
    """get_category_remaining() puede ser negativo (sobregasto)"""

    _set_budget(household_with_members_standard_categories, "fijos", 100000)

    expense = Expense("member1", make_category("fijos"), 150000, ["member1"])
    household_with_members_standard_categories.register_expense(expense)

    remaining = household_with_members_standard_categories.get_category_remaining(
        "fijos"
    )

    assert remaining == -50000


def test_get_total_remaining_when_no_expenses(
    household_with_members_standard_categories: Household,
) -> None:
    """get_total_remaining() retorna presupuesto total si no hay gastos"""
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    # reserva autocalcula a 150000 → total_budgeted = 300000

    total_remaining = household_with_members_standard_categories.get_total_remaining()

    assert total_remaining == 300000


def test_get_total_remaining_calculates_correctly(
    household_with_members_standard_categories: Household,
) -> None:
    """get_total_remaining() calcula total presupuestado - total gastado"""

    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    # total_budgeted = 300000

    expense1 = Expense("member1", make_category("fijos"), 25000, ["member1"])
    expense2 = Expense("member2", make_category("variables"), 10000, ["member2"])
    household_with_members_standard_categories.register_expense(expense1)
    household_with_members_standard_categories.register_expense(expense2)

    total_remaining = household_with_members_standard_categories.get_total_remaining()

    assert total_remaining == 265000


def test_get_total_remaining_can_be_negative(
    household_with_members_standard_categories: Household,
) -> None:
    """get_total_remaining() puede ser negativo si gastos superan presupuesto"""

    _set_budget(household_with_members_standard_categories, "fijos", 50000)
    # total_budgeted = 300000 (reserva autocalcula a 250000)

    expense = Expense("member1", make_category("fijos"), 350000, ["member1"])
    household_with_members_standard_categories.register_expense(expense)

    total_remaining = household_with_members_standard_categories.get_total_remaining()

    assert total_remaining == -50000


# ====================================================
# TESTS: get_missing_money
# ====================================================


def test_get_missing_money_raises_when_over_budget(
    household_with_members_standard_categories: Household,
) -> None:
    """set_budget_for_category bloquea presupuesto que supere los ingresos"""
    with pytest.raises(ValueError):
        _set_budget(household_with_members_standard_categories, "fijos", 350000)


# ====================================================
# TESTS: get_member_owed_total()
# ====================================================


def test_get_member_owed_total_sums_all_category_contributions(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe sumar todas las contribuciones acordadas del miembro"""
    household_with_members_standard_categories.set_distribution_method(
        method=MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 60000)
    _set_budget(household_with_members_standard_categories, "variables", 40000)
    # reserva autocalcula a 200000 → total = 300000 → EQUAL → 150000 por miembro
    household_with_members_standard_categories.freeze_planning_state()

    owed = household_with_members_standard_categories.get_member_owed_total("member1")

    assert owed == 150000


def test_get_member_owed_total_normalizes_name(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe normalizar el nombre del miembro"""
    household_with_members_standard_categories.set_distribution_method(
        method=MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 60000)
    # reserva autocalcula a 240000 → total = 300000 → EQUAL → 150000 por miembro
    household_with_members_standard_categories.freeze_planning_state()

    owed = household_with_members_standard_categories.get_member_owed_total("MEMBER1")

    assert owed == 150000


def test_get_member_owed_total_raises_if_member_not_exists(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe fallar si el miembro no existe"""
    with pytest.raises(ValueError, match="no existe en el hogar"):
        household_with_members_standard_categories.get_member_owed_total("member3")


# ====================================================
# TESTS: get_member_balance()
# ====================================================


def test_get_member_balance_negative_when_owes_money(
    household_with_members_standard_categories: Household,
) -> None:
    """Balance negativo cuando el miembro debe dinero (paid < owed)"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    # reserva=200000 → total=300000 → EQUAL → owed=150000
    household_with_members_standard_categories.freeze_planning_state()

    expense = Expense(
        "member1", make_category("fijos"), 20000, ["member1"], "Pago parcial"
    )
    household_with_members_standard_categories.register_expense(expense)

    balance = household_with_members_standard_categories.get_member_balance("member1")

    # Balance = paid - owed = 20000 - 150000 = -130000
    assert balance == -130000


def test_get_member_balance_positive_when_paid_more(
    household_with_members_standard_categories: Household,
) -> None:
    """Balance positivo cuando el miembro pagó de más (paid > owed)"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    # reserva=200000 → total=300000 → EQUAL → owed=150000
    household_with_members_standard_categories.freeze_planning_state()

    expense = Expense(
        "member1", make_category("fijos"), 200000, ["member1"], "Pagó de más"
    )
    household_with_members_standard_categories.register_expense(expense)

    balance = household_with_members_standard_categories.get_member_balance("member1")

    # Balance = paid - owed = 200000 - 150000 = +50000
    assert balance == 50000


def test_get_member_balance_zero_when_paid_exact(
    household_with_members_standard_categories: Household,
) -> None:
    """Balance cero cuando el miembro pagó exactamente lo acordado"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    # reserva=200000 → total=300000 → EQUAL → owed=150000
    household_with_members_standard_categories.freeze_planning_state()

    expense = Expense(
        "member1", make_category("fijos"), 150000, ["member1"], "Pagó exacto"
    )
    household_with_members_standard_categories.register_expense(expense)

    balance = household_with_members_standard_categories.get_member_balance("member1")

    assert balance == 0


def test_get_member_balance_normalizes_name(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe normalizar el nombre del miembro"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    # reserva=200000 → total=300000 → EQUAL → owed=150000
    household_with_members_standard_categories.freeze_planning_state()

    expense = Expense("member1", make_category("fijos"), 150000, ["member1"])
    household_with_members_standard_categories.register_expense(expense)

    balance = household_with_members_standard_categories.get_member_balance("MEMBER1")

    assert balance == 0


def test_get_member_balance_raises_if_member_not_exists(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe fallar si el miembro no existe"""
    with pytest.raises(ValueError, match="no existe en el hogar"):
        household_with_members_standard_categories.get_member_balance("member3")


# ====================================================
# TESTS: get_member_status()
# ====================================================


def test_get_member_status_returns_complete_structure(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe retornar dict con: income, owed, paid, balance, debt, saving_goal, by_category"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    # reserva=150000 → total=300000 → EQUAL → owed=150000
    household_with_members_standard_categories.freeze_planning_state()

    expense1 = Expense("member1", make_category("fijos"), 30000, ["member1"])
    expense2 = Expense("member1", make_category("variables"), 10000, ["member1"])
    household_with_members_standard_categories.register_expense(expense1)
    household_with_members_standard_categories.register_expense(expense2)

    status = SummaryService.get_member_status(
        household_with_members_standard_categories, "member1"
    )

    assert "income" in status
    assert "owed" in status
    assert "paid" in status
    assert "balance" in status
    assert "debt" in status
    assert "saving_goal" in status
    assert "by_category" in status

    assert status["income"] == 200000
    assert status["owed"] == 150000
    assert status["paid"] == 40000
    assert status["balance"] == -110000
    assert status["debt"] == 0
    assert status["saving_goal"] == 0


def test_get_member_status_paid_is_total_not_per_category(
    household_with_members_standard_categories: Household,
) -> None:
    """CRÍTICO: 'paid' debe ser el total pagado, NO el paid de una categoría"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 60000)
    _set_budget(household_with_members_standard_categories, "variables", 40000)
    # reserva autocalcula
    household_with_members_standard_categories.freeze_planning_state()

    expense1 = Expense("member1", make_category("fijos"), 20000, ["member1"])
    expense2 = Expense("member1", make_category("variables"), 15000, ["member1"])
    expense3 = Expense(
        "member1",
        make_category("reserva", auto_calculated=True),
        5000,
        ["member1"],
    )
    household_with_members_standard_categories.register_expense(expense1)
    household_with_members_standard_categories.register_expense(expense2)
    household_with_members_standard_categories.register_expense(expense3)

    status = SummaryService.get_member_status(
        household_with_members_standard_categories, "member1"
    )

    # 'paid' debe ser la SUMA de todos los gastos (20000+15000+5000=40000)
    assert status["paid"] == 40000


def test_get_member_status_by_category_has_correct_structure(
    household_with_members_standard_categories: Household,
) -> None:
    """'by_category' debe tener contribution, paid, remaining por categoría"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    household_with_members_standard_categories.freeze_planning_state()

    expense1 = Expense("member1", make_category("fijos"), 30000, ["member1"])
    expense2 = Expense("member1", make_category("variables"), 10000, ["member1"])
    household_with_members_standard_categories.register_expense(expense1)
    household_with_members_standard_categories.register_expense(expense2)

    status = SummaryService.get_member_status(
        household_with_members_standard_categories, "member1"
    )
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


def test_get_member_status_normalizes_name(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe normalizar el nombre del miembro"""
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    household_with_members_standard_categories.freeze_planning_state()

    status = SummaryService.get_member_status(
        household_with_members_standard_categories, "MEMBER1"
    )

    assert status["income"] == 200000


def test_get_member_status_includes_debt_and_saving_goal(
    household_with_members_standard_categories: Household,
) -> None:
    """debt y saving_goal (derivado de las metas con deadline, informativo) reflejan
    lo declarado en PLANNING"""
    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    # reserva autocalcula a 200000 → capacity per member = 100000
    _add_debt(household_with_members_standard_categories, "member1", 20000)
    # deadline dentro del mes actual -> months_until_deadline == 1 -> required == goal
    _add_saving_bucket(
        household_with_members_standard_categories,
        "member1",
        goal_cents=30000,
        deadline=datetime.now(),
    )
    household_with_members_standard_categories.freeze_planning_state()

    status = SummaryService.get_member_status(
        household_with_members_standard_categories, "member1"
    )

    assert status["debt"] == 20000
    assert status["saving_goal"] == 30000


def test_get_member_status_raises_if_member_not_exists(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe fallar si el miembro no existe"""
    with pytest.raises(ValueError, match="no existe en el hogar"):
        SummaryService.get_member_status(
            household_with_members_standard_categories, "member3"
        )


# ====================================================
# TESTS: get_month_summary()
# ====================================================


def test_get_month_summary_returns_complete_structure(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe retornar dict con 'totals' y 'by_category'"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    household_with_members_standard_categories.freeze_planning_state()

    expense = Expense("member1", make_category("fijos"), 30000, ["member1"])
    household_with_members_standard_categories.register_expense(expense)

    summary = SummaryService.get_month_summary(
        household_with_members_standard_categories
    )

    assert "totals" in summary
    assert "by_category" in summary

    assert "total_budgeted" in summary["totals"]
    assert "total_spent" in summary["totals"]
    assert "total_remaining" in summary["totals"]


def test_get_month_summary_includes_missing_money(
    household_with_members_standard_categories: Household,
) -> None:
    """'missing_money' debe estar presente en el summary"""
    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 200000)
    # reserva autocalcula a 100000 → total = 300000 → missing = 0
    household_with_members_standard_categories.freeze_planning_state()

    summary = SummaryService.get_month_summary(
        household_with_members_standard_categories
    )

    assert "missing_money" in summary
    assert summary["missing_money"]["total"] == 100000


def test_get_month_summary_calculates_correctly(
    household_with_members_standard_categories: Household,
) -> None:
    """Los cálculos de 'totals' deben ser correctos"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    # reserva=150000 → total_budgeted=300000
    household_with_members_standard_categories.freeze_planning_state()

    expense1 = Expense("member1", make_category("fijos"), 30000, ["member1"])
    expense2 = Expense("member2", make_category("variables"), 20000, ["member2"])
    household_with_members_standard_categories.register_expense(expense1)
    household_with_members_standard_categories.register_expense(expense2)

    summary = SummaryService.get_month_summary(
        household_with_members_standard_categories
    )

    assert summary["totals"]["total_budgeted"] == 300000
    assert summary["totals"]["total_spent"] == 50000
    assert summary["totals"]["total_remaining"] == 250000


def test_get_month_summary_by_category_has_correct_structure(
    household_with_members_standard_categories: Household,
) -> None:
    """Cada raíz en 'by_category' lleva ceiling, spent, remaining, billable y children"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    household_with_members_standard_categories.freeze_planning_state()

    expense = Expense("member1", make_category("fijos"), 25000, ["member1"])
    household_with_members_standard_categories.register_expense(expense)

    summary = SummaryService.get_month_summary(
        household_with_members_standard_categories
    )
    by_category = summary["by_category"]

    assert "fijos" in by_category
    assert "variables" in by_category

    assert set(by_category["fijos"]) == {
        "ceiling",
        "spent",
        "remaining",
        "billable",
        "children",
    }

    assert by_category["fijos"]["ceiling"] == 100000
    assert by_category["fijos"]["spent"] == 25000
    assert by_category["fijos"]["remaining"] == 75000
    assert by_category["fijos"]["billable"] == 100000
    assert by_category["fijos"]["children"] == {}

    assert by_category["variables"]["ceiling"] == 50000
    assert by_category["variables"]["spent"] == 0
    assert by_category["variables"]["remaining"] == 50000


def test_get_month_summary_nests_children_under_their_root(
    household_with_members_standard_categories: Household,
) -> None:
    """Las hijas viven dentro de 'children' y no ensucian el primer nivel"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    household_with_members_standard_categories.add_category("alquiler", parent="fijos")
    _set_budget(household_with_members_standard_categories, "alquiler", 80000)
    household_with_members_standard_categories.freeze_planning_state()

    expense = Expense(
        "member1",
        household_with_members_standard_categories.budget.get_category("alquiler"),
        80000,
        ["member1"],
    )
    household_with_members_standard_categories.register_expense(expense)

    by_category = SummaryService.get_month_summary(
        household_with_members_standard_categories
    )["by_category"]

    assert "alquiler" not in by_category
    assert by_category["fijos"]["children"]["alquiler"]["spent"] == 80000

    # El gasto de la hija cuenta contra el techo del padre
    assert by_category["fijos"]["spent"] == 80000
    assert by_category["fijos"]["remaining"] == 20000
    assert by_category["fijos"]["billable"] == 20000


def test_get_month_summary_by_category_matches_totals(
    household_with_members_standard_categories: Household,
) -> None:
    """Sumar el primer nivel cuadra con los totales: nada se cuenta dos veces"""

    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    household_with_members_standard_categories.add_category("alquiler", parent="fijos")
    _set_budget(household_with_members_standard_categories, "alquiler", 80000)
    household_with_members_standard_categories.freeze_planning_state()

    expense = Expense(
        "member1",
        household_with_members_standard_categories.budget.get_category("alquiler"),
        80000,
        ["member1"],
    )
    household_with_members_standard_categories.register_expense(expense)

    summary = SummaryService.get_month_summary(
        household_with_members_standard_categories
    )
    by_category = summary["by_category"]

    assert (
        sum(row["ceiling"] for row in by_category.values())
        == (summary["totals"]["total_budgeted"])
    )
    assert (
        sum(row["spent"] for row in by_category.values())
        == (summary["totals"]["total_spent"])
    )


# ====================================================
# TESTS: get_agreed_percentages() y get_agreed_contributions()
# ====================================================


def test_get_agreed_percentages_raises_if_not_frozen(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe fallar si finish_planning() no ha sido llamado"""
    household_with_members_standard_categories.prepare_period()

    with pytest.raises(ValueError, match="Los porcentajes no han sido congelados"):
        household_with_members_standard_categories.get_agreed_percentages()


def test_get_agreed_percentages_returns_frozen_percentages(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe retornar los porcentajes congelados después de finish_planning()"""
    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.PROPORTIONAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    household_with_members_standard_categories.freeze_planning_state()

    percentages = household_with_members_standard_categories.get_agreed_percentages()

    assert "member1" in percentages
    assert "member2" in percentages
    assert percentages["member1"] == 6667
    assert percentages["member2"] == 3333


def test_get_agreed_contributions_raises_if_not_frozen(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe fallar si finish_planning() no ha sido llamado"""
    household_with_members_standard_categories.prepare_period()

    with pytest.raises(ValueError, match="Las contribuciones no han sido congeladas"):
        household_with_members_standard_categories.get_agreed_contributions()


def test_get_agreed_contributions_returns_frozen_contributions(
    household_with_members_standard_categories: Household,
) -> None:
    """Debe retornar las contribuciones congeladas después de finish_planning()"""
    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    household_with_members_standard_categories.prepare_period()
    _set_budget(household_with_members_standard_categories, "fijos", 100000)
    _set_budget(household_with_members_standard_categories, "variables", 50000)
    household_with_members_standard_categories.freeze_planning_state()

    contributions = (
        household_with_members_standard_categories.get_agreed_contributions()
    )

    assert "fijos" in contributions
    assert "variables" in contributions
    assert contributions["fijos"]["member1"] == 50000
    assert contributions["fijos"]["member2"] == 50000
    assert contributions["variables"]["member1"] == 25000
    assert contributions["variables"]["member2"] == 25000


# ====================================================
# TESTS: get_budget_as_percentage
# ====================================================


def test_get_budget_as_percentage_basic(
    household_with_members_standard_categories: Household,
) -> None:
    """Retorna porcentaje correcto del presupuesto sobre ingresos"""
    # Ingresos: 300000, Presupuesto: 150000 → 50% = 5000 basis
    _set_budget(household_with_members_standard_categories, "fijos", 150000)

    pct_basis = household_with_members_standard_categories.get_budget_as_percentage(
        "fijos"
    )

    assert pct_basis == 5000  # 50%


def test_get_budget_as_percentage_zero_budget(
    household_with_members_standard_categories: Household,
) -> None:
    """Retorna 0 cuando el presupuesto de categoría es 0"""
    _set_budget(household_with_members_standard_categories, "variables", 0)

    pct_basis = household_with_members_standard_categories.get_budget_as_percentage(
        "variables"
    )

    assert pct_basis == 0


def test_get_budget_as_percentage_full_budget(
    household_with_members_standard_categories: Household,
) -> None:
    """Retorna 10000 (100%) cuando presupuesto de categoría = ingresos totales"""
    # Ingresos totales: 300000
    _set_budget(household_with_members_standard_categories, "fijos", 300000)

    pct_basis = household_with_members_standard_categories.get_budget_as_percentage(
        "fijos"
    )

    assert pct_basis == 10000  # 100%


def test_get_budget_as_percentage_fractional_result(
    household_with_members_standard_categories: Household,
) -> None:
    """Maneja correctamente resultados fraccionarios con floor division"""
    # 100000 / 300000 = 0.33333... → (100000 * 10000) // 300000 = 3333 basis
    _set_budget(household_with_members_standard_categories, "variables", 100000)

    pct_basis = household_with_members_standard_categories.get_budget_as_percentage(
        "variables"
    )

    assert pct_basis == 3333  # 33.33%


def test_get_budget_as_percentage_nonexistent_category(
    household_with_members_standard_categories: Household,
) -> None:
    """Lanza error si la categoría no existe"""
    with pytest.raises(ValueError, match="debe estar creada"):
        household_with_members_standard_categories.get_budget_as_percentage(
            "categoria_falsa"
        )


def test_get_budget_as_percentage_roundtrip_consistency(
    household_with_members_standard_categories: Household,
) -> None:
    """set + get debe ser consistente (considerando floor division)"""
    _set_budget(
        household_with_members_standard_categories, "fijos", 150000
    )  # 50% de 300000
    retrieved_pct = household_with_members_standard_categories.get_budget_as_percentage(
        "fijos"
    )

    assert retrieved_pct == 5000


def test_set_budget_by_percentages_sum_matches_incomes(
    base_household_with_standard_cats: Household,
) -> None:
    """set_budget_by_percentages: sin pérdida de céntimos con ingresos no redondos"""
    m = Member("solo")
    m.monthly_income = 100001
    base_household_with_standard_cats.register_member(m)
    base_household_with_standard_cats.prepare_period()

    # fijos=50%, variables=30%, reserva=20% — deben sumar exactamente 100001¢
    _set_budget_by_percentages(
        base_household_with_standard_cats,
        {"fijos": 5000, "variables": 3000, "reserva": 2000},
    )

    fijos = base_household_with_standard_cats.get_category_planned_amount("fijos")
    variables = base_household_with_standard_cats.get_category_planned_amount(
        "variables"
    )
    reserva = base_household_with_standard_cats.get_category_planned_amount("reserva")

    assert fijos + variables + reserva == 100001
    # Largest remainder asigna el céntimo extra a fijos (mayor resto: 0.5)
    assert fijos == 50001
    assert variables == 30000
    assert reserva == 20000


# ====================================================
# TESTS: Savings y Loose Money
# ====================================================


def test_deposit_to_saving_bucket_updates_balance(
    household_with_members_standard_categories: Household,
) -> None:
    """Test: depositar en un bucket de ahorro actualiza su balance"""
    household_with_members_standard_categories.prepare_period()
    bucket_id = _add_saving_bucket(
        household_with_members_standard_categories, "member1"
    )

    household_with_members_standard_categories.deposit_to_saving_bucket(
        bucket_id, "member1", 5000
    )

    bucket = household_with_members_standard_categories.get_bucket_by_id(bucket_id)
    assert bucket.balance == 5000


def test_withdraw_from_saving_bucket_reduces_balance(
    household_with_members_standard_categories: Household,
) -> None:
    """Test: retirar de un bucket de ahorro reduce su balance"""
    household_with_members_standard_categories.prepare_period()
    bucket_id = _add_saving_bucket(
        household_with_members_standard_categories, ["member1", "member2"]
    )
    household_with_members_standard_categories.deposit_to_saving_bucket(
        bucket_id, "member1", 10000
    )

    household_with_members_standard_categories.withdraw_from_bucket(
        bucket_id, "member1", 4000
    )

    bucket = household_with_members_standard_categories.get_bucket_by_id(bucket_id)
    assert bucket.balance == 6000


def test_get_reserve_contribution_by_member_with_equal_method(
    household_with_members_standard_categories: Household,
) -> None:
    """Reserva (100000, sobre total 300000) se reparte EQUAL entre los 2 miembros"""
    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.EQUAL
    )
    _set_budget(household_with_members_standard_categories, "fijos", 200000)
    # reserva autocalcula a 100000 → EQUAL → 50000 cada uno

    share_m1 = (
        household_with_members_standard_categories.get_reserve_contribution_by_member(
            "member1"
        )
    )
    share_m2 = (
        household_with_members_standard_categories.get_reserve_contribution_by_member(
            "member2"
        )
    )

    assert share_m1 == 50000
    assert share_m2 == 50000


def test_get_reserve_contribution_by_member_with_custom_method(
    household_with_members_standard_categories: Household,
) -> None:
    """Reserva (100000) se reparte según los splits CUSTOM (70/30)"""
    household_with_members_standard_categories.set_custom_splits(
        {"member1": 7000, "member2": 3000}
    )
    household_with_members_standard_categories.set_distribution_method(
        MetodoReparto.CUSTOM
    )
    _set_budget(household_with_members_standard_categories, "fijos", 200000)
    # reserva autocalcula a 100000 → CUSTOM 70/30 → 70000 / 30000

    share_m1 = (
        household_with_members_standard_categories.get_reserve_contribution_by_member(
            "member1"
        )
    )
    assert share_m1 == 70000


# ====================================================
# TESTS: validate_debt_doesnt_exceed_capacity
# ====================================================


def test_validate_debt_doesnt_exceed_capacity_passes_within_reserva(
    household_with_members_standard_categories: Household,
) -> None:
    """Deuda dentro de la parte de reserva no lanza. El ahorro no se valida —
    es elección, no obligación (T5/T6)."""
    # fijos=180000, variables=0 → reserva autocalcula = 300000 - 180000 = 120000
    # EQUAL: 120000 / 2 = 60000 por miembro
    _set_budget(household_with_members_standard_categories, "fijos", 180000)
    _add_debt(household_with_members_standard_categories, "member1", 50000)

    # 50000 <= 60000 → OK
    household_with_members_standard_categories.validate_debt_doesnt_exceed_capacity()


def test_validate_debt_doesnt_exceed_capacity_raises_when_exceeds_reserva(
    household_with_members_standard_categories: Household,
) -> None:
    """Deuda mayor que la parte de reserva del miembro lanza ValueError"""
    # fijos=180000, variables=0 → reserva autocalcula = 300000 - 180000 = 120000
    # EQUAL: 120000 / 2 = 60000 por miembro
    _set_budget(household_with_members_standard_categories, "fijos", 180000)
    _add_debt(household_with_members_standard_categories, "member1", 70000)

    # 70000 > 60000 → lanza
    with pytest.raises(ValueError, match="member1"):
        household_with_members_standard_categories.validate_debt_doesnt_exceed_capacity()


def test_validate_debt_doesnt_exceed_capacity_no_reserva_raises_if_debt(
    household_with_members_standard_categories: Household,
) -> None:
    """Sin categoría reserva, cualquier deuda supera capacidad 0"""
    _add_debt(household_with_members_standard_categories, "member1", 1)

    with pytest.raises(ValueError, match="member1"):
        household_with_members_standard_categories.validate_debt_doesnt_exceed_capacity()


def test_validate_debt_doesnt_exceed_capacity_ignores_missing_money(
    household_with_members_standard_categories: Household,
) -> None:
    """Sin reserva (fijos == total_incomes), cualquier deuda supera capacidad"""
    # fijos=total_incomes → reserva=0 → capacidad=0 por miembro
    _set_budget(household_with_members_standard_categories, "fijos", 300000)
    _add_debt(household_with_members_standard_categories, "member1", 1)

    with pytest.raises(ValueError, match="member1"):
        household_with_members_standard_categories.validate_debt_doesnt_exceed_capacity()


# ====================================================
# TESTS: register_debt_payment y get_debt_status
# ====================================================


@pytest.fixture
def household_month_ready(
    household_with_members_standard_categories: Household,
) -> Household:
    """Household con registration congelado y reserva presupuestada.
    EQUAL, reserva=120000 → 60000 por miembro. Listo para declarar deuda y pagar."""
    household_with_members_standard_categories.prepare_period()
    # fijos=180000, variables=0 → reserva = 300000 - 180000 = 120000
    _set_budget(household_with_members_standard_categories, "fijos", 180000)
    return household_with_members_standard_categories


def test_register_debt_payment_basic(household_month_ready: Household) -> None:
    """Pago de deuda se registra y get_debt_status refleja paid correcto"""
    hh = household_month_ready
    bid = _add_debt(hh, "member1", 50000)

    hh.register_debt_payment("member1", 20000, bid)

    totals = hh.get_debt_status_by_member("member1", _WIDE_START, _WIDE_END)["totals"]
    assert totals["committed"] == 50000
    assert totals["paid"] == 20000
    assert totals["remaining"] == 30000


def test_register_debt_payment_overpayment_allowed(
    household_month_ready: Household,
) -> None:
    """Sobrepago permitido (decisión T1): el backend no bloquea pagos > cuota."""
    hh = household_month_ready
    bid = _add_debt(hh, "member1", 50000)

    hh.register_debt_payment("member1", 60000, bid)

    totals = hh.get_debt_status_by_member("member1", _WIDE_START, _WIDE_END)["totals"]
    assert totals["paid"] == 60000


def test_get_debt_status_after_partial_payment(
    household_month_ready: Household,
) -> None:
    """Pago parcial: remaining = committed - paid"""
    hh = household_month_ready
    bid = _add_debt(hh, "member1", 50000)

    hh.register_debt_payment("member1", 20000, bid)

    totals = hh.get_debt_status_by_member("member1", _WIDE_START, _WIDE_END)["totals"]
    assert totals == {"committed": 50000, "paid": 20000, "remaining": 30000}


def test_get_debt_status_after_full_payment(household_month_ready: Household) -> None:
    """Pago completo de la cuota del período: remaining == 0"""
    hh = household_month_ready
    bid = _add_debt(hh, "member1", 50000)

    hh.register_debt_payment("member1", 50000, bid)

    totals = hh.get_debt_status_by_member("member1", _WIDE_START, _WIDE_END)["totals"]
    assert totals["paid"] == 50000
    assert totals["remaining"] == 0


# ====================================================
# TESTS: get_saving_status
# ====================================================


def test_get_saving_status_after_deposit(household_month_ready: Household) -> None:
    """Depósito de ahorro en MONTH se refleja en get_saving_status. required_this_month
    es informativo (deriva de goal+deadline), no un compromiso declarado."""
    hh = household_month_ready
    bucket_id = _add_saving_bucket(
        hh, "member1", goal_cents=50000, deadline=datetime.now()
    )
    hh.freeze_planning_state()

    hh.deposit_to_saving_bucket(bucket_id, "member1", 30000)

    status = hh.get_saving_status_by_member("member1", _WIDE_START, _WIDE_END)
    bucket_status = status["buckets"][bucket_id]

    # required_this_month es un cálculo en vivo sobre el saldo actual, no el
    # snapshot de antes del depósito: tras depositar 30000 de una meta de
    # 50000, faltan 20000 — el "print" ya lo refleja.
    assert bucket_status["required_this_month"] == 20000
    assert bucket_status["paid_this_period"] == 30000
    assert status["totals"]["paid_this_period"] == 30000
