"""
Tests de edge cases extremos para el sistema de cálculo de contribuciones.

Estos tests documentan casos límite que pueden causar:
- Que un miembro exceda su ingreso
- Errores acumulados de redondeo
- Descuadres entre presupuesto y contribuciones
- Pérdida de céntimos

Estado actual: MUCHOS FALLARÁN - están diseñados para exponer bugs.
"""

import pytest
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.member import Member
from src.models.constants import MetodoReparto


# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def household_base():
    b = Budget()
    e = ExpenseTracker()
    b.set_standard_categories()
    return Household(budget=b, expense_tracker=e)


# ====================================================
# EDGE CASE 1: Redondeo extremo con proporciones 2:1
# ====================================================


def test_edge_case_proportional_2_to_1_full_budget(household_base):
    """
    Caso extremo: Ingresos 2000:1000 (2:1), presupuesto 100% (3000€).

    Problema esperado:
    - Amanda: 66.66% → debe aportar 2000€ exacto
    - Cada categoría asigna su resto a Amanda
    - Acumulación de restos → Amanda excede su ingreso

    Invariantes que DEBEN cumplirse:
    1. sum(contributions por miembro) <= ingreso del miembro
    2. sum(contributions por categoría) == budget de categoría
    3. sum(todas contributions) == budget total
    """
    # Setup: 2 miembros, ratio 2:1
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 200000  # 2000€
    m2.monthly_income = 100000  # 1000€
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    # Presupuesto 100% de ingresos (3000€) en 3 categorías
    household_base.set_budget_for_category("fijos", 150000)  # 1500€
    household_base.set_budget_for_category("variables", 90000)  # 900€
    household_base.set_budget_for_category("deuda/ahorro", 60000)  # 600€
    # Total: 3000€ = 100% de ingresos

    # Calcular contribuciones
    contributions = household_base.get_current_contributions()

    # VALIDACIÓN 1: Nadie excede su ingreso
    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )
    heri_total = sum(
        contributions[cat]["contributions"]["heri"] for cat in contributions
    )

    assert amanda_total <= 200000, (
        f"Amanda debe aportar {amanda_total}¢ pero solo gana 200000¢. "
        f"Exceso: {amanda_total - 200000}¢"
    )
    assert heri_total <= 100000, (
        f"Heri debe aportar {heri_total}¢ pero solo gana 100000¢"
    )

    # VALIDACIÓN 2: Suma por categoría debe ser exacta
    for cat_name, cat_data in contributions.items():
        expected = household_base.get_category_budget(cat_name)
        actual = sum(cat_data["contributions"].values())
        assert actual == expected, (
            f"Categoría {cat_name}: expected {expected}¢, got {actual}¢. "
            f"Diferencia: {actual - expected}¢"
        )

    # VALIDACIÓN 3: Suma global debe ser exacta
    total_contributions = amanda_total + heri_total
    total_budget = 300000
    assert total_contributions == total_budget, (
        f"Total contributions: {total_contributions}¢, budget: {total_budget}¢. "
        f"Diferencia: {total_contributions - total_budget}¢"
    )


def test_edge_case_proportional_99_to_1_extreme_imbalance(household_base):
    """
    Caso extremo: Ingresos ultra desbalanceados (99:1).

    Amanda gana 2970€, Heri gana 30€ (1%) del total 3000€.
    Presupuesto 100% distribuido en 5 categorías.

    Problema: Con 5 categorías, Amanda recibe 5 restos → mayor probabilidad
    de exceder su ingreso.
    """
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 297000  # 2970€ (99%)
    m2.monthly_income = 3000  # 30€ (1%)
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    # 5 categorías para maximizar acumulación de restos
    household_base.add_category("categoria1")
    household_base.add_category("categoria2")
    household_base.add_category("categoria3")
    household_base.add_category("categoria4")
    household_base.add_category("categoria5")

    household_base.set_budget_for_category("categoria1", 60000)  # 600€
    household_base.set_budget_for_category("categoria2", 60000)
    household_base.set_budget_for_category("categoria3", 60000)
    household_base.set_budget_for_category("categoria4", 60000)
    household_base.set_budget_for_category("categoria5", 60000)
    # Total: 3000€

    contributions = household_base.get_current_contributions()

    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )

    assert amanda_total <= 297000, (
        f"Amanda excede su ingreso: {amanda_total}¢ > 297000¢. "
        f"Exceso: {amanda_total - 297000}¢"
    )


# ====================================================
# EDGE CASE 2: Números primos y restos máximos
# ====================================================


def test_edge_case_prime_numbers_maximize_remainders(household_base):
    """
    Caso extremo: Números primos para maximizar restos.

    Ingresos: 1997€ + 1003€ = 3000€
    Presupuesto: 3 categorías con números primos

    Los números primos maximizan los restos en división entera.
    """
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 199700  # 1997€ (primo)
    m2.monthly_income = 100300  # 1003€ (primo)
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    # Presupuestos primos
    household_base.set_budget_for_category("fijos", 149900)  # 1499€ (primo)
    household_base.set_budget_for_category("variables", 89989)  # 899.89€ (casi primo)
    household_base.set_budget_for_category("deuda/ahorro", 60111)  # 601.11€
    # Total: 3000€

    contributions = household_base.get_current_contributions()

    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )
    heri_total = sum(
        contributions[cat]["contributions"]["heri"] for cat in contributions
    )

    assert amanda_total <= 199700, f"Amanda excede: {amanda_total - 199700}¢"
    assert heri_total <= 100300, f"Heri excede: {heri_total - 100300}¢"

    # Validar que cada categoría suma exacto
    for cat_name, cat_data in contributions.items():
        expected = household_base.get_category_budget(cat_name)
        actual = sum(cat_data["contributions"].values())
        assert actual == expected, f"{cat_name}: expected {expected}¢, got {actual}¢"


# ====================================================
# EDGE CASE 3: Muchos miembros (más puntos de redondeo)
# ====================================================


def test_edge_case_five_members_equal_split(household_base):
    """
    Caso extremo: 5 miembros con reparto EQUAL.

    5 miembros → cada uno debe 20% exacto.
    Pero 10000 / 5 = 2000 basis points con resto.

    Con múltiples categorías, los restos se acumulan.
    """
    members = []
    for i in range(5):
        m = Member(f"miembro{i + 1}")
        m.monthly_income = 60000  # 600€ cada uno = 3000€ total
        household_base.register_member(m)
        members.append(m)

    household_base.freeze_registration_state()
    household_base.assign_distribution_method(MetodoReparto.EQUAL)

    # 3 categorías
    household_base.set_budget_for_category("fijos", 150000)
    household_base.set_budget_for_category("variables", 90000)
    household_base.set_budget_for_category("deuda/ahorro", 60000)

    contributions = household_base.get_current_contributions()

    # Cada miembro debe aportar ~600€ (su ingreso completo si budget = 100%)
    for i in range(5):
        member_name = f"miembro{i + 1}"
        total = sum(
            contributions[cat]["contributions"][member_name] for cat in contributions
        )
        assert total <= 60000, f"{member_name} excede su ingreso: {total}¢ > 60000¢"

    # Validar sumas por categoría
    for cat_name, cat_data in contributions.items():
        expected = household_base.get_category_budget(cat_name)
        actual = sum(cat_data["contributions"].values())
        assert actual == expected, f"{cat_name}: {actual}¢ != {expected}¢"


# ====================================================
# EDGE CASE 4: Presupuesto por porcentajes (33.33%)
# ====================================================


def test_edge_case_percentage_based_budget_33_percent(household_base):
    """
    Caso extremo: Usar set_budget_by_percentage con 33.33%.

    33.33% de 3000€ = 999.90€ → redondeo agresivo.
    Aplicar 3 veces (33.33% × 3) genera acumulación de errores.
    """
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    # Usar porcentajes que generan restos
    household_base.set_budget_by_percentage(3333, "fijos")  # 33.33%
    household_base.set_budget_by_percentage(3333, "variables")  # 33.33%
    household_base.set_budget_by_percentage(3334, "deuda/ahorro")  # 33.34%
    # Total: 100% (con ajuste en última categoría)

    contributions = household_base.get_current_contributions()

    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )

    assert amanda_total <= 200000, (
        f"Amanda excede con presupuesto porcentual: {amanda_total}¢ > 200000¢"
    )


# ====================================================
# EDGE CASE 5: Presupuesto mínimo (1 céntimo)
# ====================================================


def test_edge_case_one_cent_per_category(household_base):
    """
    Caso extremo: Presupuesto de 1 céntimo por categoría.

    Con 2 miembros, 1¢ no se puede dividir proporcionalmente.
    Todo el céntimo debe ir a un miembro.
    Acumulación: 3 categorías × 1¢ → un miembro recibe 3¢.
    """
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    # Presupuestos mínimos
    household_base.set_budget_for_category("fijos", 1)
    household_base.set_budget_for_category("variables", 1)
    household_base.set_budget_for_category("deuda/ahorro", 1)

    contributions = household_base.get_current_contributions()

    # Con 1¢, todo debe ir a un miembro (el de mayor ingreso)
    # NO debe romperse
    for cat_name, cat_data in contributions.items():
        actual = sum(cat_data["contributions"].values())
        assert actual == 1, f"{cat_name}: expected 1¢, got {actual}¢"


# ====================================================
# EDGE CASE 6: Muchas categorías (10+)
# ====================================================


def test_edge_case_ten_categories_accumulate_remainders(household_base):
    """
    Caso extremo: 10 categorías para maximizar acumulación de restos.

    Si cada categoría deja un resto de 1-2¢ para Amanda,
    10 categorías → 10-20¢ acumulados → excede ingreso.
    """
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    # 10 categorías con 300€ cada una = 3000€ total
    for i in range(10):
        cat_name = f"categoria{i + 1}"
        household_base.add_category(cat_name)
        household_base.set_budget_for_category(cat_name, 30000)

    contributions = household_base.get_current_contributions()

    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )

    assert amanda_total <= 200000, (
        f"Con 10 categorías, Amanda excede: {amanda_total}¢ > 200000¢. "
        f"Exceso acumulado: {amanda_total - 200000}¢"
    )


# ====================================================
# EDGE CASE 7: Custom splits con porcentajes raros
# ====================================================


def test_edge_case_custom_split_awkward_percentages(household_base):
    """
    Caso extremo: CUSTOM con porcentajes que no dividen limpiamente.

    Amanda: 66.66% (6666 basis)
    Heri: 33.33% (3333 basis)
    Resto: 1 basis point → se pierde o se asigna mal
    """
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    # Custom splits problemáticos
    household_base.assign_distribution_method(MetodoReparto.CUSTOM)
    household_base.set_custom_splits({"amanda": 66.66, "heri": 33.33})
    # Suma: 99.99% → falta 0.01% (1 basis point)

    household_base.set_budget_for_category("fijos", 150000)
    household_base.set_budget_for_category("variables", 90000)
    household_base.set_budget_for_category("deuda/ahorro", 60000)

    contributions = household_base.get_current_contributions()

    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )

    assert amanda_total <= 200000, (
        f"Custom split: Amanda excede {amanda_total - 200000}¢"
    )


# ====================================================
# EDGE CASE 8: Presupuesto > Ingresos (over-commit)
# ====================================================


def test_edge_case_budget_exceeds_income(household_base):
    """
    Caso extremo: Presupuesto > Ingresos totales.

    Ingresos: 3000€
    Presupuesto: 3500€ (116.6%)

    Sistema debe: rechazar o advertir.
    """
    m1 = Member("amanda")
    m2 = Member("heri")
    m1.monthly_income = 200000
    m2.monthly_income = 100000
    household_base.register_member(m1)
    household_base.register_member(m2)
    household_base.freeze_registration_state()

    # Presupuesto que excede ingresos
    household_base.set_budget_for_category("fijos", 175000)  # 1750€
    household_base.set_budget_for_category("variables", 105000)  # 1050€
    household_base.set_budget_for_category("deuda/ahorro", 70000)  # 700€
    # Total: 3500€ > 3000€

    # Esto NO debe romper el sistema
    contributions = household_base.get_current_contributions()

    # Aunque el presupuesto excede, nadie debe aportar más de lo que gana
    amanda_total = sum(
        contributions[cat]["contributions"]["amanda"] for cat in contributions
    )
    heri_total = sum(
        contributions[cat]["contributions"]["heri"] for cat in contributions
    )

    assert amanda_total <= 200000, "Amanda no puede aportar más de su ingreso"
    assert heri_total <= 100000, "Heri no puede aportar más de su ingreso"

    # La suma de contributions será < budget (déficit)
    total_contrib = amanda_total + heri_total
    total_budget = 350000
    assert total_contrib < total_budget, (
        "Con over-commit, contributions < budget es esperado"
    )


# ====================================================
# RESUMEN DE INVARIANTES CRÍTICOS
# ====================================================

"""
INVARIANTES QUE DEBEN CUMPLIRSE SIEMPRE:

1. ∀ miembro: Σ(contributions) ≤ ingreso_miembro
   Nadie puede aportar más de lo que gana.

2. ∀ categoría: Σ(contributions) == budget_categoría ± epsilon
   Las sumas deben cuadrar (epsilon máximo = número de miembros)

3. Σ(todas contributions) == Σ(budgets) ± epsilon
   La suma global debe cuadrar.

4. No pérdida de céntimos:
   Si budget = 3000€, contributions debe sumar 3000€ exacto.

5. Proporciones respetadas (cuando sea matemáticamente posible):
   Si Amanda gana 66.67%, debe aportar ~66.67% de cada categoría.

NOTA: Con aritmética entera, es imposible garantizar las 5 simultáneamente.
El sistema debe priorizar: 1 > 2 > 3 > 4 > 5
"""
