import pytest
from src.models.participante import Participante
from src.models.household import Household


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
    from src.models.budget import Budget

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
