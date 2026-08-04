"""
SIMULACIÓN REALISTA — Un mes completo de Amanda y Heri

Caso real:
- Amanda gana 1.339,58€ / Heri gana 1.124,50€ (total hogar: 2.464,08€)
- Reparto proporcional al sueldo
- Fijos: 53% | Variables: 20% | Reserva (auto): 27%
- Amanda tiene una deuda personal: financiación coche (cuota 317,67€/mes)
- Heri tiene una deuda personal: préstamo estudios (cuota 150€/mes)
- Ahorro en buckets: colchón libre de Heri, meta de Amanda (curso, deadline relativo),
  y un bucket compartido "Vacaciones verano" con meta de 1.200€ y deadline fijo.
  El ahorro es elección, no obligación — nada se valida contra la reserva.

Flujo: REGISTRATION → PLANNING → MONTH → CLOSING
"""

from datetime import date, datetime, timedelta

from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.utils.currency import format_percentage, to_cents, to_euros, to_euros_float
from src.workflow.workflow_manager import WorkflowManager
from src.workflow.summary_service import SummaryService

# Persistencia
from src.storage.connection import DatabaseConnection
from src.storage.member_repository import MemberRepository
from src.storage.household_repository import HouseholdRepository
from src.storage.period_repository import PeriodRepository
from src.storage.debt_entry_repository import DebtEntryRepository
from src.storage.budget_categories_repository import BudgetCategoryRepository
from src.storage.expense_repository import ExpenseRepository
from src.storage.income_entry_repository import IncomeEntryRepository
from src.storage.saving_bucket_repository import SavingBucketRepository
from src.storage.saving_bucket_entry_repository import SavingBucketEntryRepository
from src.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

with DatabaseConnection(
    database=DB_NAME,
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
) as conn:
    household_repo = HouseholdRepository(conn)
    member_repo = MemberRepository(conn)
    period_repo = PeriodRepository(conn)
    debt_repo = DebtEntryRepository(conn)
    budget_categories_repo = BudgetCategoryRepository(conn)
    expense_repo = ExpenseRepository(conn)
    income_entry_repo = IncomeEntryRepository(conn)
    saving_bucket_repo = SavingBucketRepository(conn)
    saving_bucket_entry_repo = SavingBucketEntryRepository(conn)
    # =============================================
    # SETUP — Instanciar todo
    # =============================================

    household = Household(
        budget=Budget(),
        expense_tracker=ExpenseTracker(),
        saving_bucket_tracker=SavingBucketTracker(),
        debt_bucket_tracker=DebtBucketTracker(),
        method=MetodoReparto.PROPORTIONAL,
    )
    wm = WorkflowManager(
        household=household,
        household_repo=household_repo,
        member_repo=member_repo,
        period_repo=period_repo,
        debt_repo=debt_repo,
        budget_categories_repository=budget_categories_repo,
        expense_repo=expense_repo,
        saving_bucket_repo=saving_bucket_repo,
        income_entry_repo=income_entry_repo,
        saving_bucket_entry_repo=saving_bucket_entry_repo,
    )

    # =============================================
    # FASE 1 — ABRIR PERÍODO Y REGISTRAR
    # =============================================

    print("=" * 60)
    print("FASE 1: APERTURA DEL PERÍODO Y REGISTRO")
    print("=" * 60)

    # El período nace aquí: start_new_month es el único punto de apertura
    wm.start_new_month(start_date=date(2026, 5, 6))

    wm.register_member("Amanda")
    wm.set_member_incomes("Amanda", 1339.58)

    wm.register_member("Heri")
    wm.set_member_incomes("Heri", 1124.50)

    print(f"Amanda: {to_euros(wm.get_member_income('amanda'))}")
    print(f"Heri:   {to_euros(wm.get_member_income('heri'))}")
    print(f"Total:  {to_euros(wm.get_total_incomes())}")

    print("\n[OK] Período abierto. Fase: PLANNING\n")

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

    print("Presupuestos asignados (solo las raíces cuentan contra el ingreso):")
    for cat in wm.get_root_categories():
        budget = wm.get_category_budget(cat)
        pct = wm.get_budget_as_percentage(cat)
        print(f"  {cat.title():<12} {to_euros(budget):>10}  ({format_percentage(pct)})")

    # --- Desglose de "fijos" en subcategorías (árbol: fijos es el techo) ---
    wm.add_category("alquiler", parent="fijos")
    wm.add_category("luz", parent="fijos")
    wm.add_category("internet", parent="fijos")
    wm.set_budget_for_category("alquiler", 800.0)
    wm.set_budget_for_category("luz", 90.0)
    wm.set_budget_for_category("internet", 50.0)

    print("\nEl techo de 'fijos' repartido en subcategorías:")
    for child in wm.get_category_children("fijos"):
        print(
            f"    · {child.title():<12} {to_euros(wm.get_category_budget(child)):>10}"
        )
    print(
        f"    · {'Sin desglosar':<12} {to_euros(wm.get_category_billable('fijos')):>10}"
    )
    print(f"  {'TECHO':<14} {to_euros(wm.get_category_budget('fijos')):>10}")

    # --- Método de reparto ---
    wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
    print("\nMétodo de reparto: PROPORCIONAL")

    # --- Contribuciones por categoría ---
    # Cada categoría reparte solo lo suyo: una raíz con hijas reparte lo que no
    # les ha delegado, así que nadie aporta dos veces por el mismo dinero.
    contributions = wm.get_current_contributions()
    print("\nContribuciones (lo que aporta cada miembro por categoría):")
    for root in wm.get_root_categories():
        children = wm.get_category_children(root)
        print(f"\n  {root.title()} — techo {to_euros(wm.get_category_budget(root))}")

        if not children:
            for member, amount in contributions[root]["contributions"].items():
                print(f"      {member.title():<12} {to_euros(amount):>10}")
            continue

        # Las hijas y, al final, lo que la raíz no ha delegado en ellas
        group = [(child.title(), child) for child in children]
        group.append(("Sin desglosar", root))

        for label, cat in group:
            data = contributions[cat]
            print(f"    · {label:<14} reparte {to_euros(data['planned']):>10}")
            for member, amount in data["contributions"].items():
                print(f"        {member.title():<12} {to_euros(amount):>10}")

    # --- Compromisos personales (se descuentan de la cuota de reserva) ---
    coche_debt_id = wm.add_debt_bucket(
        name="financiación coche",
        principal_euros=20000,
        owner="amanda",
        installment_euros=317.67,
    )
    estudios_debt_id = wm.add_debt_bucket(
        name="Estudios",
        principal_euros=4000,
        owner="heri",
        installment_euros=150,
    )

    debts = wm.get_all_debts_summary()
    print("\nDeuda declarada:")
    for member, summary in debts.items():
        for bucket in summary["buckets"].values():
            print(
                f"  {member.title()} — {bucket['name']}: "
                f"{to_euros(bucket['principal'])} total · "
                f"cuota {to_euros(bucket['installment'])}/mes · "
                f"{bucket['remaining_installments']} cuotas restantes"
            )

    # --- Validar que la deuda no supera la reserva de cada miembro.
    # El ahorro NO se valida aquí: es elección, no obligación (ver DECISIONS). ---
    wm.validate_debt_doesnt_exceed_capacity()
    print("\n[OK] Deuda validada (no supera la parte de reserva de cada miembro)")

    # --- Ahorro: todo vive en buckets. Personal/compartido se deriva de owners;
    # la meta y el deadline son opcionales. Sin los dos, el bucket es puro ahorro
    # libre (colchón) — sin exigencia calculada. ---

    # Bucket personal SIN meta: colchón / ahorro libre de Heri.
    colchon_heri_id = wm.create_saving_bucket(
        bucket_name="colchón", owners=["heri"], description="colchón de ahorro de Heri"
    )
    # Bucket personal CON meta y deadline relativo ("dentro de 7 meses"): Amanda ahorra
    # para un curso. required_this_month se deriva solo, es informativo.
    curso_amanda_id = wm.create_saving_bucket(
        bucket_name="curso francés",
        owners=["amanda"],
        goal_euros=3400,
        deadline_in_months=7,
        description="ahorro para estudios amanda",
    )
    # Bucket COMPARTIDO con meta y deadline explícito: vacaciones.
    vacaciones_compartido_id = wm.create_saving_bucket(
        bucket_name="Vacaciones verano",
        goal_euros=1200.0,
        owners=["Amanda", "Heri"],
        deadline=datetime(2027, 7, 1),
        description="Viaje de verano",
    )

    bucket = wm.get_bucket_by_id(vacaciones_compartido_id)
    if bucket.goal:
        print(f"\nBucket creado: '{bucket.bucket_name}' — meta {to_euros(bucket.goal)}")
    print(f"  Propietarios: {', '.join(o.title() for o in bucket.owners)}")
    deadline = bucket.deadline.strftime("%d/%m/%Y") if bucket.deadline else "sin fecha"
    print(f"  Fecha límite: {deadline}")

    # --- Resumen de planificación ---
    print("\n" + "-" * 40)
    print("RESUMEN PLANNING:")
    print("-" * 40)
    print(f"  Fijos:     {to_euros(wm.get_category_budget('fijos'))}")
    print(f"  Variables: {to_euros(wm.get_category_budget('variables'))}")
    print(f"  Reserva:   {to_euros(wm.get_category_budget('reserva'))} (autocalculada)")
    for member in ["amanda", "heri"]:
        debt_totals = wm.get_debt_status(member)["totals"]
        saving_required = wm.get_saving_requirement_by_member(member)
        print(f"\n  {member.title()}:")
        print(f"    Deuda mensual:            {to_euros(debt_totals['committed'])}")
        print(
            f"    Ahorro exigido (informativo): {to_euros(saving_required)} "
            f"(metas con meta+deadline; no es obligación)"
        )

    wm.finish_planning()
    print("\n[OK] Planning congelado. Fase: MONTH\n")

    # =============================================
    # FASE 3 — MONTH (el día a día)
    # =============================================

    print("=" * 60)
    print("FASE 3: TRANSCURSO DEL MES")
    print("=" * 60)

    # --- Gastos fijos (compartidos → cuentan para el settlement) ---
    wm.register_expense("Amanda", "alquiler", 800.00, "Alquiler")
    wm.register_expense("Heri", "luz", 85.50, "Luz")
    wm.register_expense("Amanda", "internet", 45.00, "Internet")
    print("Gastos fijos registrados:")
    print("  Amanda: alquiler 800€ + internet 45€")
    print("  Heri:   luz 85.50€")

    # --- Gastos variables (behavior PERSONAL → no cuentan para settlement) ---
    wm.register_expense("Heri", "variables", 150.00, "Supermercado")
    wm.register_expense("Amanda", "variables", 67.30, "Farmacia")
    print("\nGastos variables registrados:")
    print("  Amanda: farmacia 67.30€")
    print("  Heri:   supermercado 150€")

    # --- Pagos de deuda (por bucket) ---
    wm.register_debt_payment(
        member="amanda", bucket_id=coche_debt_id, amount_euros=317.67
    )
    amanda_paid = to_euros(wm.get_debt_status("amanda")["totals"]["paid"])
    print(f"\nDeuda Amanda: pago de la cuota completa {amanda_paid}")

    wm.register_debt_payment(
        member="heri", bucket_id=estudios_debt_id, amount_euros=80.0
    )
    wm.register_debt_payment(
        member="heri", bucket_id=estudios_debt_id, amount_euros=70.0
    )
    heri_paid = to_euros(wm.get_debt_status("heri")["totals"]["paid"])
    print(f"Deuda Heri:   dos pagos parciales, total {heri_paid}")

    # --- AHORRO en MONTH: todo pasa por deposit_to_saving_bucket/withdraw_from_saving_bucket,
    # sin scope. La verdad es lo que se deposita/retira de verdad, no una promesa. ---

    # Vacaciones (compartido): ambos aportan.
    wm.deposit_to_saving_bucket(
        bucket_id=vacaciones_compartido_id, member="heri", amount_euros=100.0
    )
    wm.deposit_to_saving_bucket(
        bucket_id=vacaciones_compartido_id, member="amanda", amount_euros=100.0
    )

    # Colchón de Heri (sin meta): deposita el excedente discrecional tras deuda —
    # su parte de reserva menos la cuota de deuda. Nadie se lo exige, es su elección.
    disponible_heri = to_euros_float(
        wm.get_reserve_contribution_by_member("heri")
    ) - to_euros_float(wm.get_debt_status("heri")["totals"]["committed"])
    wm.deposit_to_saving_bucket(
        bucket_id=colchon_heri_id, member="heri", amount_euros=disponible_heri
    )
    print(f"\nHeri deposita en su colchón: {to_euros(to_cents(disponible_heri))}")

    # Curso de Amanda (meta + deadline): deposita, luego retira una parte —
    # get_saving_status debe reflejar el NETO, no cada movimiento por separado.
    wm.deposit_to_saving_bucket(
        bucket_id=curso_amanda_id, member="amanda", amount_euros=500.0
    )
    wm.withdraw_from_saving_bucket(
        bucket_id=curso_amanda_id, member="amanda", amount_euros=100.0
    )

    amanda_status = wm.get_saving_status("amanda")
    curso_status = amanda_status["buckets"][curso_amanda_id]
    print(
        f"Amanda - curso francés: depositó 500€, retiró 100€, neto este período: "
        f"{to_euros(curso_status['paid_this_period'])} "
        f"(saldo total: {to_euros(curso_status['balance'])}, "
        f"aún exige {to_euros(curso_status['required_this_month'])}/mes)"
    )

    # --- Bucket de vacaciones: estado tras los depósitos ---
    bucket = wm.get_bucket_by_id(vacaciones_compartido_id)
    pct_meta = int(bucket.balance / bucket.goal * 100) if bucket.goal else 0
    print(
        f"\nBucket '{bucket.bucket_name}': "
        f"{to_euros(bucket.balance)} / {to_euros(bucket.goal)} ({pct_meta}%)"
    )

    # --- Total compartido y movimientos compartidos del período ---
    total_shared = wm.get_savings_total_shared()
    print(f"Total en buckets compartidos (todo el hogar): {to_euros(total_shared)}")

    # El rango es semiabierto [inicio, fin): para incluir hoy, el fin es mañana.
    today = date.today()
    shared_movements = wm.get_savings_shared_by_period(today, today + timedelta(days=1))
    print("Movimientos compartidos de hoy, por miembro:")
    if not shared_movements:
        print("  (ninguno)")
    for member, entries in shared_movements.items():
        neto = sum(e.amount_cents for e in entries)
        print(
            f"  {member.title()}: {len(entries)} movimiento(s), neto {to_euros(neto)}"
        )

    # --- Agregar un ingreso extra ---
    wm.add_income_entry("Amanda", 200.0, "Venta de bicicleta")
    extra_incomes = wm.get_extra_income_entries()
    print(
        f"\nIngreso extra registrado: {extra_incomes[0].member_name.title()} - {to_euros(extra_incomes[0].amount_cents)} - {extra_incomes[0].description}"
    )
    print("\nReserva recalculada tras el ingreso extra:")
    print(f"  Total: {to_euros(wm.get_category_budget('reserva'))}")
    for member in ["amanda", "heri"]:
        print(
            f"  {member.title()}: "
            f"{to_euros(wm.get_reserve_contribution_by_member(member))}"
        )

    # =============================================
    # CONSULTAS EN MONTH
    # =============================================

    print("\n" + "=" * 60)
    print("ESTADO DEL MES")
    print("=" * 60)

    # --- Presupuesto vs gasto real: del total al detalle ---
    month_summary = SummaryService.get_month_summary(household=household)
    totals = month_summary["totals"]
    by_category = month_summary["by_category"]
    by_member = month_summary["by_member"]

    LABEL_WIDTH = 30

    def print_row(label: str, indent: int, planned: int, spent: int, left: int) -> None:
        """Una fila del árbol: etiqueta sangrada y las tres columnas alineadas."""
        text = " " * indent + label
        print(
            f"  {text:<{LABEL_WIDTH}}"
            f"{to_euros(planned):>13}{to_euros(spent):>13}{to_euros(left):>13}"
        )

    def member_share(member: str, categories: list[str]) -> tuple[int, int]:
        """Lo acordado y lo pagado por un miembro sumando esas categorías."""
        rows = by_member[member]["by_category"]
        agreed = sum(rows[c]["contribution"] for c in categories if c in rows)
        paid = sum(rows[c]["paid"] for c in categories if c in rows)
        return agreed, paid

    members = list(by_member)

    print("\nPRESUPUESTO vs GASTO REAL")
    print()
    print("  CÓMO SE LEE")
    print("    Cada bloque baja de lo general a lo concreto:")
    print("      TOTAL DEL HOGAR, luego cada categoría raíz, luego sus subcategorías.")
    print("    Bajo cada línea, quién pone ese dinero.")
    print()
    print("    En una CATEGORÍA:  presupuestado · gastado · lo que queda por gastar.")
    print(
        "    En un MIEMBRO:     lo que acordó poner · lo que ya pagó · lo que le falta."
    )
    print()
    print("    RESTANTE en negativo:")
    print("      en una categoría, se ha gastado más de lo presupuestado.")
    print("      en un miembro, ha pagado de más y el hogar se lo debe.")
    print()
    print("    'Sin desglosar' es la parte del techo que no está repartida en")
    print("    subcategorías. El techo de la raíz ya incluye a sus hijas, así que")
    print("    sumar la raíz y sus hijas contaría el mismo dinero dos veces.")
    print()
    print(f"  {'':<{LABEL_WIDTH}}{'PRESUP.':>13}{'GASTADO':>13}{'RESTANTE':>13}")
    print("  " + "-" * (LABEL_WIDTH + 39))

    print_row(
        "TOTAL DEL HOGAR",
        0,
        totals["total_budgeted"],
        totals["total_spent"],
        totals["total_remaining"],
    )

    for root_name, root in by_category.items():
        children = root["children"]
        subtree = [root_name] + list(children)

        print()
        print_row(
            root_name.title(), 2, root["ceiling"], root["spent"], root["remaining"]
        )

        # Quién sostiene esta raíz, contando también lo que cuelga de ella
        agreed_total = 0
        for member in members:
            agreed, paid = member_share(member, subtree)
            agreed_total += agreed
            print_row(member.title(), 4, agreed, paid, agreed - paid)

        # Lo acordado se congeló en finish_planning; el presupuesto sigue vivo.
        # Si se han movido después (p. ej. un ingreso extra sube la reserva),
        # las dos cifras dejan de coincidir y conviene decirlo, no esconderlo.
        if agreed_total != root["ceiling"]:
            print(
                f"      (lo acordado suma {to_euros(agreed_total)}: el presupuesto "
                f"cambió después de congelar el acuerdo)"
            )

        for child_name, child in children.items():
            print()
            print_row(
                f"· {child_name.title()}",
                4,
                child["ceiling"],
                child["spent"],
                child["remaining"],
            )
            for member in members:
                agreed, paid = member_share(member, [child_name])
                print_row(member.title(), 8, agreed, paid, agreed - paid)

        # Lo que la raíz no ha desglosado en hijas
        if children:
            own_spent = root["spent"] - sum(c["spent"] for c in children.values())
            print()
            print_row(
                "· Sin desglosar",
                4,
                root["unallocated"],
                own_spent,
                root["unallocated"] - own_spent,
            )
            for member in members:
                agreed, paid = member_share(member, [root_name])
                print_row(member.title(), 8, agreed, paid, agreed - paid)

    # --- Estado personal de cada miembro ---
    print("\nESTADO POR MIEMBRO:")
    for member in ["amanda", "heri"]:
        print(f"\n  {member.title()}:")
        debt_totals = wm.get_debt_status(member)["totals"]
        saving_totals = wm.get_saving_status(member)["totals"]

        print(
            f"    Deuda:  {to_euros(debt_totals['paid'])} pagado de"
            f" {to_euros(debt_totals['committed'])}"
            f" (faltan {to_euros(debt_totals['remaining'])})"
        )
        print(
            f"    Ahorro: {to_euros(saving_totals['paid_this_period'])} depositado"
            f" (metas exigen {to_euros(saving_totals['required_this_month'])}/mes,"
            f" informativo — no es obligación)"
        )

        # Historial de pagos de deuda
        history = wm.get_debt_history(member)
        if history:
            print(f"    Historial deuda ({len(history)} pago/s):")
            for entry in history:
                fecha = entry.date.strftime("%d/%m/%Y")
                print(f"      · {to_euros(entry.amount_cents)} ({fecha})")

    # --- Total compartido ahorrado ---
    total_shared = wm.get_savings_total_shared()
    print(f"\nFondo compartido total (todos los miembros): {to_euros(total_shared)}")

    # --- Buckets del hogar ---
    print("\nBUCKETS DEL HOGAR:")
    for bid, bkt in wm.get_all_buckets().items():
        if bkt.goal:
            pct = int(bkt.balance / bkt.goal * 100)
            print(
                f"  '{bkt.bucket_name}': {to_euros(bkt.balance)} / {to_euros(bkt.goal)} ({pct}%)"
            )
        else:
            print(f"  '{bkt.bucket_name}': {to_euros(bkt.balance)} (sin meta)")

    # --- Settlement: quién debe a quién ---
    print("\nSETTLEMENT (gastos compartidos):")
    settlement = wm.get_settlement()
    if settlement:
        for t in settlement:
            print(
                f"  {t['from'].title()} debe pagar"
                f" {to_euros(t['amount'])} a {t['to'].title()}"
            )
    else:
        print("  Todo saldado")

    # =============================================
    # FASE 4 — CLOSING
    # =============================================

    print("\n" + "=" * 60)
    print("FASE 4: CIERRE DEL MES")
    print("=" * 60)

    # La ventana del período es [inicio, fin): el día de cierre es exclusivo, para
    # que el día de corte pertenezca solo al mes que empieza. Aquí todo se ha
    # registrado hoy, así que el cierre va a mañana o los movimientos de hoy
    # quedarían fuera de su propio mes.
    wm.finish_month(end_date=date.today() + timedelta(days=1))

    month_summary = wm.get_month_summary()
    print("\nRESUMEN FINAL:")
    print(
        f"  Total presupuestado: {to_euros(month_summary['totals']['total_budgeted'])}"
    )
    print(f"  Total gastado:       {to_euros(month_summary['totals']['total_spent'])}")
    print(
        f"  Total restante:      {to_euros(month_summary['totals']['total_remaining'])}"
    )

    # Solo la deuda es un compromiso real (cumple/no cumple). El ahorro es elección:
    # se muestra lo depositado, sin marcar "fallo" por no llegar a una meta.
    print("\nCOMPROMISOS PERSONALES:")
    for member in ["amanda", "heri"]:
        debt_totals = wm.get_debt_status(member)["totals"]
        saving_totals = wm.get_saving_status(member)["totals"]
        debt_ok = "[OK]" if debt_totals["remaining"] == 0 else "[FAIL]"
        print(
            f"  {member.title()}: Deuda {debt_ok} | "
            f"Ahorro depositado {to_euros(saving_totals['paid_this_period'])} "
            f"(informativo)"
        )

    print("\n[OK] Mes cerrado.")
