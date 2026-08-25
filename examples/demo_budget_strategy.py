"""
Demo: Cómo debería funcionar el sistema de estrategias de presupuesto

FLUJO DESEADO:
1. Usuario registra ingresos totales: 3000€
2. Usuario elige estrategia "50/30/20"
3. Sistema calcula automáticamente:
   - Necesidades (fijos): 1500€ (50%)
   - Deseos (variables): 900€ (30%)
   - Ahorro+Deuda: 600€ (20%)
4. Usuario puede ajustar la distribución del 20%:
   - Ahorro: 400€
   - Deuda: 200€
5. Si hay loose money restante, va automático a ahorro (configurable)
"""

from src.workflow.workflow_manager import WorkflowManager
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.constants import MetodoReparto


def scenario_1_manual_tradicional():
    """Forma actual: usuario asigna presupuesto manualmente a cada categoría"""
    print("\n=== ESCENARIO 1: Forma tradicional (manual) ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_standard_categories()

    # Usuario asigna UNO POR UNO
    wm.set_budget_for_category("fijos", 1200)
    wm.set_budget_for_category("variables", 800)
    wm.set_budget_for_category("ahorro", 500)
    wm.set_budget_for_category("deuda", 300)

    summary = wm.get_planning_summary()
    total = summary["total_budgeted"] / 100
    loose = summary["loose_money"] / 100

    print(f"Total presupuestado: {total}€")
    print(f"Loose money: {loose}€")
    print("❌ Problema: Usuario debe hacer cálculos mentales, puede olvidar dinero")


def scenario_2_strategy_ideal():
    """FORMA IDEAL: Usuario elige estrategia 50/30/20"""
    print("\n=== ESCENARIO 2: Con estrategia 50/30/20 (IDEAL) ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)  # 3000€ totales
    wm.finish_registration()

    wm.set_standard_categories()

    # NUEVA FUNCIONALIDAD: Aplicar estrategia
    # wm.apply_budget_strategy("50/30/20", {
    #     "necesidades": ["fijos"],          # 50% → 1500€
    #     "deseos": ["variables"],           # 30% → 900€
    #     "ahorro_deuda": ["ahorro", "deuda"] # 20% → 600€
    # })

    # Sistema calcula automáticamente:
    # - fijos: 1500€
    # - variables: 900€
    # - ahorro: 400€ (66.6% del 20%)
    # - deuda: 200€ (33.3% del 20%)

    print("✅ Sistema calculó todo automáticamente")
    print("✅ Usuario solo eligió: estrategia + distribución dentro del 20%")
    print("⚠️ FALTA IMPLEMENTAR: apply_budget_strategy()")


def scenario_3_ajuste_porcentajes():
    """Usuario quiere 60/25/15 en lugar de 50/30/20"""
    print("\n=== ESCENARIO 3: Estrategia custom 60/25/15 ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 4000)
    wm.finish_registration()

    wm.set_standard_categories()

    # NUEVA FUNCIONALIDAD: Estrategia custom
    # wm.apply_custom_budget_strategy({
    #     "fijos": 60,        # 60% → 2400€
    #     "variables": 25,    # 25% → 1000€
    #     "ahorro": 10,       # 10% → 400€
    #     "deuda": 5          # 5% → 200€
    # })

    print("✅ Usuario tiene control total de porcentajes")
    print("✅ No hay loose money (suma 100%)")
    print("⚠️ FALTA IMPLEMENTAR: apply_custom_budget_strategy()")


def scenario_4_loose_money_automatico():
    """Qué pasa con el loose money sobrante"""
    print("\n=== ESCENARIO 4: Loose money automático ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_standard_categories()

    # Usuario presupuesta solo lo básico
    wm.set_budget_for_category("fijos", 1200)
    wm.set_budget_for_category("variables", 600)
    # Quedan 1200€ sin asignar (loose money)

    # NUEVA FUNCIONALIDAD: Asignar loose money automáticamente
    # wm.assign_loose_money_to("ahorro")  # Por defecto
    # O en config: wm.set_loose_money_destination("ahorro")

    summary = wm.get_planning_summary()
    loose = summary["loose_money"] / 100

    print(f"Loose money actual: {loose}€")
    print("💡 Debería ir automáticamente a 'ahorro'")
    print("⚠️ FALTA IMPLEMENTAR: assign_loose_money_to()")


def scenario_5_subcategorias():
    """Usar subcategorías para desglosar ahorro"""
    print("\n=== ESCENARIO 5: Subcategorías ===")
    wm = WorkflowManager(Household(Budget(), ExpenseTracker()))

    wm.register_member("Amanda")
    wm.set_incomes("Amanda", 3000)
    wm.finish_registration()

    wm.set_standard_categories()
    wm.set_budget_for_category("ahorro", 600)

    # NUEVA FUNCIONALIDAD: Desglosar categoría en subcategorías
    # wm.split_category_into_subcategories("ahorro", {
    #     "emergencias": 300,
    #     "vacaciones": 200,
    #     "inversiones": 100
    # })

    # Al registrar gasto:
    # wm.register_expense("Amanda", "ahorro", 50, subcategory="emergencias")

    print("💡 Subcategorías permiten tracking más detallado")
    print("💡 Pero NO afectan el reparto entre miembros (eso es por categoría)")
    print("⚠️ FALTA IMPLEMENTAR: split_category_into_subcategories()")


if __name__ == "__main__":
    print("=" * 70)
    print("DEMO: Estrategias de Presupuesto")
    print("=" * 70)

    scenario_1_manual_tradicional()
    scenario_2_strategy_ideal()
    scenario_3_ajuste_porcentajes()
    scenario_4_loose_money_automatico()
    scenario_5_subcategorias()

    print("\n" + "=" * 70)
    print("RESUMEN DE FUNCIONALIDADES FALTANTES")
    print("=" * 70)
    print("1. apply_budget_strategy('50/30/20', mappings)")
    print("2. apply_custom_budget_strategy(percentages)")
    print("3. assign_loose_money_to(category)")
    print("4. split_category_into_subcategories(category, splits)")
    print("\n💡 Todas operan en fase PLANNING, antes de finish_planning()")
