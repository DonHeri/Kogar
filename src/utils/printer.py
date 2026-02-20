"""
printer.py - Arsenal de impresión para CLI financiero
Zero dependencias externas. Todo ANSI puro.
"""
# pragma: no cover
# ─────────────────────────────────────────────
# ANSI CODES
# ─────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDER = "\033[4m"
BLINK = "\033[5m"  # usar con moderación
STRIKE = "\033[9m"

# Foreground
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
GRAY = "\033[90m"

# Bright Foreground
BRED = "\033[91m"
BGREEN = "\033[92m"
BYELLOW = "\033[93m"
BBLUE = "\033[94m"
BMAGENTA = "\033[95m"
BCYAN = "\033[96m"
BWHITE = "\033[97m"

# Background
BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"
BG_WHITE = "\033[47m"
BG_GRAY = "\033[100m"


# ─────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────
def _ansi_len(text: str) -> int:
    """Longitud visual ignorando secuencias ANSI."""
    import re

    return len(re.sub(r"\033\[[0-9;]*m", "", text))


def _pad(text: str, width: int, align: str = "left") -> str:
    """Pad teniendo en cuenta códigos ANSI invisibles."""
    visible = _ansi_len(text)
    spaces = max(0, width - visible)
    if align == "center":
        l = spaces // 2
        r = spaces - l
        return " " * l + text + " " * r
    elif align == "right":
        return " " * spaces + text
    return text + " " * spaces


# ─────────────────────────────────────────────
# TÍTULOS Y SECCIONES
# ─────────────────────────────────────────────
def title(text: str, width: int = 60, color: str = CYAN) -> None:
    """Título principal con doble borde."""
    bar = "═" * width
    inner = _pad(f"  {text.upper()}  ", width, "center")
    print(f"\n{BOLD}{color}╔{bar}╗")
    print(f"║{inner}║")
    print(f"╚{bar}╝{RESET}\n")


def section(text: str, width: int = 50, color: str = MAGENTA) -> None:
    """Sección con borde simple."""
    bar = "─" * width
    inner = _pad(f" {text} ", width, "center")
    print(f"\n{BOLD}{color}┌{bar}┐")
    print(f"│{inner}│")
    print(f"└{bar}┘{RESET}")


def subtitle(text: str, color: str = BYELLOW) -> None:
    """Subtítulo con línea decorativa inferior."""
    print(f"\n{BOLD}{color}{text}{RESET}")
    print(f"{DIM}{color}{'▸' * (len(text) + 2)}{RESET}")


def divider(char: str = "─", width: int = 54, color: str = GRAY) -> None:
    """Separador horizontal simple."""
    print(f"{color}{char * width}{RESET}")


def blank() -> None:
    print()


# ─────────────────────────────────────────────
# MENSAJES DE ESTADO
# ─────────────────────────────────────────────
def ok(text: str) -> None:
    print(f"{GREEN}✓ {text}{RESET}")


def warn(text: str) -> None:
    print(f"{BYELLOW}⚠ {text}{RESET}")


def error(text: str) -> None:
    print(f"{BRED}✗ {text}{RESET}")


def info(text: str) -> None:
    print(f"{CYAN}ℹ {text}{RESET}")


def tip(text: str) -> None:
    print(f"{DIM}{BCYAN}💡 {text}{RESET}")


def muted(text: str) -> None:
    print(f"{DIM}{GRAY}{text}{RESET}")


# ─────────────────────────────────────────────
# DATOS FINANCIEROS
# ─────────────────────────────────────────────
def amount_positive(label: str, value: str) -> None:
    """Importe positivo (ingreso, superávit)."""
    print(f"  {WHITE}{label:<28}{RESET}{BOLD}{BGREEN}{value:>12}{RESET}")


def amount_negative(label: str, value: str) -> None:
    """Importe negativo (gasto, déficit)."""
    print(f"  {WHITE}{label:<28}{RESET}{BOLD}{BRED}{value:>12}{RESET}")


def amount_neutral(label: str, value: str) -> None:
    """Importe neutro (presupuestado, pendiente)."""
    print(f"  {WHITE}{label:<28}{RESET}{BOLD}{BYELLOW}{value:>12}{RESET}")


def amount_auto(label: str, value: float, formatter=None) -> None:
    """
    Elige color automáticamente según signo.
    formatter: callable que convierte float → str (ej: to_euros)
    """
    fmt = formatter(value) if formatter else f"{value:.2f}"
    if value > 0:
        amount_positive(label, fmt)
    elif value < 0:
        amount_negative(label, fmt)
    else:
        amount_neutral(label, fmt)


def percentage_bar(label: str, pct: float, width: int = 20, color: str = CYAN) -> None:
    """
    Barra de progreso visual para porcentajes.
    pct: 0.0 a 100.0
    """
    filled = int((pct / 100) * width)
    empty = width - filled
    bar = f"{color}{'█' * filled}{DIM}{'░' * empty}{RESET}"
    print(f"  {WHITE}{label:<20}{RESET} {bar} {BOLD}{color}{pct:6.2f}%{RESET}")


def member_contribution(name: str, amount: str, budget: str, pct: float) -> None:
    """Fila compacta para contribución de un miembro."""
    pct_color = BGREEN if pct <= 50 else BYELLOW
    print(
        f"  {BOLD}{WHITE}{name:<12}{RESET}"
        f"{CYAN}{amount:>10}{RESET}"
        f"{GRAY}  /  {budget}{RESET}"
        f"  {pct_color}({pct:.1f}%){RESET}"
    )


# ─────────────────────────────────────────────
# TABLAS SIMPLES
# ─────────────────────────────────────────────
def table(
    headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None
) -> None:
    """
    Tabla ASCII alineada correctamente.
    El truco: pad ANTES de añadir color, así f-string nunca ve los códigos ANSI.

    Uso:
        table(
            headers=["Categoría", "Presupuesto", "Amanda", "Heri"],
            rows=[
                ["Fijos", "900 €", "487 €", "413 €"],
                ["Variables", "300 €", "163 €", "137 €"],
            ],
            col_widths=[14, 12, 10, 10]  # opcional
        )
    """
    if col_widths is None:
        col_widths = [
            max(len(str(row[i])) for row in ([headers] + rows)) + 2
            for i in range(len(headers))
        ]

    def _render_row(cells, color="", bold=""):
        parts = []
        for cell, w in zip(cells, col_widths):
            # Pad primero sobre texto limpio, luego envuelve en color
            padded = f"{str(cell):<{w}}"
            parts.append(f"{bold}{color}{padded}{RESET}")
        return f"  │ {'│ '.join(parts)}│"

    total_width = sum(col_widths) + len(col_widths) * 3 + 1

    print(f"\n  {CYAN}┌{'─' * total_width}┐{RESET}")
    print(_render_row(headers, color=BCYAN, bold=BOLD))
    print(f"  {CYAN}├{'─' * total_width}┤{RESET}")

    for i, row in enumerate(rows):
        color = GRAY if i % 2 != 0 else WHITE
        print(_render_row(row, color=color))

    print(f"  {CYAN}└{'─' * total_width}┘{RESET}\n")


# ─────────────────────────────────────────────
# CUADROS DE RESUMEN (KEY-VALUE)
# ─────────────────────────────────────────────
def summary_box(title_text: str, items: dict, color: str = CYAN) -> None:
    """
    Caja de resumen con pares clave-valor.

    items = {"Total ingresos": "2.800 €", "Total gastos": "1.550 €"}
    """
    max_key = max(len(k) for k in items)
    width = max_key + 20

    print(
        f"\n  {BOLD}{color}┌─ {title_text.upper()} {'─' * (width - len(title_text) - 2)}┐{RESET}"
    )
    for k, v in items.items():
        print(
            f"  {color}│{RESET}  {WHITE}{k:<{max_key}}{RESET}  {BOLD}{BGREEN}{v:>10}{RESET}  {color}│{RESET}"
        )
    print(f"  {BOLD}{color}└{'─' * (width + 2)}┘{RESET}\n")


# ─────────────────────────────────────────────
# BANNER / SPLASH
# ─────────────────────────────────────────────
def banner(app_name: str = "FINANZAS PRO", version: str = "v1.0") -> None:
    """Splash screen minimalista al arrancar."""
    lines = [
        f"  {BOLD}{BGREEN}{'█' * 3} {BOLD}{BWHITE}{app_name}{RESET}",
        f"  {GRAY}{version} — Gestión de hogar compartido{RESET}",
    ]
    width = 46
    print(f"\n{BOLD}{GREEN}{'═' * width}{RESET}")
    for l in lines:
        print(l)
    print(f"{BOLD}{GREEN}{'═' * width}{RESET}\n")


# ─────────────────────────────────────────────
# DEMO  (python printer.py)
# ─────────────────────────────────────────────
if __name__ == "__main__":  # pragma: no cover
    banner()

    title("FASE 1: REGISTRO")
    ok("Household creado con método: PROPORCIONAL")
    info("Miembros cargados desde configuración")
    warn("Sin datos del mes anterior para comparar")
    error("Categoría 'ocio' sin presupuesto asignado")
    tip("Usa MetodoReparto.EQUAL si los ingresos son similares")

    section("INGRESOS DEL MES")
    amount_positive("Amanda", "1.500,00 €")
    amount_positive("Heri", "1.300,00 €")
    divider()
    amount_positive("TOTAL", "2.800,00 €")

    section("DISTRIBUCIÓN PROPORCIONAL")
    percentage_bar("Amanda", 53.57)
    percentage_bar("Heri", 46.43)

    section("CONTRIBUCIONES — FIJOS (900 €)")
    member_contribution("Amanda", "482,14 €", "900,00 €", 53.57)
    member_contribution("Heri", "417,86 €", "900,00 €", 46.43)

    subtitle("Resumen general")
    summary_box(
        "Balance del mes",
        {
            "Total ingresos": "2.800,00 €",
            "Total presupuesto": "1.550,00 €",
            "Superávit estimado": "1.250,00 €",
        },
        color=BGREEN,
    )

    table(
        headers=["Categoría", "Planeado", "Amanda", "Heri"],
        rows=[
            ["Fijos", "900 €", "482 €", "418 €"],
            ["Variables", "300 €", "161 €", "139 €"],
            ["Deuda", "350 €", "187 €", "163 €"],
        ],
        col_widths=[12, 10, 10, 10],
    )

    muted("Generado el 2025-01-01 · Finanzas Pro")
