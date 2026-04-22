"""
SIMULACIÓN REALISTA — Un mes completo de Amanda y Heri

Caso real:
- Amanda gana 1.339,58€ / Heri gana 1.124,50€ (total hogar: 2.464,08€)
- Reparto proporcional al sueldo
- Fijos: 53% | Variables: 20% | Reserva (auto): 27%
- Amanda tiene una deuda personal de 118,90€/mes (préstamo coche)
- Heri tiene una deuda personal de 138,66€/mes (préstamo estudios)
- El resto de reserva de cada uno → ahorro automático
- Bucket compartido: "Vacaciones verano" con meta de 1.200€

Flujo: REGISTRATION → PLANNING → MONTH → CLOSING
"""

from datetime import datetime

from src.models.budget import Budget
from src.models.constants import MetodoReparto, SavingScope
from src.models.debt_tracker import DebtTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.saving_tracker import SavingTracker
from src.utils.currency import format_percentage, to_euros
from src.workflow.workflow_manager import WorkflowManager

# =============================================
# SETUP — Instanciar todo
# =============================================

household = Household(
    budget=Budget(),
    expense_tracker=ExpenseTracker(),
    saving_tracker=SavingTracker(),
    debt_tracker=DebtTracker(),
    method=MetodoReparto.PROPORTIONAL,
)
wm = WorkflowManager(household)


# =============================================
# FASE 1 — REGISTRATION
# =============================================

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

wm.finish_registration()
print("\n[OK] Registro congelado. Fase: PLANNING\n")


# =============================================
# FASE 2 — PLANNING
# =============================================

print("=" * 60)
print("FASE 2: PLANIFICACIÓN")
print("=" * 60)

# --- Presupuestos por porcentaje ---
# reserva se autocalcula: 100 - 53 - 20 = 27%
# (hay que incluir reserva para que los porcentajes sumen 100%)
wm.set_budget_by_percentages({"fijos": 53.0, "variables": 20.0, "reserva": 27.0})

print("Presupuestos asignados:")
for cat in wm.get_active_categories():
    budget = wm.get_category_budget(cat)
    pct = wm.get_budget_as_percentage(cat)
    behavior = wm.get_category_behavior(cat)
    print(f"  {cat.title():<12} {to_euros(budget):>10}"
          f"  ({format_percentage(pct)})  [{behavior.name}]")

# --- Método de reparto ---
wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
print("\nMétodo de reparto: PROPORCIONAL")

# --- Contribuciones por categoría ---
contributions = wm.get_current_contributions()
print("\nContribuciones (lo que aporta cada miembro por categoría):")
for cat, data in contributions.items():
    print(f"  {cat.title()}: {to_euros(data['planned'])}")
    for member, amount in data["contributions"].items():
        print(f"    {member.title()}: {to_euros(amount)}")

# --- Compromisos personales (se descuentan de la cuota de reserva) ---
wm.set_member_debt("Amanda", 118.90)   # préstamo coche
wm.set_member_debt("Heri", 138.66)     # préstamo estudios

debts = wm.get_all_debts()
print("\nDeuda declarada:")
print(f"  Amanda: {to_euros(debts['amanda'])} (préstamo coche)")
print(f"  Heri:   {to_euros(debts['heri'])} (préstamo estudios)")

# --- Ahorro automático = cuota de reserva - deuda ---
wm.auto_assign_saving_goals()

saving_goals = wm.get_all_saving_goals()
print("\nAhorro automático (reserva - deuda):")
print(f"  Amanda: {to_euros(saving_goals['amanda'])}")
print(f"  Heri:   {to_euros(saving_goals['heri'])}")

# --- Validar que deuda + ahorro no supera la reserva de cada miembro ---
wm.validate_debt_and_saving_dont_exceed_capacity()
print("\n[OK] Compromisos personales validados (no superan reserva)")

# --- Bucket de ahorro compartido: Vacaciones ---
bucket_id = wm.create_saving_bucket(
    bucket_name="Vacaciones verano",
    goal_euros=1200.0,
    scope=SavingScope.SHARED,
    owners=["Amanda", "Heri"],
    deadline=datetime(2026, 7, 1),
    description="Viaje de verano",
)
bucket = wm.get_bucket_by_id(bucket_id)
print(f"\nBucket creado: '{bucket.bucket_name}' — meta {to_euros(bucket.goal)}")
print(f"  Propietarios: {', '.join(o.title() for o in bucket.owners)}")
deadline = bucket.deadline.strftime('%d/%m/%Y') if bucket.deadline else "sin fecha"
print(f"  Fecha límite: {deadline}")

# --- Resumen de planificación ---
print("\n" + "-" * 40)
print("RESUMEN PLANNING:")
print("-" * 40)
print(f"  Fijos:     {to_euros(wm.get_category_budget('fijos'))}")
print(f"  Variables: {to_euros(wm.get_category_budget('variables'))}")
print(f"  Reserva:   {to_euros(wm.get_category_budget('reserva'))} (autocalculada)")
for member in ["amanda", "heri"]:
    debt_status = wm.get_debt_status(member)
    saving_status = wm.get_saving_goal_status(member)
    print(f"\n  {member.title()}:")
    print(f"    Deuda mensual:  {to_euros(debt_status['committed'])}")
    print(f"    Ahorro mensual: {to_euros(saving_status['committed'])}")

wm.finish_planning()
print("\n[OK] Planning congelado. Fase: MONTH\n")


# =============================================
# FASE 3 — MONTH (el día a día)
# =============================================

print("=" * 60)
print("FASE 3: TRANSCURSO DEL MES")
print("=" * 60)

# --- Gastos fijos (compartidos → cuentan para el settlement) ---
wm.register_expense("Amanda", "fijos", 800.00, "Alquiler")
wm.register_expense("Heri",   "fijos",  85.50, "Luz")
wm.register_expense("Amanda", "fijos",  45.00, "Internet")
print("Gastos fijos registrados:")
print("  Amanda: alquiler 800€ + internet 45€")
print("  Heri:   luz 85.50€")

# --- Gastos variables (behavior PERSONAL → no cuentan para settlement) ---
wm.register_expense("Heri",   "variables", 150.00, "Supermercado")
wm.register_expense("Amanda", "variables",  67.30, "Farmacia")
print("\nGastos variables registrados:")
print("  Amanda: farmacia 67.30€")
print("  Heri:   supermercado 150€")

# --- Pagos de deuda ---
wm.register_debt_payment("amanda", 118.90, "Cuota préstamo coche")
print(f"\nDeuda Amanda: pago único {to_euros(wm.get_debt_status('amanda')['paid'])}")

wm.register_debt_payment("heri",  70.00, "Préstamo estudios - parcial 1")
wm.register_debt_payment("heri",  68.66, "Préstamo estudios - parcial 2")
heri_paid = to_euros(wm.get_debt_status("heri")["paid"])
print(f"Deuda Heri:   dos pagos parciales, total {heri_paid}")

# --- Depósito de ahorro en cuenta individual ---
saving_remaining_amanda = wm.get_saving_goal_status("amanda")["remaining"]
wm.register_savings_deposit(
    "Amanda", saving_remaining_amanda / 100, SavingScope.PERSONAL, "Ahorro mensual"
)
print(f"\nAhorro: Amanda deposita {to_euros(saving_remaining_amanda)} (personal)")

saving_remaining_heri = wm.get_saving_goal_status("heri")["remaining"]
wm.register_savings_deposit(
    "Heri", saving_remaining_heri / 100, SavingScope.SHARED, "Fondo conjunto"
)
print(f"Ahorro: Heri deposita {to_euros(saving_remaining_heri)} (compartido)")

# --- Aportaciones al bucket de vacaciones ---
wm.deposit_to_bucket(bucket_id, "Amanda", 100.0)
wm.deposit_to_bucket(bucket_id, "Heri",   100.0)
bucket = wm.get_bucket_by_id(bucket_id)
pct_meta = int(bucket.balance / bucket.goal * 100) if bucket.goal else 0
print(
    f"\nBucket '{bucket.bucket_name}': "
    f"{to_euros(bucket.balance)} / {to_euros(bucket.goal)} ({pct_meta}%)"
)


# =============================================
# CONSULTAS EN MONTH
# =============================================

print("\n" + "=" * 60)
print("ESTADO DEL MES")
print("=" * 60)

# --- Presupuesto vs gasto real por categoría ---
print("\nPRESUPUESTOS vs GASTO REAL:")
for cat in wm.get_active_categories():
    budgeted  = wm.get_category_budget(cat)
    spent     = wm.get_category_spent(cat)
    remaining = wm.get_category_remaining(cat)
    print(f"  {cat.title():<12} {to_euros(budgeted):>10} presup. | "
          f"{to_euros(spent):>10} gastado | {to_euros(remaining):>10} restante")

# --- Estado personal de cada miembro ---
print("\nESTADO POR MIEMBRO:")
for member in ["amanda", "heri"]:
    print(f"\n  {member.title()}:")
    debt_status   = wm.get_debt_status(member)
    saving_status = wm.get_saving_goal_status(member)

    print(
        f"    Deuda:  {to_euros(debt_status['paid'])} pagado de"
        f" {to_euros(debt_status['committed'])}"
        f" (faltan {to_euros(debt_status['remaining'])})"
    )
    print(
        f"    Ahorro: {to_euros(saving_status['paid'])} depositado de"
        f" {to_euros(saving_status['committed'])}"
        f" (faltan {to_euros(saving_status['remaining'])})"
    )

    # Historial de pagos de deuda
    history = wm.get_debt_history(member)
    if history:
        print(f"    Historial deuda ({len(history)} pago/s):")
        for entry in history:
            print(f"      · {to_euros(entry.amount_cents)} — {entry.description}")

# --- Total compartido ahorrado ---
total_shared = wm.get_savings_total_shared()
print(f"\nFondo compartido total (todos los miembros): {to_euros(total_shared)}")

# --- Buckets del hogar ---
print("\nBUCKETS DEL HOGAR:")
for bid, bkt in wm.get_all_buckets().items():
    pct = int(bkt.balance / bkt.goal * 100) if bkt.goal else 0
    print(f"  '{bkt.bucket_name}': "
          f"{to_euros(bkt.balance)} / {to_euros(bkt.goal)} ({pct}%)")

# --- Settlement: quién debe a quién ---
print("\nSETTLEMENT (gastos compartidos):")
settlement = wm.get_settlement()
if settlement:
    for t in settlement:
        print(f"  {t['from'].title()} debe pagar"
              f" {to_euros(t['amount'])} a {t['to'].title()}")
else:
    print("  Todo saldado")


# =============================================
# FASE 4 — CLOSING
# =============================================

print("\n" + "=" * 60)
print("FASE 4: CIERRE DEL MES")
print("=" * 60)

wm.finish_month()

month_summary = wm.get_month_summary()
print("\nRESUMEN FINAL:")
print(f"  Total presupuestado: {to_euros(month_summary['totals']['total_budgeted'])}")
print(f"  Total gastado:       {to_euros(month_summary['totals']['total_spent'])}")
print(f"  Total restante:      {to_euros(month_summary['totals']['total_remaining'])}")

print("\nCOMPROMISOS PERSONALES — CUMPLIMIENTO:")
for member in ["amanda", "heri"]:
    debt_status   = wm.get_debt_status(member)
    saving_status = wm.get_saving_goal_status(member)
    debt_ok   = "[OK]" if debt_status["remaining"]   == 0 else "[FAIL]"
    saving_ok = "[OK]" if saving_status["remaining"] == 0 else "[FAIL]"
    print(f"  {member.title()}: Deuda {debt_ok} | Ahorro {saving_ok}")

print("\n[OK] Mes cerrado.")
