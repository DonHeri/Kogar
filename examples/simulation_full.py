"""
SIMULACIÓN REALISTA — Un mes completo de Amanda y Heri

Caso real:
- Amanda gana 1.339,58€ / Heri gana 1.124,50€ (total hogar: 2.464,08€)
- Reparto proporcional al sueldo
- Fijos: 53% | Variables: 20% | Reserva (auto): 27%
- Amanda tiene una deuda personal de 118,90€/mes (préstamo coche)
- Heri tiene una deuda personal de 138,66€/mes (préstamo estudios)
- El resto de reserva de cada uno → ahorro automático

Flujo: REGISTRATION → PLANNING → MONTH → CLOSING
"""

from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.saving_tracker import SavingTracker
from src.models.debt_tracker import DebtTracker  # ← NUEVO
from src.models.constants import MetodoReparto, SavingScope
from src.workflow.workflow_manager import WorkflowManager
from src.utils.currency import to_euros

# =============================================
# SETUP — Instanciar todo
# =============================================

budget = Budget()
expense_tracker = ExpenseTracker()
saving_tracker = SavingTracker()
debt_tracker = DebtTracker()  # ← NUEVO

household = Household(
    budget=budget,
    expense_tracker=expense_tracker,
    saving_tracker=saving_tracker,
    debt_tracker=debt_tracker,  # ← NUEVO parámetro
    method=MetodoReparto.PROPORTIONAL,
)

wm = WorkflowManager(household)


# =============================================
# FASE 1 — REGISTRATION
# =============================================
# ¿Quiénes viven juntos y cuánto ganan?

print("=" * 60)
print("FASE 1: REGISTRO")
print("=" * 60)

wm.register_member("Amanda")
wm.set_incomes("Amanda", 1339.58)

wm.register_member("Heri")
wm.set_incomes("Heri", 1124.50)

print(f"Amanda: {to_euros(wm.get_member_income('amanda'))}")
print(f"Heri:   {to_euros(wm.get_member_income('heri'))}")
print(f"Total:  {to_euros(wm.get_total_incomes())}")

# Congelar registro → crea SavingAccounts + DebtAccounts, avanza a PLANNING
wm.finish_registration()
print("\n✓ Registro congelado. Fase: PLANNING\n")


# =============================================
# FASE 2 — PLANNING
# =============================================
# ¿Cómo repartimos el dinero?

print("=" * 60)
print("FASE 2: PLANIFICACIÓN")
print("=" * 60)

# --- Presupuestos por porcentaje ---
# CLI calcula reserva automáticamente: 100 - 53 - 20 = 27
pct_fijos = 5300
pct_variables = 2000
pct_reserva = 10000 - (pct_fijos + pct_variables)

percentages = {"fijos": pct_fijos, "variables": pct_variables, "reserva": pct_reserva}
household.set_budget_by_percentages(percentages)

print("Presupuestos asignados:")
print(f"  Fijos:     {to_euros(wm.get_category_budget('fijos'))}")
print(f"  Variables: {to_euros(wm.get_category_budget('variables'))}")
print(f"  Reserva:   {to_euros(wm.get_category_budget('reserva'))} (auto)")
print(f"  Total:     {to_euros(wm.get_total_budgeted())}")

# --- Método de reparto ---
wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
print("\nMétodo de reparto: PROPORCIONAL")

# --- Contribuciones por categoría ---
# Cuánto aporta cada uno a fijos, variables y reserva
contributions = wm.preview_budget_contribution_summary(MetodoReparto.PROPORTIONAL)
print("\nContribuciones:")
for cat, data in contributions.items():
    print(f"  {cat}: {to_euros(data['planned'])}")
    for member, amount in data["contributions"].items():
        print(f"    {member}: {to_euros(amount)}")

# --- Compromisos personales (salen de reserva) ---
# Amanda: préstamo coche 118.90€/mes
# Heri: préstamo estudios 138.66€/mes
wm.set_member_debt("Amanda", 118.90)
wm.set_member_debt("Heri", 138.66)
print("\nDeuda declarada:")
print(f"  Amanda: {to_euros(household._member_debts['amanda'])} (préstamo coche)")
print(f"  Heri:   {to_euros(household._member_debts['heri'])} (préstamo estudios)")

# --- Ahorro automático = lo que sobra de reserva tras deuda ---
household.auto_assign_saving_goals()
print("\nAhorro automático (reserva - deuda):")
print(f"  Amanda: {to_euros(household._saving_goals['amanda'])}")
print(f"  Heri:   {to_euros(household._saving_goals['heri'])}")

# --- Validar que deuda + ahorro no supera reserva ---
# Esto se llama automáticamente en finish_planning,
# pero lo mostramos explícito para la simulación
household.validate_debt_and_saving_dont_exceed_capacity()
print("\n✓ Compromisos personales validados (no superan reserva)")

# --- Lo que ve el usuario (reserva NO se muestra) ---
print("\n" + "-" * 40)
print("RESUMEN PARA EL USUARIO:")
print("-" * 40)
print(f"  Fijos:     {to_euros(wm.get_category_budget('fijos'))}")
print(f"  Variables: {to_euros(wm.get_category_budget('variables'))}")
print()
for member in ["amanda", "heri"]:
    debt = household._member_debts[member]
    saving = household._saving_goals[member]
    print(f"  {member.title()}:")
    print(f"    Deuda mensual:  {to_euros(debt)}")
    print(f"    Ahorro mensual: {to_euros(saving)}")
print("-" * 40)

# Congelar planning → avanza a MONTH
wm.finish_planning()
print("\n✓ Planning congelado. Fase: MONTH\n")


# =============================================
# FASE 3 — MONTH (el día a día)
# =============================================
# Registrar gastos, pagos de deuda y depósitos de ahorro

print("=" * 60)
print("FASE 3: TRANSCURSO DEL MES")
print("=" * 60)

# --- Gastos compartidos (fijos) ---
# Amanda paga el alquiler (compartido, categoría fijos)
wm.register_expense("Amanda", "fijos", 800.00, "Alquiler")
print("Gasto: Amanda paga alquiler 800€ (fijos, compartido)")

# Heri paga la luz (compartido, categoría fijos)
wm.register_expense("Heri", "fijos", 85.50, "Luz")
print("Gasto: Heri paga luz 85.50€ (fijos, compartido)")

# Amanda paga internet (compartido, categoría fijos)
wm.register_expense("Amanda", "fijos", 45.00, "Internet")
print("Gasto: Amanda paga internet 45€ (fijos, compartido)")

# --- Gastos variables (personales por CategoryBehavior) ---
wm.register_expense("Heri", "variables", 150.00, "Supermercado")
print("Gasto: Heri supermercado 150€ (variables)")

wm.register_expense("Amanda", "variables", 67.30, "Farmacia")
print("Gasto: Amanda farmacia 67.30€ (variables)")

# --- Amanda paga su deuda (préstamo coche) ---
# Puede hacerlo en un solo pago o en varios parciales
household.register_debt_payment("amanda", 11890, "Cuota préstamo coche")
print("\nDeuda: Amanda paga 118.90€ (préstamo coche)")

# --- Heri paga su deuda en dos partes ---
household.register_debt_payment("heri", 7000, "Préstamo estudios - parcial 1")
print("Deuda: Heri paga 70.00€ (parcial 1 préstamo estudios)")

household.register_debt_payment("heri", 6866, "Préstamo estudios - parcial 2")
print("Deuda: Heri paga 68.66€ (parcial 2 préstamo estudios)")

# --- Ahorro ---
# Amanda deposita su parte de ahorro (personal)
saving_amanda = household._saving_goals["amanda"]
wm.register_savings_deposit(
    "Amanda", saving_amanda / 100, SavingScope.PERSONAL, "Ahorro mensual"
)
print(f"\nAhorro: Amanda deposita {to_euros(saving_amanda)} (personal)")

# Heri deposita su parte (compartido, para fondo conjunto)
saving_heri = household._saving_goals["heri"]
wm.register_savings_deposit(
    "Heri", saving_heri / 100, SavingScope.SHARED, "Fondo conjunto"
)
print(f"Ahorro: Heri deposita {to_euros(saving_heri)} (compartido)")


# =============================================
# CONSULTAS EN MONTH
# =============================================

print("\n" + "=" * 60)
print("ESTADO DEL MES")
print("=" * 60)

# --- Categorías (sin reserva) ---
print("\nPRESUPUESTOS vs GASTO REAL:")
for cat in ["fijos", "variables"]:
    budgeted = wm.get_category_budget(cat)
    spent = wm.get_category_spent(cat)
    remaining = wm.get_category_remaining(cat)
    print(
        f"  {cat.title()}: {to_euros(budgeted)} presupuestado | {to_euros(spent)} gastado | {to_euros(remaining)} restante"
    )

# --- Estado personal de cada miembro ---
print("\nESTADO POR MIEMBRO:")
for member in ["amanda", "heri"]:
    print(f"\n  {member.title()}:")

    # Deuda
    debt_status = household.get_debt_status(member)
    print(
        f"    Deuda:  {to_euros(debt_status['paid'])} pagado de {to_euros(debt_status['committed'])} (faltan {to_euros(debt_status['remaining'])})"
    )

    # Ahorro
    saving_status = household.get_saving_goal_status(member)
    print(
        f"    Ahorro: {to_euros(saving_status['paid'])} depositado de {to_euros(saving_status['committed'])} (faltan {to_euros(saving_status['remaining'])})"
    )

# --- Settlement (quién debe a quién en gastos compartidos) ---
print("\nSETTLEMENT (gastos compartidos):")
settlement = wm.get_settlement()
if settlement:
    for t in settlement:
        print(
            f"  {t['from'].title()} debe pagar {to_euros(t['amount'])} a {t['to'].title()}"
        )
else:
    print("  Todo saldado")


# =============================================
# FASE 4 — CLOSING
# =============================================

print("\n" + "=" * 60)
print("FASE 4: CIERRE DEL MES")
print("=" * 60)

wm.finish_month()

# Resumen final
print("\nRESUMEN FINAL:")
month_summary = household.get_month_summary()
print(f"  Total presupuestado: {to_euros(month_summary['totals']['total_budgeted'])}")
print(f"  Total gastado:       {to_euros(month_summary['totals']['total_spent'])}")
print(f"  Total restante:      {to_euros(month_summary['totals']['total_remaining'])}")

# Estado de compromisos personales
print("\nCOMPROMISOS PERSONALES — CUMPLIMIENTO:")
for member in ["amanda", "heri"]:
    debt_status = household.get_debt_status(member)
    saving_status = household.get_saving_goal_status(member)

    debt_ok = "✓" if debt_status["remaining"] == 0 else "✗"
    saving_ok = "✓" if saving_status["remaining"] == 0 else "✗"

    print(f"  {member.title()}: Deuda {debt_ok} | Ahorro {saving_ok}")

print("\n✓ Mes cerrado.")
