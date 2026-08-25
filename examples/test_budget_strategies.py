"""
Demo REAL de las nuevas funcionalidades de estrategias de presupuesto
"""

from src.workflow.workflow_manager import WorkflowManager
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.constants import MetodoReparto


def test_assign_loose_money():
    """Test: Asignar loose money automáticamente a ahorro"""
    print("\n" + "="*70)
    print("TEST 1: Asignar Loose Money a Ahorro")
    print("="*70)
    
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))
    
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)  # 3000€
    wm.finish_registration()
    
    wm.set_standard_categories()
    
    # Usuario presupuesta solo lo esencial
    wm.set_budget_for_category("fijos", 1200)
    wm.set_budget_for_category("variables", 600)
    
    summary_before = wm.get_planning_summary()
    loose_before = summary_before['loose_money'] / 100
    
    print(f"✓ Presupuestado: fijos=1200€, variables=600€")
    print(f"✓ Loose money ANTES: {loose_before}€")
    
    # NUEVA FUNCIONALIDAD: Asignar loose money a ahorro
    wm.assign_loose_money_to("ahorro")
    
    summary_after = wm.get_planning_summary()
    loose_after = summary_after['loose_money'] / 100
    ahorro_budget = summary_after['budget_by_category']['ahorro'] / 100
    
    print(f"✓ assign_loose_money_to('ahorro') ejecutado")
    print(f"✓ Loose money DESPUÉS: {loose_after}€")
    print(f"✓ Presupuesto ahorro: {ahorro_budget}€")
    
    if loose_after == 0 and ahorro_budget == loose_before:
        print("✅ ¡FUNCIONA! Todo el loose money fue a ahorro")
        return True
    else:
        print("❌ FALLO")
        return False


def test_apply_budget_percentages():
    """Test: Asignar presupuesto por porcentajes personalizados"""
    print("\n" + "="*70)
    print("TEST 2: Aplicar Porcentajes Personalizados (60/25/10/5)")
    print("="*70)
    
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))
    
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 4000)  # 4000€
    wm.finish_registration()
    
    wm.set_standard_categories()
    
    # NUEVA FUNCIONALIDAD: Aplicar porcentajes
    wm.apply_budget_percentages({
        "fijos": 60,        # 60% = 2400€
        "variables": 25,    # 25% = 1000€
        "ahorro": 10,       # 10% = 400€
        "deuda": 5          # 5% = 200€
    })
    
    summary = wm.get_planning_summary()
    
    print(f"✓ Ingresos totales: 4000€")
    print(f"✓ Fijos (60%): {summary['budget_by_category']['fijos']/100:.2f}€")
    print(f"✓ Variables (25%): {summary['budget_by_category']['variables']/100:.2f}€")
    print(f"✓ Ahorro (10%): {summary['budget_by_category']['ahorro']/100:.2f}€")
    print(f"✓ Deuda (5%): {summary['budget_by_category']['deuda']/100:.2f}€")
    print(f"✓ Loose money: {summary['loose_money']/100:.2f}€")
    
    if summary['loose_money'] == 0:
        print("✅ ¡FUNCIONA! Porcentajes suman 100%, no hay loose money")
        return True
    else:
        print("❌ FALLO")
        return False


def test_apply_strategy_50_30_20():
    """Test: Estrategia 50/30/20 con distribución por defecto"""
    print("\n" + "="*70)
    print("TEST 3: Estrategia 50/30/20 (con distribución por defecto)")
    print("="*70)
    
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))
    
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)  # 3000€
    wm.finish_registration()
    
    wm.set_standard_categories()
    
    # NUEVA FUNCIONALIDAD: Aplicar estrategia predefinida
    wm.apply_budget_strategy("50/30/20")
    
    summary = wm.get_planning_summary()
    
    print(f"✓ Ingresos totales: 3000€")
    print(f"✓ Necesidades (50%): fijos = {summary['budget_by_category']['fijos']/100:.2f}€")
    print(f"✓ Deseos (30%): variables = {summary['budget_by_category']['variables']/100:.2f}€")
    print(f"✓ Ahorro/Deuda (20%): ahorro = {summary['budget_by_category']['ahorro']/100:.2f}€, deuda = {summary['budget_by_category']['deuda']/100:.2f}€")
    print(f"✓ Loose money: {summary['loose_money']/100:.2f}€")
    
    expected_fijos = 1500  # 50%
    expected_variables = 900  # 30%
    actual_fijos = summary['budget_by_category']['fijos'] / 100
    actual_variables = summary['budget_by_category']['variables'] / 100
    
    if abs(actual_fijos - expected_fijos) < 1 and abs(actual_variables - expected_variables) < 1:
        print("✅ ¡FUNCIONA! Estrategia 50/30/20 aplicada correctamente")
        return True
    else:
        print("❌ FALLO")
        return False


def test_apply_strategy_custom_distribution():
    """Test: Estrategia 50/30/20 con distribución personalizada del 20%"""
    print("\n" + "="*70)
    print("TEST 4: Estrategia 50/30/20 con distribución custom del 20%")
    print("="*70)
    
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))
    
    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)  # 3000€
    wm.finish_registration()
    
    wm.set_standard_categories()
    
    # NUEVA FUNCIONALIDAD: Estrategia con distribución personalizada
    # Usuario quiere: 50% necesidades, 30% deseos, 20% ahorro/deuda
    # Pero dentro del 20%: 15% ahorro, 5% deuda
    wm.apply_budget_strategy("50/30/20", {
        "necesidades": {"fijos": 100},
        "deseos": {"variables": 100},
        "ahorro_deuda": {"ahorro": 75, "deuda": 25}  # 75% ahorro, 25% deuda del total
    })
    
    summary = wm.get_planning_summary()
    
    ahorro_amount = summary['budget_by_category']['ahorro'] / 100
    deuda_amount = summary['budget_by_category']['deuda'] / 100
    total_ahorro_deuda = ahorro_amount + deuda_amount
    
    print(f"✓ Ingresos totales: 3000€")
    print(f"✓ Ahorro/Deuda total (20% de 3000€): {total_ahorro_deuda:.2f}€")
    print(f"✓ Ahorro (75% del 20%): {ahorro_amount:.2f}€")
    print(f"✓ Deuda (25% del 20%): {deuda_amount:.2f}€")
    
    if abs(total_ahorro_deuda - 600) < 1 and abs(ahorro_amount - 450) < 1:
        print("✅ ¡FUNCIONA! Distribución personalizada del 20% correcta")
        return True
    else:
        print("❌ FALLO")
        return False


def test_flujo_completo_con_estrategia():
    """Test: Flujo completo usando estrategia"""
    print("\n" + "="*70)
    print("TEST 5: Flujo END-TO-END con estrategia 50/30/20")
    print("="*70)
    
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))
    
    # REGISTRATION
    wm.register_member("Amanda")
    wm.register_member("Heri")
    wm.set_incomes("Amanda", 2500)
    wm.set_incomes("Heri", 1500)
    wm.finish_registration()
    print("✓ Registro completado: 2 miembros, 4000€ totales")
    
    # PLANNING con estrategia
    wm.set_standard_categories()
    wm.apply_budget_strategy("50/30/20")
    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    
    planning = wm.get_planning_summary()
    print(f"✓ Estrategia 50/30/20 aplicada")
    print(f"  - Fijos: {planning['budget_by_category']['fijos']/100:.2f}€")
    print(f"  - Variables: {planning['budget_by_category']['variables']/100:.2f}€")
    print(f"  - Ahorro: {planning['budget_by_category']['ahorro']/100:.2f}€")
    print(f"  - Deuda: {planning['budget_by_category']['deuda']/100:.2f}€")
    
    wm.finish_planning()
    print("✓ Planning finalizado")
    
    # MONTH
    wm.register_expense("Amanda", "fijos", 800)
    wm.register_expense("Heri", "variables", 400)
    
    month_summary = wm.get_month_summary()
    print(f"✓ Gastos registrados: {month_summary['total']['total_spent']/100:.2f}€")
    
    print("✅ FLUJO COMPLETO FUNCIONA con estrategia de presupuesto")
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING: Nuevas funcionalidades de Estrategias de Presupuesto")
    print("="*70)
    
    resultados = []
    
    try:
        resultados.append(("Loose Money", test_assign_loose_money()))
    except Exception as e:
        print(f"❌ ERROR: {e}")
        resultados.append(("Loose Money", False))
    
    try:
        resultados.append(("Porcentajes Custom", test_apply_budget_percentages()))
    except Exception as e:
        print(f"❌ ERROR: {e}")
        resultados.append(("Porcentajes Custom", False))
    
    try:
        resultados.append(("Estrategia 50/30/20", test_apply_strategy_50_30_20()))
    except Exception as e:
        print(f"❌ ERROR: {e}")
        resultados.append(("Estrategia 50/30/20", False))
    
    try:
        resultados.append(("Distribución Custom", test_apply_strategy_custom_distribution()))
    except Exception as e:
        print(f"❌ ERROR: {e}")
        resultados.append(("Distribución Custom", False))
    
    try:
        resultados.append(("Flujo Completo", test_flujo_completo_con_estrategia()))
    except Exception as e:
        print(f"❌ ERROR: {e}")
        resultados.append(("Flujo Completo", False))
    
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)
    for nombre, pasó in resultados:
        status = "✅" if pasó else "❌"
        print(f"{status} {nombre}")
    
    total_passed = sum(1 for _, pasó in resultados if pasó)
    print(f"\n{total_passed}/{len(resultados)} tests pasando")
