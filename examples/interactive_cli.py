"""
CLI interactivo de Kogar — ARCHIVO DESECHABLE.

No es el CLI oficial. Vive en un solo archivo y no toca nada de `src/`:
bórralo y no queda rastro.

    python examples/interactive_cli.py

Qué hace que el simulador no haga: REANUDAR. Rehidrata un período ya abierto
desde la BD, así que puedes cerrar el programa y seguir mañana donde lo dejaste.
Esa reconstrucción vive aquí abajo, en `resume_manager()` — a propósito, para no
meter un `resume` en WorkflowManager antes de decidir dónde debe vivir.

Dos avisos honestos sobre este archivo:

1. Cada operación que sale bien hace `commit()`. La conexión de Kogar solo confirma
   al salir del `with`, y eso convierte una sesión de 40 minutos en una única
   transacción: un Ctrl+C y pierdes el mes entero. Aquí se confirma acción a acción.

2. Cuando una operación falla, hace `rollback()` y la BD queda limpia — pero el
   objeto en memoria puede haberse quedado a medias si el fallo llegó después de
   mutarlo. Si ves algo raro tras un error, sal y vuelve a entrar: se rehidrata
   desde la BD, que es la verdad.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import UUID

# Permite `python examples/interactive_cli.py` sin haber hecho `pip install -e .`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# printer.py dibuja cajas con caracteres Unicode. Una consola en cp1252 los rechaza
# y tumba el programa a media tabla, así que la salida se fuerza a UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import psycopg2  # noqa: E402

from src.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER  # noqa: E402
from src.models.budget import Budget  # noqa: E402
from src.models.constants import MetodoReparto, Phase  # noqa: E402
from src.models.debt_bucket_tracker import DebtBucketTracker  # noqa: E402
from src.models.expense_tracker import ExpenseTracker  # noqa: E402
from src.models.household import Household  # noqa: E402
from src.models.saving_bucket_tracker import SavingBucketTracker  # noqa: E402
from src.storage.budget_categories_repository import (  # noqa: E402
    BudgetCategoryRepository,
)
from src.storage.connection import DatabaseConnection  # noqa: E402
from src.storage.debt_bucket_repository import DebtBucketRepository  # noqa: E402
from src.storage.debt_entry_repository import DebtEntryRepository  # noqa: E402
from src.storage.expense_repository import ExpenseRepository  # noqa: E402
from src.storage.household_repository import HouseholdRepository  # noqa: E402
from src.storage.member_repository import MemberRepository  # noqa: E402
from src.storage.period_repository import PeriodRepository  # noqa: E402
from src.storage.saving_bucket_entry_repository import (  # noqa: E402
    SavingBucketEntryRepository,
)
from src.storage.saving_bucket_repository import SavingBucketRepository  # noqa: E402
from src.utils import printer as p  # noqa: E402
from src.utils.currency import format_percentage, to_euros  # noqa: E402
from src.workflow.household_loader import HouseholdLoader  # noqa: E402
from src.workflow.workflow_manager import WorkflowManager  # noqa: E402

try:  # los colores ANSI en la consola de Windows
    import colorama

    colorama.just_fix_windows_console()
except Exception:  # pragma: no cover - cosmético
    pass


# ══════════════════════════════════════════════════════════════════
# ENTRADA DE DATOS
# ══════════════════════════════════════════════════════════════════


class Back(Exception):
    """El usuario quiere volver atrás. Cancela la acción en curso."""


def _read(prompt: str) -> str:
    """Lee una línea. Ctrl+C / Ctrl+D cancelan la acción, no el programa."""
    try:
        return input(f"  {p.BCYAN}›{p.RESET} {prompt}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise Back()


def ask_text(label: str, default: str | None = None) -> str:
    hint = f" [{default}]" if default else ""
    while True:
        value = _read(f"{label}{hint}: ")
        if value:
            return value
        if default is not None:
            return default
        p.warn("No puede quedar vacío. (Ctrl+C para volver)")


def ask_float(label: str, default: float | None = None) -> float:
    hint = f" [{default}]" if default is not None else ""
    while True:
        raw = _read(f"{label}{hint}: ")
        if not raw and default is not None:
            return default
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            p.warn("Escribe un número. Ej: 1234.56")


def ask_int(label: str, default: int | None = None) -> int:
    hint = f" [{default}]" if default is not None else ""
    while True:
        raw = _read(f"{label}{hint}: ")
        if not raw and default is not None:
            return default
        try:
            return int(raw)
        except ValueError:
            p.warn("Escribe un número entero.")


def ask_yes_no(label: str, default: bool = False) -> bool:
    hint = "S/n" if default else "s/N"
    while True:
        raw = _read(f"{label} ({hint}): ").lower()
        if not raw:
            return default
        if raw in ("s", "si", "sí", "y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        p.warn("Responde s o n.")


def ask_date(label: str, default: date) -> date:
    while True:
        raw = _read(f"{label} [{default.strftime('%d/%m/%Y')}]: ")
        if not raw:
            return default
        try:
            return datetime.strptime(raw, "%d/%m/%Y").date()
        except ValueError:
            p.warn("Formato: dd/mm/aaaa")


def choose(label: str, options: list[tuple[object, str]]) -> object:
    """Menú numerado. Devuelve la clave elegida; 0 cancela."""
    if not options:
        p.warn("No hay nada que elegir aquí todavía.")
        raise Back()

    p.blank()
    print(f"  {p.BOLD}{p.BYELLOW}{label}{p.RESET}")
    for i, (_, text) in enumerate(options, start=1):
        print(f"    {p.BCYAN}{i:>2}{p.RESET}  {text}")
    print(f"    {p.GRAY} 0  volver{p.RESET}")

    while True:
        raw = _read("Opción: ")
        if raw == "0":
            raise Back()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        p.warn(f"Elige un número entre 0 y {len(options)}.")


# ══════════════════════════════════════════════════════════════════
# TRANSACCIÓN — una confirmación por operación
# ══════════════════════════════════════════════════════════════════


def guarded(conn, fn, *args, success: str | None = None, **kwargs):
    """Ejecuta una operación, confirma si sale bien y revierte si falla.

    Todos los errores de dominio heredan de ValueError (ver src/models/exceptions.py),
    así que un solo `except ValueError` cubre el dominio entero.
    """
    try:
        result = fn(*args, **kwargs)
    except ValueError as exc:
        conn.rollback()
        p.error(str(exc))
        return None
    except psycopg2.errors.UniqueViolation as exc:
        conn.rollback()
        if "uq_period_start" in str(exc):
            p.error(
                "Ya existe un período de este hogar que empieza ese mismo día."
                " Elige otra fecha de inicio."
            )
        else:
            p.error(f"Ese dato ya existe: {str(exc).strip().splitlines()[0]}")
        return None
    except psycopg2.Error as exc:
        conn.rollback()
        p.error(f"Error de base de datos: {str(exc).strip().splitlines()[0]}")
        return None

    conn.commit()
    if success:
        p.ok(success)
    return result if result is not None else True


# ══════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN — repositorios y WorkflowManager
# ══════════════════════════════════════════════════════════════════


def build_repos(conn) -> dict:
    return {
        "household": HouseholdRepository(conn),
        "member": MemberRepository(conn),
        "period": PeriodRepository(conn),
        "budget_categories": BudgetCategoryRepository(conn),
        "expense": ExpenseRepository(conn),
        "debt_bucket": DebtBucketRepository(conn),
        "debt_entry": DebtEntryRepository(conn),
        "saving_bucket": SavingBucketRepository(conn),
        "saving_entry": SavingBucketEntryRepository(conn),
    }


def build_loader(repos: dict) -> HouseholdLoader:
    return HouseholdLoader(
        household_repo=repos["household"],
        member_repo=repos["member"],
        period_repo=repos["period"],
        budget_categories_repo=repos["budget_categories"],
        expense_repository=repos["expense"],
        debt_bucket_repository=repos["debt_bucket"],
        debt_entry_repository=repos["debt_entry"],
        saving_bucket_repository=repos["saving_bucket"],
        saving_bucket_entry_repository=repos["saving_entry"],
    )


def empty_household() -> Household:
    return Household(
        budget=Budget(),
        expense_tracker=ExpenseTracker(),
        saving_bucket_tracker=SavingBucketTracker(),
        debt_bucket_tracker=DebtBucketTracker(),
        method=MetodoReparto.PROPORTIONAL,
    )


def wire_manager(household: Household, repos: dict) -> WorkflowManager:
    return WorkflowManager(
        household=household,
        household_repo=repos["household"],
        member_repo=repos["member"],
        period_repo=repos["period"],
        expense_repo=repos["expense"],
        debt_repo=repos["debt_entry"],
        saving_bucket_entry_repo=repos["saving_entry"],
        saving_bucket_repo=repos["saving_bucket"],
        budget_categories_repository=repos["budget_categories"],
    )


def resume_manager(repos: dict, period_id: int) -> WorkflowManager:
    """Reconstruye un WorkflowManager sobre un período que ya existe en BD.

    Esto es lo único que le falta a la fachada para servir a un programa que se
    cierra y se vuelve a abrir. `load_full` ya trae el hogar entero; lo que hay
    que enhebrar a mano son los cuatro identificadores y el estado de fase.

    `_completed_phases` se deriva del orden del ciclo: si el período está en MONTH,
    PLANNING ya pasó. Es la misma regla que `Phase.require_at_least` usa en la ruta
    stateless, sin necesidad de llevar la cuenta en memoria.
    """
    household, member_ids, period = build_loader(repos).load_full(period_id=period_id)

    wm = wire_manager(household, repos)
    wm.household_id = period.household_id
    wm.period_id = period_id
    wm.period = period
    wm.member_ids = member_ids
    wm.current_phase = period.status
    wm._completed_phases = {
        phase for phase in Phase.cycle() if period.status.is_at_least(phase)
    }
    return wm


# ══════════════════════════════════════════════════════════════════
# ARRANQUE — elegir hogar y período
# ══════════════════════════════════════════════════════════════════


MAX_HOUSEHOLDS_SHOWN = 12


def pick_household(repos: dict, conn) -> int | None:
    """Devuelve el household_id elegido, o None si hay que crear uno nuevo.

    La BD acumula hogares vacíos de ejecuciones de test, y listarlos todos deja
    un menú inservible. Se muestran solo los que tienen miembros, los más
    recientes primero. Para cualquier otro, se escribe el id a mano.
    """
    households = repos["household"].list_households()

    with_members = []
    for row in sorted(households, key=lambda r: r["id"], reverse=True):
        members = repos["member"].list_members(row["id"])
        if members:
            names = ", ".join(m["full_name"].title() for m in members)
            with_members.append((row["id"], names))

    shown = with_members[:MAX_HOUSEHOLDS_SHOWN]
    options: list[tuple[object, str]] = [
        (hid, f"Hogar #{hid} — {names}") for hid, names in shown
    ]
    options.append(("NEW", f"{p.BGREEN}Crear un hogar nuevo{p.RESET}"))
    options.append(("ID", f"{p.GRAY}Escribir un id de hogar a mano{p.RESET}"))

    hidden = len(households) - len(shown)
    if hidden > 0:
        p.muted(
            f"  ({hidden} hogares más, sin miembros o antiguos — escribe el id si buscas uno)"
        )

    choice = choose("¿Con qué hogar trabajas?", options)

    if choice == "NEW":
        return None
    if choice == "ID":
        while True:
            hid = ask_int("Id del hogar")
            if repos["household"].find_by_id(hid):
                return hid
            p.warn(f"No existe ningún hogar con id {hid}.")
    return int(choice)  # type: ignore[arg-type]


def open_session(repos: dict, conn) -> WorkflowManager | None:
    """Deja lista una sesión: reanuda el período abierto o abre uno nuevo."""
    household_id = pick_household(repos, conn)

    # --- Hogar nuevo: la fachada crea la fila del hogar y la del período ---
    if household_id is None:
        start = ask_date("Fecha de inicio del período", date.today())
        wm = wire_manager(empty_household(), repos)
        if not guarded(conn, wm.start_new_month, start_date=start):
            return None
        p.ok(f"Hogar #{wm.household_id} creado. Período abierto el {start}.")
        return wm

    # --- Hogar existente con período abierto: reanudar ---
    current = repos["period"].get_current(household_id=household_id)
    if current and current.id:
        wm = resume_manager(repos, current.id)
        p.ok(
            f"Período #{current.id} reanudado — abierto el "
            f"{current.start_date.strftime('%d/%m/%Y')}, fase {current.status.value.upper()}."
        )
        return wm

    # --- Hogar existente sin período abierto: abrir uno nuevo con sus miembros ---
    p.info("Este hogar no tiene ningún período abierto.")
    if not ask_yes_no("¿Abrir un mes nuevo?", default=True):
        return None

    last = repos["period"].get_last(household_id=household_id)
    default_start = last.end_date if last and last.end_date else date.today()

    # Se reintenta porque la fecha puede chocar con un período ya existente
    # (hay un UNIQUE por hogar y día de inicio), y eso lo arregla el usuario.
    while True:
        start = ask_date("Fecha de inicio del período", default_start)

        household, member_ids = build_loader(repos).load_members_only(
            household_id=household_id
        )
        wm = wire_manager(household, repos)
        wm.household_id = household_id
        wm.member_ids = member_ids

        if guarded(conn, wm.start_new_month, start_date=start):
            p.ok(f"Período #{wm.period_id} abierto el {start.strftime('%d/%m/%Y')}.")
            return wm

        if not ask_yes_no("¿Probar con otra fecha?", default=True):
            return None


# ══════════════════════════════════════════════════════════════════
# PANTALLAS DE LECTURA
# ══════════════════════════════════════════════════════════════════


def show_header(wm: WorkflowManager) -> None:
    start = wm.period.start_date.strftime("%d/%m/%Y") if wm.period else "?"
    members = wm.get_registered_members()
    p.blank()
    p.divider("═")
    print(
        f"  {p.BOLD}{p.BWHITE}Hogar #{wm.household_id}{p.RESET}"
        f"{p.GRAY}  ·  {p.RESET}Período #{wm.period_id} desde {start}"
        f"{p.GRAY}  ·  {p.RESET}{p.BOLD}{p.BYELLOW}{wm.current_phase.value.upper()}{p.RESET}"
    )
    if members:
        ingresos = to_euros(wm.get_total_incomes())
        print(
            f"  {p.GRAY}{', '.join(n.title() for n in members)}"
            f"  ·  ingreso del hogar {ingresos}{p.RESET}"
        )
    p.divider("═")


def show_members(wm: WorkflowManager) -> None:
    incomes = wm.get_incomes()
    if not incomes:
        p.warn("Todavía no hay miembros registrados.")
        return
    p.section("MIEMBROS E INGRESOS")
    for name, cents in incomes.items():
        p.amount_positive(name.title(), to_euros(cents))
    p.divider()
    p.amount_positive("TOTAL", to_euros(wm.get_total_incomes()))


def show_budget(wm: WorkflowManager) -> None:
    roots = wm.get_root_categories()
    if not roots:
        p.warn("No hay categorías todavía.")
        return

    p.section("PRESUPUESTO")
    rows = []
    for root in roots:
        rows.append(
            [
                root.title(),
                to_euros(wm.get_category_budget(root)),
                format_percentage(wm.get_budget_as_percentage(root)),
            ]
        )
        for child in wm.get_category_children(root):
            rows.append(
                [f"  · {child.title()}", to_euros(wm.get_category_budget(child)), ""]
            )
        if wm.get_category_children(root):
            # Sin color: p.table pad la celda contando los códigos ANSI como
            # caracteres, así que colorear aquí descuadra la columna.
            rows.append(
                ["  · sin desglosar", to_euros(wm.get_category_billable(root)), ""]
            )
    p.table(headers=["Categoría", "Presupuesto", "% ingreso"], rows=rows)
    p.amount_neutral("TOTAL PRESUPUESTADO", to_euros(wm.get_total_budgeted()))


def show_contributions(wm: WorkflowManager) -> None:
    contributions = wm.get_current_contributions()
    if not contributions:
        p.warn("Aún no hay nada que repartir: asigna presupuesto primero.")
        return

    p.section("QUIÉN PONE QUÉ")
    p.muted("  Cada categoría reparte solo lo suyo — una raíz con hijas reparte")
    p.muted("  lo que no les ha delegado, así nadie aporta dos veces.")
    for category, data in contributions.items():
        name = category if isinstance(category, str) else str(category)
        if not data["contributions"]:
            continue
        p.subtitle(f"{name.title()} — reparte {to_euros(data['planned'])}")
        for member, amount in data["contributions"].items():
            p.amount_neutral(member.title(), to_euros(amount))


def show_debts(wm: WorkflowManager) -> None:
    summary = wm.get_all_debts_summary()
    has_any = any(s["buckets"] for s in summary.values())
    if not has_any:
        p.info("No hay ninguna deuda declarada.")
        return

    p.section("DEUDA DECLARADA")
    for member, data in summary.items():
        if not data["buckets"]:
            continue
        p.subtitle(member.title())
        for bucket in data["buckets"].values():
            estado = "cerrada" if bucket["is_closed"] else "abierta"
            print(
                f"    {p.BWHITE}{bucket['name']:<24}{p.RESET}"
                f"{p.BYELLOW}{to_euros(bucket['installment']):>12}{p.RESET}/mes"
                f"{p.GRAY}  ·  quedan {to_euros(bucket['remaining_balance'])}"
                f" en {bucket['remaining_installments']} cuotas  ·  {estado}{p.RESET}"
            )
        totals = data["totals"]
        p.muted(
            f"    Este período: pagado {to_euros(totals['paid'])}"
            f" de {to_euros(totals['committed'])}"
            f" (faltan {to_euros(totals['remaining'])})"
        )


def show_buckets(wm: WorkflowManager) -> None:
    buckets = wm.get_all_buckets()
    if not buckets:
        p.info("No hay buckets de ahorro.")
        return

    p.section("BUCKETS DE AHORRO")
    for bucket in buckets.values():
        owners = ", ".join(o.title() for o in bucket.owners)
        if bucket.goal:
            pct = min(100.0, bucket.balance / bucket.goal * 100)
            p.percentage_bar(bucket.bucket_name[:20], pct)
            p.muted(
                f"      {to_euros(bucket.balance)} de {to_euros(bucket.goal)}  ·  {owners}"
            )
        else:
            p.amount_positive(bucket.bucket_name[:26], to_euros(bucket.balance))
            p.muted(f"      sin meta  ·  {owners}")


def show_month_summary(wm: WorkflowManager) -> None:
    summary = wm.get_month_summary()
    totals = summary["totals"]

    p.summary_box(
        "Balance del mes",
        {
            "Presupuestado": to_euros(totals["total_budgeted"]),
            "Gastado": to_euros(totals["total_spent"]),
            "Restante": to_euros(totals["total_remaining"]),
        },
    )

    rows = []
    for root_name, root in summary["by_category"].items():
        rows.append(
            [
                root_name.title(),
                to_euros(root["ceiling"]),
                to_euros(root["spent"]),
                to_euros(root["remaining"]),
            ]
        )
        for child_name, child in root["children"].items():
            rows.append(
                [
                    f"  · {child_name.title()}",
                    to_euros(child["ceiling"]),
                    to_euros(child["spent"]),
                    to_euros(child["remaining"]),
                ]
            )
    p.table(headers=["Categoría", "Presup.", "Gastado", "Restante"], rows=rows)

    p.subtitle("Por miembro — lo acordado frente a lo pagado")
    for member, data in summary["by_member"].items():
        acordado = sum(row["contribution"] for row in data["by_category"].values())
        pagado = sum(row["paid"] for row in data["by_category"].values())
        p.amount_auto(
            f"{member.title()} (pagado − acordado)",
            pagado - acordado,
            formatter=lambda cents: to_euros(int(cents)),
        )
        p.muted(f"      acordó {to_euros(acordado)}  ·  pagó {to_euros(pagado)}")


def show_settlement(wm: WorkflowManager) -> None:
    transfers = wm.get_settlement()
    p.section("SETTLEMENT — GASTOS COMPARTIDOS")
    if not transfers:
        p.ok("Todo saldado. Nadie debe nada a nadie.")
        return
    for t in transfers:
        print(
            f"  {p.BOLD}{p.BRED}{t['from'].title()}{p.RESET} debe "
            f"{p.BOLD}{p.BYELLOW}{to_euros(t['amount'])}{p.RESET} a "
            f"{p.BOLD}{p.BGREEN}{t['to'].title()}{p.RESET}"
        )


def show_expenses(wm: WorkflowManager) -> None:
    """Los gastos del período, uno a uno, diciendo cuáles entran al settlement."""
    expenses = wm.household.expense_tracker.expenses
    if not expenses:
        p.info("No hay ningún gasto registrado todavía.")
        return

    p.section("GASTOS DEL PERÍODO")
    p.muted("  'Compartido' = tiene más de un participante, y solo esos entran")
    p.muted("  en el settlement. Un gasto de un solo participante es personal.")

    rows = []
    for expense in sorted(expenses, key=lambda e: e.date):
        reparto = (
            ", ".join(x.title() for x in expense.participants)
            if expense.is_shared
            else "personal"
        )
        rows.append(
            [
                expense.date.strftime("%d/%m"),
                expense.member.title(),
                expense.category.name.title(),
                to_euros(expense.amount),
                expense.description[:18],
                reparto[:26],
            ]
        )
    p.table(
        headers=["Día", "Pagó", "Categoría", "Importe", "Concepto", "Reparto"],
        rows=rows,
    )
    p.amount_neutral("TOTAL GASTADO", to_euros(wm.get_total_spent()))


def show_member_status(wm: WorkflowManager) -> None:
    member = str(
        choose("¿De quién?", [(m, m.title()) for m in wm.get_registered_members()])
    )
    status = wm.get_member_status(member)

    p.section(f"ESTADO DE {member.upper()}")
    p.summary_box(
        member.title(),
        {
            "Ingreso": to_euros(status["income"]),
            "Le toca poner": to_euros(status["owed"]),
            "Ha pagado": to_euros(status["paid"]),
            "Cuota de deuda": to_euros(status["debt"]),
            "Metas de ahorro": to_euros(status["saving_goal"]),
        },
    )
    p.amount_auto(
        "Balance (pagado − debido)",
        status["balance"],
        formatter=lambda cents: to_euros(int(cents)),
    )
    p.muted("      En negativo, debe dinero al hogar.")

    rows = [
        [
            cat.title(),
            to_euros(data["contribution"]),
            to_euros(data["paid"]),
            to_euros(data["remaining"]),
        ]
        for cat, data in status["by_category"].items()
    ]
    if rows:
        p.table(headers=["Categoría", "Acordó", "Pagó", "Le falta"], rows=rows)


def show_member_debt(wm: WorkflowManager) -> None:
    member = str(
        choose("¿De quién?", [(m, m.title()) for m in wm.get_registered_members()])
    )
    status = wm.get_debt_status(member)

    p.section(f"DEUDA DE {member.upper()}")
    if not status["buckets"]:
        p.info("No tiene ninguna deuda declarada.")
        return

    for bucket in status["buckets"].values():
        p.subtitle(bucket["name"])
        p.amount_neutral("Cuota mensual", to_euros(bucket["installment"]))
        p.amount_negative("Saldo pendiente", to_euros(bucket["remaining_balance"]))
        p.amount_positive("Pagado en total", to_euros(bucket["total_paid"]))
        p.muted(
            f"      quedan {bucket['remaining_installments']} cuotas"
            f"  ·  {'cerrada' if bucket['is_closed'] else 'abierta'}"
        )
        period = bucket["period"]
        p.muted(
            f"      este período: {to_euros(period['paid'])} de"
            f" {to_euros(period['committed'])}"
        )

    totals = status["totals"]
    p.summary_box(
        "Total del período",
        {
            "Comprometido": to_euros(totals["committed"]),
            "Pagado": to_euros(totals["paid"]),
            "Pendiente": to_euros(totals["remaining"]),
        },
    )

    if wm.current_phase.is_at_least(Phase.MONTH):
        history = wm.get_debt_history(member)
        if history:
            p.subtitle(f"Historial ({len(history)} pagos)")
            for entry in sorted(history, key=lambda e: e.date):
                p.muted(
                    f"      {entry.date.strftime('%d/%m/%Y')}"
                    f"  ·  {to_euros(entry.amount_cents)}"
                )


def show_member_saving(wm: WorkflowManager) -> None:
    member = str(
        choose("¿De quién?", [(m, m.title()) for m in wm.get_registered_members()])
    )
    status = wm.get_saving_status(member)

    p.section(f"AHORRO DE {member.upper()}")
    p.muted("  Todo esto es informativo: el ahorro es elección, no obligación.")

    for bucket_id, data in status["buckets"].items():
        bucket = wm.get_bucket_by_id(bucket_id)
        p.subtitle(bucket.bucket_name)
        p.amount_positive("Saldo", to_euros(data["balance"]))
        p.amount_neutral("Neto este período", to_euros(data["paid_this_period"]))
        if data["required_this_month"]:
            p.amount_neutral(
                "Exigiría al mes", to_euros(data["required_this_month"])
            )

    totals = status["totals"]
    p.summary_box(
        "Total del período",
        {
            "Depositado (neto)": to_euros(totals["paid_this_period"]),
            "Exigen las metas": to_euros(totals["required_this_month"]),
        },
    )


def show_shared_savings(wm: WorkflowManager) -> None:
    p.section("AHORRO COMPARTIDO")
    p.amount_positive("Total en buckets compartidos", to_euros(wm.get_savings_total_shared()))

    start, end = wm._current_period_range()
    movements = wm.get_savings_shared_by_period(start, end)
    if not movements:
        p.info("Sin movimientos compartidos en este período.")
        return

    p.subtitle("Movimientos del período, por miembro")
    for member, entries in movements.items():
        neto = sum(e.amount_cents for e in entries)
        p.amount_auto(
            f"{member.title()} ({len(entries)} mov.)",
            neto,
            formatter=lambda cents: to_euros(int(cents)),
        )


def show_missing_money(wm: WorkflowManager) -> None:
    """La parte de reserva que cada uno aún no ha destinado a nada."""
    summary = (
        wm.get_month_summary()
        if wm.current_phase.is_at_least(Phase.MONTH)
        else wm.get_planning_summary()
    )
    missing = summary["missing_money"]

    p.section("RESERVA SIN DESTINO")
    p.muted("  Dinero libre: de aquí sale deuda, ahorro, o lo que decidas.")
    for member, cents in missing["by_member"].items():
        p.amount_positive(member.title(), to_euros(cents))
    p.divider()
    p.amount_positive("TOTAL", to_euros(missing["total"]))


def show_method_comparison(wm: WorkflowManager) -> None:
    """Los tres métodos de reparto lado a lado, antes de elegir uno."""
    members = wm.get_registered_members()
    if not members:
        p.warn("Registra miembros antes de comparar métodos.")
        return

    p.section("COMPARAR MÉTODOS DE REPARTO")
    p.muted(f"  Método activo ahora: {wm.household.method.value}")

    totals: dict[str, dict[str, int]] = {}
    for method in (
        MetodoReparto.PROPORTIONAL,
        MetodoReparto.EQUAL,
        MetodoReparto.CUSTOM,
    ):
        try:
            preview = wm.preview_budget_contribution_summary(method)
        except ValueError as exc:
            p.muted(f"  {method.value}: no disponible ({exc})")
            continue
        per_member = {m: 0 for m in members}
        for data in preview.values():
            for member, amount in data["contributions"].items():
                per_member[member] = per_member.get(member, 0) + amount
        totals[method.value] = per_member

    if not totals:
        return

    methods = list(totals)
    rows = [
        [member.title()] + [to_euros(totals[m][member]) for m in methods]
        for member in members
    ]
    p.table(headers=["Miembro"] + [m.title() for m in methods], rows=rows)


def show_plan(wm: WorkflowManager) -> None:
    """El plan entero de un vistazo, antes de congelarlo."""
    show_members(wm)
    show_budget(wm)
    show_contributions(wm)
    show_debts(wm)
    show_buckets(wm)
    show_missing_money(wm)


# ══════════════════════════════════════════════════════════════════
# ACCIONES — PLANNING
# ══════════════════════════════════════════════════════════════════


def action_add_member(wm: WorkflowManager, conn) -> None:
    name = ask_text("Nombre del miembro")
    if not guarded(conn, wm.register_member, name, success=f"{name.title()} registrado"):
        return
    income = ask_float(f"Ingreso mensual de {name.title()} (€)")
    guarded(
        conn,
        wm.set_member_incomes,
        name,
        income,
        success=f"Ingreso de {name.title()}: {income:.2f} €",
    )


def action_set_income(wm: WorkflowManager, conn) -> None:
    members = wm.get_registered_members()
    member = choose(
        "¿A quién le cambias el ingreso?",
        [(m, f"{m.title()} — {to_euros(wm.get_member_income(m))}") for m in members],
    )
    income = ask_float(f"Nuevo ingreso de {str(member).title()} (€)")
    guarded(conn, wm.set_member_incomes, member, income, success="Ingreso actualizado")


def action_set_method(wm: WorkflowManager, conn) -> None:
    method = choose(
        "Método de reparto",
        [
            (MetodoReparto.PROPORTIONAL, "Proporcional al ingreso de cada uno"),
            (MetodoReparto.EQUAL, "A partes iguales"),
            (MetodoReparto.CUSTOM, "Porcentajes que decides tú"),
        ],
    )
    if not guarded(
        conn, wm.assign_distribution_method, method, success="Método asignado"
    ):
        return

    if method is MetodoReparto.CUSTOM:
        splits = {}
        for name in wm.get_registered_members():
            splits[name] = ask_float(f"% que pone {name.title()}")
        guarded(conn, wm.set_custom_splits, splits, success="Porcentajes guardados")


def action_budget_by_percentages(wm: WorkflowManager, conn) -> None:
    roots = wm.get_root_categories()
    total_income = wm.get_total_incomes()

    p.info(f"Ingreso del hogar: {to_euros(total_income)}. Los % se aplican sobre eso.")
    p.muted("  Deja 0 en una categoría para no asignarle nada.")

    percentages: dict[str, float] = {}
    remaining = 100.0
    for root in roots:
        p.muted(f"  Quedan {remaining:.2f} puntos por repartir.")
        pct = ask_float(f"% para {root.title()}", default=0.0)
        percentages[root] = pct
        remaining -= pct

    guarded(
        conn,
        wm.set_budget_by_percentages,
        percentages,
        success="Presupuesto asignado por porcentajes",
    )


def action_budget_bottom_up(wm: WorkflowManager, conn) -> None:
    """Presupuestar una raíz desde sus gastos concretos.

    Nadie sabe cuánto va a "fijos", pero todo el mundo sabe lo que paga de alquiler.
    Se preguntan las hijas primero SIN tocar el dominio (son números en memoria),
    se suman, y ese total es el mínimo del techo. Solo después se llama al dominio:
    ponerle importe a una hija antes de que su raíz tenga techo revienta, porque
    el techo vale 0.
    """
    root = str(choose("¿Qué categoría raíz desglosas?", [(r, r.title()) for r in wm.get_root_categories()]))

    p.info(f"Dime los gastos concretos de '{root}'. Enter en blanco para terminar.")
    children: dict[str, float] = {}
    while True:
        try:
            name = ask_text("Nombre del gasto (o Ctrl+C para terminar)")
        except Back:
            break
        amount = ask_float(f"Importe mensual de {name} (€)")
        children[name] = amount
        p.muted(f"    Llevas {sum(children.values()):.2f} € declarados en {root}.")

    declared = sum(children.values())
    if declared:
        p.ok(f"Has declarado {declared:.2f} € en {root}.")

    # Cuánto ingreso queda libre: el techo no puede pasar de ingresos − otras raíces
    otras = sum(
        wm.get_category_budget(other)
        for other in wm.get_root_categories()
        if other != root
    )
    libre = wm.get_total_incomes() - otras
    p.info(f"Puedes asignar hasta {to_euros(libre)} sin pasarte del ingreso.")

    ceiling = ask_float(f"Techo de '{root}' (€)", default=declared)
    if ceiling == declared and declared > 0:
        p.warn(
            "Techo justo: 'sin desglosar' queda en 0 y cualquier imprevisto"
            " se sale del presupuesto. Considera dejar margen."
        )

    if not guarded(
        conn, wm.set_budget_for_category, root, ceiling, success=f"Techo de {root} fijado"
    ):
        return

    for name, amount in children.items():
        if guarded(conn, wm.add_category, name, parent=root) is None:
            continue
        guarded(
            conn,
            wm.set_budget_for_category,
            name,
            amount,
            success=f"{name.title()}: {amount:.2f} €",
        )


def action_set_category_amount(wm: WorkflowManager, conn) -> None:
    category = str(
        choose(
            "¿A qué categoría le pones importe?",
            [(c, c.title()) for c in wm.get_active_categories()],
        )
    )
    amount = ask_float(
        f"Presupuesto de {category} (€)",
        default=float(wm.get_category_budget(category)) / 100,
    )
    guarded(
        conn, wm.set_budget_for_category, category, amount, success="Presupuesto fijado"
    )


def action_add_root_category(wm: WorkflowManager, conn) -> None:
    """Crea una categoría raíz. Las raíces son las que cuentan contra el ingreso."""
    existing = set(wm.get_active_categories())
    suggestions = {
        name: desc
        for name, desc in wm.household.budget.library.get_all_suggestions().items()
        if name not in existing
    }

    options: list[tuple[object, str]] = [
        (name, f"{name.title()}  {p.GRAY}{desc}{p.RESET}")
        for name, desc in list(suggestions.items())[:10]
    ]
    options.append(("OTRA", f"{p.BGREEN}Escribir un nombre nuevo{p.RESET}"))

    choice = choose("¿Qué categoría raíz creas?", options)
    name = ask_text("Nombre de la categoría") if choice == "OTRA" else str(choice)

    if not guarded(conn, wm.add_category, name, success=f"Categoría '{name}' creada"):
        return

    p.info("Una raíz nueva nace compartida: sus gastos se reparten entre todos.")
    if ask_yes_no("¿Le pones presupuesto ahora?", default=True):
        amount = ask_float(f"Presupuesto de {name} (€)")
        guarded(
            conn, wm.set_budget_for_category, name, amount, success="Presupuesto fijado"
        )


def action_add_subcategory(wm: WorkflowManager, conn) -> None:
    """Crea una subcategoría dentro de una raíz. Hereda de ella si es compartida."""
    roots = wm.get_root_categories()
    parent = str(
        choose(
            "¿Dentro de qué raíz?",
            [
                (
                    f"{r.title()}  {p.GRAY}techo {to_euros(wm.get_category_budget(r))},"
                    f" sin desglosar {to_euros(wm.get_category_billable(r))}{p.RESET}",
                )
                for r in roots
            ],
        )
    )

    ceiling = wm.get_category_budget(parent)
    if ceiling == 0:
        p.warn(
            f"'{parent}' tiene techo 0. Ponle presupuesto antes, o cualquier"
            " importe de una hija se saldrá del techo."
        )

    name = ask_text("Nombre de la subcategoría")
    if not guarded(
        conn, wm.add_category, name, parent=parent, success=f"'{name}' creada bajo {parent}"
    ):
        return

    libre = wm.get_category_billable(parent)
    p.info(f"Sin desglosar en '{parent}' quedan {to_euros(libre)}.")
    if ask_yes_no("¿Le pones importe ahora?", default=True):
        amount = ask_float(f"Importe de {name} (€)")
        guarded(
            conn, wm.set_budget_for_category, name, amount, success="Importe fijado"
        )


def action_remove_category(wm: WorkflowManager, conn) -> None:
    category = str(
        choose(
            "¿Qué categoría borras?",
            [
                (c, f"{c.title()}  {p.GRAY}{to_euros(wm.get_category_budget(c))}{p.RESET}")
                for c in wm.get_active_categories()
            ],
        )
    )
    p.muted("  Los gastos de una hija suben a su padre. Una raíz con gastos no se borra.")
    if not ask_yes_no(f"¿Seguro que borras '{category}'?", default=False):
        return
    guarded(conn, wm.remove_category, category, success=f"'{category}' borrada")


def action_standard_categories(wm: WorkflowManager, conn) -> None:
    p.info("Repone fijos, variables y reserva si alguna falta. No toca las que ya están.")
    guarded(conn, wm.set_standard_categories, success="Categorías estándar repuestas")


def action_set_debt_installment(wm: WorkflowManager, conn) -> None:
    options: list[tuple[object, str]] = []
    for member, data in wm.get_all_debts_summary().items():
        for bucket_id, bucket in data["buckets"].items():
            options.append(
                (
                    bucket_id,
                    f"{member.title()} — {bucket['name']}"
                    f"  {p.GRAY}cuota actual {to_euros(bucket['installment'])}{p.RESET}",
                )
            )

    bucket_id = choose("¿A qué deuda le cambias la cuota?", options)
    amount = ask_float("Nueva cuota mensual (€)")
    guarded(
        conn,
        wm.set_debt_bucket_installment,
        bucket_id,
        amount,
        success=f"Cuota cambiada a {amount:.2f} €",
    )


def action_validate_debt_capacity(wm: WorkflowManager, conn) -> None:
    """Comprueba que la deuda cabe en la reserva de cada uno, antes de congelar."""
    if wm.current_phase is not Phase.PLANNING:
        p.info(
            "Esta comprobación solo se hace planificando: el acuerdo ya está"
            " congelado. Aquí abajo tienes la reserva que le queda a cada uno."
        )
        show_missing_money(wm)
        return

    p.info("La deuda de cada miembro no puede superar su parte de reserva.")
    if guarded(conn, wm.validate_debt_doesnt_exceed_capacity):
        p.ok("La deuda cabe en la reserva de todos.")
    show_missing_money(wm)


def action_add_debt(wm: WorkflowManager, conn) -> None:
    owner = str(
        choose(
            "¿De quién es la deuda?",
            [(m, m.title()) for m in wm.get_registered_members()],
        )
    )
    name = ask_text("Nombre de la deuda (ej: financiación coche)")
    principal = ask_float("Importe total pendiente (€)")
    installment = ask_float("Cuota mensual (€)")
    description = ask_text("Descripción", default="")

    guarded(
        conn,
        wm.add_debt_bucket,
        name=name,
        principal_euros=principal,
        owner=owner,
        installment_euros=installment,
        description=description,
        success=f"Deuda '{name}' declarada para {owner.title()}",
    )


def action_create_bucket(wm: WorkflowManager, conn) -> None:
    name = ask_text("Nombre del bucket (ej: vacaciones verano)")

    owners = []
    for member in wm.get_registered_members():
        if ask_yes_no(f"¿{member.title()} participa en este bucket?", default=True):
            owners.append(member)
    if not owners:
        p.warn("Un bucket necesita al menos un propietario.")
        return

    has_goal = ask_yes_no("¿Tiene meta de dinero?", default=False)
    goal = ask_float("Meta (€)") if has_goal else None

    months = None
    if has_goal and ask_yes_no("¿Tiene fecha límite?", default=False):
        months = ask_int("¿Dentro de cuántos meses?")

    description = ask_text("Descripción", default="")

    guarded(
        conn,
        wm.create_saving_bucket,
        bucket_name=name,
        owners=owners,
        goal_euros=goal,
        deadline_in_months=months,
        description=description,
        success=f"Bucket '{name}' creado",
    )


def action_finish_planning(wm: WorkflowManager, conn) -> None:
    show_budget(wm)
    show_contributions(wm)
    p.warn("Al cerrar la planificación, los ingresos y el acuerdo se congelan.")
    if not ask_yes_no("¿Cerrar la planificación y empezar el mes?", default=False):
        return
    guarded(conn, wm.finish_planning, success="Planificación congelada. Fase: MONTH")


# ══════════════════════════════════════════════════════════════════
# ACCIONES — MONTH
# ══════════════════════════════════════════════════════════════════


def _ask_participants(wm: WorkflowManager, payer: str, category: str) -> list[str] | None:
    """Quién comparte el gasto. Devolver None deja decidir a la categoría.

    Un gasto entra en el settlement cuando tiene más de un participante
    (Expense.is_shared es len(participants) > 1). La categoría solo decide el
    valor por defecto: 'fijos' viene compartida, 'variables' viene personal.
    Por eso hace falta poder decirlo gasto a gasto — si no, una compra grande
    en 'variables' que pagáis a medias nunca aparecería en el settlement.
    """
    members = wm.get_registered_members()
    is_shared_default = wm.household.budget.get_category(category).is_shared
    por_defecto = "entre todos" if is_shared_default else f"solo {payer.title()}"

    choice = choose(
        f"¿Quién comparte este gasto?  (por defecto: {por_defecto})",
        [
            ("DEFAULT", f"Lo que diga la categoría — {por_defecto}"),
            ("ALL", "Entre todos los miembros del hogar"),
            ("ONLY", f"Solo {payer.title()} (personal, fuera del settlement)"),
            ("PICK", "Elegir quién participa"),
        ],
    )

    if choice == "DEFAULT":
        return None
    if choice == "ALL":
        return list(members)
    if choice == "ONLY":
        return [payer]

    picked = [m for m in members if ask_yes_no(f"¿Participa {m.title()}?", default=True)]
    if not picked:
        p.warn("Nadie participa: el gasto queda a nombre de quien lo pagó.")
        return [payer]
    return picked


def action_register_expense(wm: WorkflowManager, conn) -> None:
    member = str(
        choose("¿Quién ha pagado?", [(m, m.title()) for m in wm.get_registered_members()])
    )
    category = str(
        choose(
            "¿En qué categoría?",
            [
                (
                    c,
                    f"{c.title()}  {p.GRAY}queda {to_euros(wm.get_category_remaining(c))}"
                    f"  ·  {'compartida' if wm.household.budget.get_category(c).is_shared else 'personal'}{p.RESET}",
                )
                for c in wm.get_active_categories()
            ],
        )
    )
    amount = ask_float("Importe (€)")
    description = ask_text("Concepto", default=category)
    participants = _ask_participants(wm, member, category)

    reparto = (
        "según la categoría"
        if participants is None
        else ", ".join(x.title() for x in participants)
    )
    guarded(
        conn,
        wm.register_expense,
        member=member,
        category=category,
        amount_euros=amount,
        description=description,
        participants=participants,
        success=f"{amount:.2f} € en {category} — pagó {member.title()}, reparto: {reparto}",
    )


def action_pay_debt(wm: WorkflowManager, conn) -> None:
    options: list[tuple[object, str]] = []
    for member, data in wm.get_all_debts_summary().items():
        for bucket_id, bucket in data["buckets"].items():
            if bucket["is_closed"]:
                continue
            pending = bucket["period"]["remaining"]
            options.append(
                (
                    (member, bucket_id),
                    f"{member.title()} — {bucket['name']}"
                    f"  {p.GRAY}(cuota {to_euros(bucket['installment'])},"
                    f" falta {to_euros(pending)} este mes){p.RESET}",
                )
            )

    member, bucket_id = choose("¿Qué deuda pagas?", options)  # type: ignore[misc]
    amount = ask_float("Importe del pago (€)")

    guarded(
        conn,
        wm.register_debt_payment,
        member=str(member),
        bucket_id=UUID(str(bucket_id)) if not isinstance(bucket_id, UUID) else bucket_id,
        amount_euros=amount,
        success=f"Pago de {amount:.2f} € registrado",
    )


def _pick_bucket(wm: WorkflowManager) -> tuple[UUID, object]:
    buckets = wm.get_all_buckets()
    options = []
    for bucket_id, bucket in buckets.items():
        meta = f" / {to_euros(bucket.goal)}" if bucket.goal else " (sin meta)"
        owners = ", ".join(o.title() for o in bucket.owners)
        options.append(
            (
                bucket_id,
                f"{bucket.bucket_name}  {p.GRAY}{to_euros(bucket.balance)}{meta}"
                f"  ·  {owners}{p.RESET}",
            )
        )
    bucket_id = choose("¿Qué bucket?", options)
    return bucket_id, buckets[bucket_id]  # type: ignore[index]


def action_deposit(wm: WorkflowManager, conn) -> None:
    bucket_id, bucket = _pick_bucket(wm)
    member = str(
        choose("¿Quién deposita?", [(o, o.title()) for o in bucket.owners])  # type: ignore[attr-defined]
    )
    amount = ask_float("Importe a depositar (€)")

    guarded(
        conn,
        wm.deposit_to_saving_bucket,
        bucket_id=bucket_id,
        member=member,
        amount_euros=amount,
        success=f"{amount:.2f} € depositados",
    )


def action_withdraw(wm: WorkflowManager, conn) -> None:
    bucket_id, bucket = _pick_bucket(wm)
    member = str(
        choose("¿Quién retira?", [(o, o.title()) for o in bucket.owners])  # type: ignore[attr-defined]
    )
    amount = ask_float("Importe a retirar (€)")

    guarded(
        conn,
        wm.withdraw_from_saving_bucket,
        bucket_id=bucket_id,
        member=member,
        amount_euros=amount,
        success=f"{amount:.2f} € retirados",
    )


def action_finish_month(wm: WorkflowManager, conn) -> None:
    p.info(
        "La ventana del período es [inicio, fin): el día de cierre es exclusivo,"
        " así pertenece solo al mes que empieza."
    )
    p.muted("  Por eso el valor por defecto es mañana: si cierras hoy, lo registrado")
    p.muted("  hoy quedaría fuera de su propio mes.")
    end = ask_date("Fecha de cierre", date.today() + timedelta(days=1))
    if not ask_yes_no(f"¿Cerrar el mes el {end.strftime('%d/%m/%Y')}?", default=False):
        return
    guarded(conn, wm.finish_month, end_date=end, success="Mes cerrado")


# ══════════════════════════════════════════════════════════════════
# MENÚS POR FASE
# ══════════════════════════════════════════════════════════════════

def action_new_month(wm: WorkflowManager, conn) -> None:
    default = wm.period.end_date if wm.period and wm.period.end_date else date.today()
    while True:
        start = ask_date("Fecha de inicio del mes nuevo", default)
        if guarded(conn, wm.start_new_month, start_date=start, success="Mes nuevo abierto"):
            return
        if not ask_yes_no("¿Probar con otra fecha?", default=True):
            return


# Cada entrada: (etiqueta, destino, tipo)
#   "action" → destino(wm, conn)   ·   "view" → destino(wm)   ·   "menu" → submenú
MEMBERS_MENU = [
    ("Registrar un miembro", action_add_member, "action"),
    ("Cambiar el ingreso de alguien", action_set_income, "action"),
    ("Ver miembros e ingresos", show_members, "view"),
]

CATEGORIES_MENU = [
    ("Crear una categoría raíz", action_add_root_category, "action"),
    ("Crear una subcategoría", action_add_subcategory, "action"),
    ("Borrar una categoría", action_remove_category, "action"),
    ("Reponer las categorías estándar", action_standard_categories, "action"),
    ("Ver el presupuesto", show_budget, "view"),
]

BUDGET_MENU = [
    ("Presupuestar por porcentajes", action_budget_by_percentages, "action"),
    ("Presupuestar una raíz desde sus gastos", action_budget_bottom_up, "action"),
    ("Poner importe a una categoría", action_set_category_amount, "action"),
    ("Ver el presupuesto", show_budget, "view"),
    ("Ver la reserva sin destino", show_missing_money, "view"),
]

SPLIT_MENU = [
    ("Elegir el método de reparto", action_set_method, "action"),
    ("Comparar los tres métodos", show_method_comparison, "view"),
    ("Ver quién pone qué", show_contributions, "view"),
]

DEBT_MENU = [
    ("Declarar una deuda", action_add_debt, "action"),
    ("Cambiar la cuota de una deuda", action_set_debt_installment, "action"),
    ("Comprobar que la deuda cabe en la reserva", action_validate_debt_capacity, "action"),
    ("Ver la deuda del hogar", show_debts, "view"),
    ("Ver la deuda de un miembro", show_member_debt, "view"),
]

SAVING_MENU = [
    ("Crear un bucket de ahorro", action_create_bucket, "action"),
    ("Ver los buckets", show_buckets, "view"),
    ("Ver el ahorro de un miembro", show_member_saving, "view"),
    ("Ver el ahorro compartido", show_shared_savings, "view"),
]

VIEWS_MENU = [
    ("Resumen del mes", show_month_summary, "view"),
    ("Settlement — quién debe a quién", show_settlement, "view"),
    ("Gastos del período, uno a uno", show_expenses, "view"),
    ("Estado de un miembro", show_member_status, "view"),
    ("Presupuesto", show_budget, "view"),
    ("Quién pone qué", show_contributions, "view"),
    ("Deuda del hogar", show_debts, "view"),
    ("Deuda de un miembro", show_member_debt, "view"),
    ("Buckets de ahorro", show_buckets, "view"),
    ("Ahorro de un miembro", show_member_saving, "view"),
    ("Ahorro compartido", show_shared_savings, "view"),
    ("Reserva sin destino", show_missing_money, "view"),
    ("Miembros e ingresos", show_members, "view"),
]

PLANNING_ENTRIES = [
    ("Miembros e ingresos", MEMBERS_MENU, "menu"),
    ("Categorías", CATEGORIES_MENU, "menu"),
    ("Presupuesto", BUDGET_MENU, "menu"),
    ("Reparto entre miembros", SPLIT_MENU, "menu"),
    ("Deuda", DEBT_MENU, "menu"),
    ("Ahorro", SAVING_MENU, "menu"),
    ("Ver el plan completo", show_plan, "view"),
    ("Cerrar la planificación y empezar el mes", action_finish_planning, "action"),
]

MONTH_ENTRIES = [
    ("Registrar un gasto", action_register_expense, "action"),
    ("Registrar un pago de deuda", action_pay_debt, "action"),
    ("Depositar en un bucket", action_deposit, "action"),
    ("Retirar de un bucket", action_withdraw, "action"),
    ("Consultar", VIEWS_MENU, "menu"),
    ("Deuda", DEBT_MENU, "menu"),
    ("Ahorro", SAVING_MENU, "menu"),
    ("Cerrar el mes", action_finish_month, "action"),
]

CLOSING_ENTRIES = [
    ("Consultar", VIEWS_MENU, "menu"),
    ("Abrir un mes nuevo", action_new_month, "action"),
]


def phase_entries(wm: WorkflowManager) -> list:
    if wm.current_phase is Phase.PLANNING:
        return PLANNING_ENTRIES
    if wm.current_phase is Phase.MONTH:
        return MONTH_ENTRIES
    return CLOSING_ENTRIES


def _menu_options(entries: list) -> list[tuple[object, str]]:
    """Convierte las entradas en opciones para `choose`, marcando cada tipo."""
    options: list[tuple[object, str]] = []
    for text, target, kind in entries:
        if kind == "menu":
            shown = f"{text} {p.GRAY}▸{p.RESET}"
        elif kind == "view":
            shown = f"{p.GRAY}{text}{p.RESET}"
        else:
            shown = text
        options.append(((target, kind, text), shown))
    return options


def run_menu(wm: WorkflowManager, conn, label: str, entries: list) -> None:
    """Muestra un menú y ejecuta lo elegido. Los submenús se anidan aquí mismo."""
    while True:
        try:
            target, kind, text = choose(label, _menu_options(entries))  # type: ignore[misc]
        except Back:
            return

        try:
            if kind == "menu":
                run_menu(wm, conn, str(text), target)  # type: ignore[arg-type]
            elif kind == "view":
                target(wm)  # type: ignore[operator]
            else:
                target(wm, conn)  # type: ignore[operator]
        except Back:
            p.muted("  (cancelado)")
        except ValueError as exc:
            conn.rollback()
            p.error(str(exc))


def session_loop(wm: WorkflowManager, conn, repos: dict) -> None:
    while True:
        show_header(wm)

        entries = phase_entries(wm) + [("Salir", None, "view")]
        options = _menu_options(entries)

        try:
            target, kind, text = choose(  # type: ignore[misc]
                f"¿Qué haces? (fase {wm.current_phase.value.upper()})", options
            )
        except Back:
            if ask_yes_no("¿Salir de Kogar?", default=False):
                return
            continue

        if target is None:
            return

        try:
            if kind == "menu":
                run_menu(wm, conn, str(text), target)  # type: ignore[arg-type]
            elif kind == "view":
                target(wm)  # type: ignore[operator]
            else:
                target(wm, conn)  # type: ignore[operator]
        except Back:
            p.muted("  (cancelado)")
        except ValueError as exc:
            conn.rollback()
            p.error(str(exc))


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════


def main() -> int:
    p.banner("KOGAR", "cli desechable")

    if not DB_NAME:
        p.error("No hay configuración de BD. Revisa el .env (DB_NAME, DB_USER, ...).")
        return 1

    try:
        with DatabaseConnection(
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
        ) as conn:
            repos = build_repos(conn)

            try:
                wm = open_session(repos, conn)
            except Back:
                p.muted("  Hasta luego.")
                return 0

            if wm is None:
                return 0

            session_loop(wm, conn, repos)
            conn.commit()

    except psycopg2.OperationalError as exc:
        p.error(f"No se pudo conectar a PostgreSQL: {str(exc).strip()}")
        return 1

    p.blank()
    p.ok("Sesión cerrada. Todo lo confirmado está en la BD.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
