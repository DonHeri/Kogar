"""
SIMULACIÓN MES REAL — Amanda y Heri

Datos:
- Amanda: 1.339,58€ | Heri: 1.124,50€ | Total: 2.464,08€
- Fijos 53% | Variables 20% | Reserva 27% (auto)
- Reparto proporcional
- Amanda deuda: 118,90€ | Heri deuda: 138,66€
- Ahorro: auto (reserva - deuda)
"""

from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.saving_tracker import SavingTracker
from src.models.debt_tracker import DebtTracker
from src.models.constants import MetodoReparto, SavingScope
from src.models.member import Member
from src.utils.currency import to_euros, to_cents

# =============================================
# SETUP
# =============================================
budget = Budget()
expense_tracker = ExpenseTracker()
saving_tracker = SavingTracker()
debt_tracker = DebtTracker()

household = Household(
    budget=budget,
    expense_tracker=expense_tracker,
    saving_tracker=saving_tracker,
    debt_tracker=debt_tracker,
    method=MetodoReparto.PROPORTIONAL,
)

# =============================================
# REGISTRATION
# =============================================
print("=" * 60)
print("REGISTRO")
print("=" * 60)

amanda = Member("Amanda")
amanda.add_incomes(133958)
household.register_member(amanda)

heri = Member("Heri")
heri.add_incomes(112450)
household.register_member(heri)

household.freeze_registration_state()

print(f"Amanda: {to_euros(133958)}")
print(f"Heri:   {to_euros(112450)}")
print(f"Total:  {to_euros(household.get_total_incomes())}")

# =============================================
# PLANNING
# =============================================
print("\n" + "=" * 60)
print("PLANIFICACIÓN")
print("=" * 60)

# Presupuestos
pct_fijos = 5300
pct_variables = 2000
pct_reserva = 10000 - pct_fijos - pct_variables
household.set_budget_by_percentages(
    {"fijos": pct_fijos, "variables": pct_variables, "reserva": pct_reserva}
)

print(f"Fijos:     {to_euros(household.get_category_budget('fijos'))}")
print(f"Variables: {to_euros(household.get_category_budget('variables'))}")
print(f"Reserva:   {to_euros(household.get_category_budget('reserva'))} (auto)")
print(f"Total:     {to_euros(household.get_total_budgeted())}")

# Deuda
household.set_member_debt("amanda", 11890)
household.set_member_debt("heri", 13866)

# Ahorro auto
household.auto_assign_saving_goals()

print(
    f"\nAmanda — deuda: {to_euros(11890)} | ahorro: {to_euros(household._saving_goals['amanda'])}"
)
print(
    f"Heri   — deuda: {to_euros(13866)} | ahorro: {to_euros(household._saving_goals['heri'])}"
)

# Freeze
household.validate_debt_and_saving_dont_exceed_capacity()
household.freeze_planning_state()
print("\n✓ Planning congelado → MONTH")

# =============================================
# MONTH — Vida real
# =============================================
print("\n" + "=" * 60)
print("TRANSCURSO DEL MES")
print("=" * 60)

# ------ GASTOS COMPARTIDOS (fijos, is_shared=True) ------
print("\n--- Gastos compartidos (fijos) ---")

# Alquiler + agua: 581€, sacado de ahorros por ambos
# Primero retiran de ahorros, luego registran el gasto
# Asumo: cada uno retira su parte proporcional de savings
# Amanda paga el gasto (quien lo abona al casero da igual para el settlement)
from src.models.expense import Expense

expense_alquiler = Expense("amanda", "fijos", 58100, "Alquiler + agua", is_shared=True)
household.register_expense(expense_alquiler)
print(f"Amanda paga alquiler+agua: 581,00€ (compartido)")

# Internet: Heri paga 21€
expense_internet = Expense("heri", "fijos", 2100, "Internet", is_shared=True)
household.register_expense(expense_internet)
print(f"Heri paga internet: 21,00€ (compartido)")

# ------ GASTOS PERSONALES (variables, is_shared=False) ------
print("\n--- Gastos personales (variables) ---")

# Amanda: 442,51€ ocio (personal, cobró 25€ extra del mes anterior)
expense_ocio_amanda = Expense(
    "amanda", "variables", 44251, "Ocio personal", is_shared=False
)
household.register_expense(expense_ocio_amanda)
print(f"Amanda ocio: 442,51€ (personal)")

# Heri: 80,24€ nutrición (personal)
expense_nutri = Expense(
    "heri", "variables", 8024, "Productos nutrición", is_shared=False
)
household.register_expense(expense_nutri)
print(f"Heri nutrición: 80,24€ (personal)")

# Heri: 26,55€ gimnasio (personal)
expense_gym = Expense("heri", "variables", 2655, "Gimnasio", is_shared=False)
household.register_expense(expense_gym)
print(f"Heri gimnasio: 26,55€ (personal)")

# Heri: 3,90€ (personal, variables)
expense_misc = Expense("heri", "variables", 390, "Varios", is_shared=False)
household.register_expense(expense_misc)
print(f"Heri varios: 3,90€ (personal)")

# Heri: 10,24€ gasolina (personal, variables)
expense_gas = Expense("heri", "variables", 1024, "Gasolina", is_shared=False)
household.register_expense(expense_gas)
print(f"Heri gasolina: 10,24€ (personal)")

# ------ PAGOS DE DEUDA ------
print("\n--- Pagos de deuda ---")

# Amanda: paga su deuda completa 118,90€
household.register_debt_payment("amanda", 11890, "Préstamo coche")
print(f"Amanda paga deuda: 118,90€ ✓ completa")

# Heri: paga deuda completa (131,19 + 7,47 = 138,66)
household.register_debt_payment("heri", 13119, "Préstamo - parte principal")
household.register_debt_payment("heri", 747, "Préstamo - intereses")
print(f"Heri paga deuda: 131,19 + 7,47 = 138,66€ ✓ completa")

# ------ AHORRO ------
print("\n--- Movimientos de ahorro ---")

# Heri: deposita 131,19€ (lo que pagó de deuda principal va también a ahorro)
saving_tracker.deposit("heri", 13119, SavingScope.PERSONAL, "Depósito mensual")
print(f"Heri deposita en ahorro: 131,19€ (personal)")

# Heri: debe 20€ más a su cuenta de ahorro (pendiente de depositar)
saving_tracker.deposit("heri", 2000, SavingScope.PERSONAL, "Deuda con cuenta ahorro")
print(f"Heri deposita en ahorro: 20,00€ (deuda con su cuenta)")

# Amanda: lo que se pasó de ocio lo cubre retirando de ahorro
# Su presupuesto de variables (su parte proporcional): consultamos
contributions = household.get_agreed_contributions()
amanda_variables_budget = (
    contributions.get("variables", {}).get("contributions", {}).get("amanda", 0)
)
exceso_amanda = 44251 - amanda_variables_budget
if exceso_amanda > 0:
    saving_tracker.withdraw(
        "amanda", exceso_amanda, SavingScope.PERSONAL, "Cubrir exceso ocio"
    )
    print(f"Amanda retira de ahorro: {to_euros(exceso_amanda)} (cubrir exceso ocio)")

# =============================================
# ESTADO FINAL DEL MES
# =============================================
print("\n" + "=" * 60)
print("ESTADO DEL MES")
print("=" * 60)

# --- Categorías visibles (sin reserva) ---
print("\nPRESUPUESTOS vs REALIDAD:")
for cat in ["fijos", "variables"]:
    budgeted = household.get_category_budget(cat)
    spent = household.get_category_spent(cat)
    remaining = household.get_category_remaining(cat)
    print(
        f"  {cat.title():12s} {to_euros(budgeted):>10s} presup. | {to_euros(spent):>10s} gastado | {to_euros(remaining):>10s} restante"
    )

# --- Estado por miembro ---
print("\nESTADO POR MIEMBRO:")
for member in ["amanda", "heri"]:
    print(f"\n  {member.title()}:")

    # Deuda
    debt_status = household.get_debt_status(member)
    debt_check = (
        "✓"
        if debt_status["remaining"] == 0
        else f"faltan {to_euros(debt_status['remaining'])}"
    )
    print(
        f"    Deuda:  {to_euros(debt_status['paid'])} / {to_euros(debt_status['committed'])} ({debt_check})"
    )

    # Ahorro
    saving_status = household.get_saving_goal_status(member)
    saving_check = (
        "✓"
        if saving_status["remaining"] <= 0
        else f"faltan {to_euros(saving_status['remaining'])}"
    )
    print(
        f"    Ahorro: {to_euros(saving_status['paid'])} / {to_euros(saving_status['committed'])} ({saving_check})"
    )

# --- Settlement ---
print("\nSETTLEMENT (gastos compartidos):")
settlement = household.get_settlement()
if settlement:
    for t in settlement:
        print(
            f"  {t['from'].title()} debe pagar {to_euros(t['amount'])} a {t['to'].title()}"
        )
else:
    print("  Todo saldado")

# --- Resumen rápido Amanda ---
print("\n" + "-" * 40)
print("Amanda dice que le quedan 887,52€ en cuenta.")
total_amanda_gastado = 58100 + 44251 + 11890  # alquiler + ocio + deuda
print(f"Amanda ha desembolsado este mes: {to_euros(total_amanda_gastado)}")
print(
    f"Ingreso: {to_euros(133958)} - desembolsado: {to_euros(total_amanda_gastado)} = {to_euros(133958 - total_amanda_gastado)}"
)
print("(Sin contar retiro de ahorro ni lo que reciba del settlement)")
