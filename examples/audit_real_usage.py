"""
Auditoría real: ejecuta todos los flujos principales para ver qué funciona
"""

from src.workflow.workflow_manager import WorkflowManager
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.constants import MetodoReparto


def test_flujo_basico():
    """Flujo completo más simple: 2 personas, método proporcional"""
    print("\n=== FLUJO BÁSICO ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    # REGISTRATION
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 2000)
    wm.set_incomes("Heri", 1000)
    wm.finish_registration()
    print("✓ Registro completado")

    # PLANNING
    wm.set_standard_categories()
    wm.set_budget_for_category("fijos", 1500)
    wm.set_budget_for_category("variables", 800)
    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)

    planning_summary = wm.get_planning_summary()
    print(f"✓ Planning configurado: {len(planning_summary['categories'])} categorías")
    print(
        f"  - Amanda debe: {planning_summary['contributions_preview']['fijos']['contributions']['amanda'] / 100:.2f}€"  # to_euros()
    )
    print(
        f"  - Heri debe: {planning_summary['contributions_preview']['fijos']['contributions']['heri'] / 100:.2f}€"
    )

    wm.finish_planning()
    print("✓ Planning finalizado")

    # MONTH
    wm.register_expense("Amanda", "fijos", 500, "Alquiler")
    wm.register_expense("Heri", "variables", 200, "Supermercado")
    wm.register_expense("Amanda", "fijos", 300, "Luz")
    
    month_summary = wm.get_month_summary()
    print(f"✓ Gastos registrados: {month_summary['total']['total_spent'] / 100:.2f}€")
    print(
        f"  - Fijos: {month_summary['by_category']['fijos']['spent'] / 100:.2f}€ / {month_summary['by_category']['fijos']['budget'] / 100:.2f}€"
    )
    print(
        f"  - Variables: {month_summary['by_category']['variables']['spent'] / 100:.2f}€ / {month_summary['by_category']['variables']['budget'] / 100:.2f}€"
    )
    print(planning_summary)
    return "✅ FLUJO BÁSICO FUNCIONA"


def test_metodo_equal():
    """Flujo con método EQUAL"""
    print("\n=== MÉTODO EQUAL ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 1000)
    wm.finish_registration()

    wm.set_standard_categories()
    wm.set_budget_for_category("fijos", 2000)
    wm.assign_distribution_method(MetodoReparto.EQUAL)

    planning_summary = wm.get_planning_summary()
    amanda_contrib = planning_summary["contributions_preview"]["fijos"][
        "contributions"
    ]["amanda"]
    heri_contrib = planning_summary["contributions_preview"]["fijos"]["contributions"][
        "heri"
    ]

    print(f"  - Amanda (3000€ ingreso) debe: {amanda_contrib / 100:.2f}€")
    print(f"  - Heri (1000€ ingreso) debe: {heri_contrib / 100:.2f}€")

    if amanda_contrib == heri_contrib:
        print("✓ Reparto 50/50 funciona correctamente")
        return "✅ MÉTODO EQUAL FUNCIONA"
    else:
        return "❌ MÉTODO EQUAL ROTO"


def test_metodo_custom():
    """Flujo con método CUSTOM"""
    print("\n=== MÉTODO CUSTOM ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 3000)
    wm.set_incomes("Heri", 1000)
    wm.finish_registration()

    wm.set_standard_categories()
    wm.set_budget_for_category("fijos", 2000)
    wm.set_custom_splits({"amanda": 70.0, "heri": 30.0})
    wm.assign_distribution_method(MetodoReparto.CUSTOM)

    try:
        planning_summary = wm.get_planning_summary()
        amanda_contrib = planning_summary["contributions_preview"]["fijos"][
            "contributions"
        ]["amanda"]
        heri_contrib = planning_summary["contributions_preview"]["fijos"][
            "contributions"
        ]["heri"]

        print(f"  - Amanda (70%) debe: {amanda_contrib / 100:.2f}€")
        print(f"  - Heri (30%) debe: {heri_contrib / 100:.2f}€")

        expected_amanda = 2000 * 0.70  # 1400€
        expected_heri = 2000 * 0.30  # 600€

        if (
            abs(amanda_contrib / 100 - expected_amanda) < 0.01
            and abs(heri_contrib / 100 - expected_heri) < 0.01
        ):
            print("✓ Reparto custom 70/30 funciona")
            return "✅ MÉTODO CUSTOM FUNCIONA"
        else:
            print(f"❌ Esperaba Amanda={expected_amanda}€, Heri={expected_heri}€")
            return "❌ MÉTODO CUSTOM: CÁLCULO INCORRECTO"
    except Exception as e:
        print(f"❌ Error: {e}")
        return f"❌ MÉTODO CUSTOM FALLA: {e}"


def test_member_status():
    """Ver status individual de un miembro"""
    print("\n=== STATUS POR MIEMBRO ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 2000)
    wm.set_incomes("Heri", 1000)
    wm.finish_registration()

    wm.set_standard_categories()
    wm.set_budget_for_category("fijos", 1500)
    wm.set_budget_for_category("variables", 600)
    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.finish_planning()

    wm.register_expense("Amanda", "fijos", 800)
    wm.register_expense("Heri", "fijos", 300)
    wm.register_expense("Amanda", "variables", 200)

    # Esto es dominio, no workflow - verificar si hay wrapper
    try:
        status = wm.household.get_member_status("amanda")
        print(f"✓ Amanda status:")
        print(f"  - Debe: {status['owed'] / 100:.2f}€")
        print(f"  - Pagó: {status['paid'] / 100:.2f}€")
        print(f"  - Balance: {status['balance'] / 100:.2f}€")

        if status["balance"] > 0:
            print(f"  → Amanda pagó DE MÁS: {abs(status['balance']) / 100:.2f}€")
        elif status["balance"] < 0:
            print(f"  → Amanda debe TODAVÍA: {abs(status['balance']) / 100:.2f}€")
        else:
            print(f"  → Amanda está al día")

        return "✅ MEMBER STATUS FUNCIONA"
    except Exception as e:
        return (
            f"⚠️ MEMBER STATUS: acceso directo a household (falta wrapper en workflow)"
        )


def test_categoria_custom():
    """Crear categoría personalizada"""
    print("\n=== CATEGORÍA CUSTOM ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 2000)
    wm.finish_registration()

    wm.set_standard_categories()
    wm.add_category("mascotas")
    wm.set_budget_for_category("mascotas", 150)
    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    wm.finish_planning()

    wm.register_expense("Amanda", "mascotas", 80, "Veterinario")

    summary = wm.get_month_summary()
    if "mascotas" in summary["by_category"]:
        print(
            f"✓ Categoría 'mascotas' funciona: {summary['by_category']['mascotas']['spent'] / 100:.2f}€"
        )
        return "✅ CATEGORÍAS CUSTOM FUNCIONAN"
    else:
        return "❌ CATEGORÍAS CUSTOM ROTAS"


def test_loose_money():
    """Verificar dinero suelto (ingresos - presupuesto)"""
    print("\n=== LOOSE MONEY ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)  # 3000€ de ingreso
    wm.finish_registration()

    wm.set_standard_categories()
    wm.set_budget_for_category("fijos", 1500)  # Solo presupuestamos 1500€
    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)

    planning = wm.get_planning_summary()
    loose = planning["loose_money"]["total"]

    expected_loose = (3000 - 1500) * 100  # 1500€ en cents

    print(f"  - Ingresos: 3000€")
    print(f"  - Presupuestado: 1500€")
    print(f"  - Loose money: {loose / 100:.2f}€")

    if abs(loose - expected_loose) < 1:
        print("✓ Cálculo correcto")
        return "✅ LOOSE MONEY FUNCIONA"
    else:
        print(f"❌ Esperaba {expected_loose / 100:.2f}€, obtuve {loose / 100:.2f}€")
        return "❌ LOOSE MONEY INCORRECTO"


if __name__ == "__main__":
    print("=" * 60)
    print("AUDITORÍA REAL - EJECUTANDO FLUJOS")
    print("=" * 60)

    resultados = []

    try:
        resultados.append(test_flujo_basico())
    except Exception as e:
        resultados.append(f"❌ FLUJO BÁSICO FALLA: {e}")

    try:
        resultados.append(test_metodo_equal())
    except Exception as e:
        resultados.append(f"❌ MÉTODO EQUAL FALLA: {e}")

    try:
        resultados.append(test_metodo_custom())
    except Exception as e:
        resultados.append(f"❌ MÉTODO CUSTOM FALLA: {e}")

    try:
        resultados.append(test_member_status())
    except Exception as e:
        resultados.append(f"❌ MEMBER STATUS FALLA: {e}")

    try:
        resultados.append(test_categoria_custom())
    except Exception as e:
        resultados.append(f"❌ CATEGORÍA CUSTOM FALLA: {e}")

    try:
        resultados.append(test_loose_money())
    except Exception as e:
        resultados.append(f"❌ LOOSE MONEY FALLA: {e}")

    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    for r in resultados:
        print(r)

    funcionan = sum(1 for r in resultados if r.startswith("✅"))
    total = len(resultados)
    print(f"\n{funcionan}/{total} flujos funcionando")
