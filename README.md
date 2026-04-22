# KOGAR

Gestión financiera para hogares compartidos. Resuelve _cuánto debe pagar cada miembro del núcleo familiar, acorde a como quieran hacer el reparto_, registra gastos del mes y calcula transferencias mínimas para saldar las cuentas.

> _Estado_: core de dominio funcional y testeado. Sin UI ni persistencia aún -- todo vive en memoria. Próxima fase SQLite.

---

## El problema

Un núcleo familiar o de confianza busca cuidar sus finanzas para perseguir metas juntas, sin complicarse en cálculos. Un miembro gana 2000€, y el otro 1500€. El alquiler son 800€. ¿Cuánto paga cada uno?.

La respuesta "400 y 400" puede parecer injusta; dejaría al segundo con menos margen. Aunque también puede ser la más simple y equitativa.
La respuesta "proporcional al sueldo" puede sonar mejor para todos. Pero los cálculos pueden quitarnos tiempo.
Si decides que lo mejor es ajustar tú mismo el porcentaje que mejor se adapta, también es una buena elección.

Con Kogar este problema se resuelve eligiendo el método que mejor se adapte a tú hogar. Además, internamente lo gestiona todo en céntimos para garantizar que _la suma de contribuciones siempre es exactamente el presupuesto_, ni más, ni menos.

---

## Qué hace hoy

- Registra miembros del hogar y sus ingresos mensuales.

- Planifica presupuesto por categorías (fijos, variables, reserva, o las que añadas), _asignable por monto o por porcentaje de ingreso_.

- Reparte cada presupuesto entre miembros según el método elegido, con precisión de céntimo.

- Registra gastos reales del mes, diferenciando compartidos vs personales.

- Gestiona ahorro (personal o compartido) y "buckets" con objetivo (vacaciones, ITV, seguro anual).

- Gestiona compromisos de pago de deuda.

- Calcula al cierre quién le debe a quién con el mínimo de transferencias posible.

## Qué NO hace todavía

- No hay interfaz de usuario (solo API de Python).

- No hay persistencia — al matar el proceso se pierde el estado.

- No hay histórico multi-mes ni comparativas.

- No hay gestión de ingresos extra ni transferencias internas entre miembros.

---

## Ejemplo mínimo

```python

from src.models.workflow_manager import WorkflowManager
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.saving_tracker import SavingTracker
from src.models.debt_tracker import DebtTracker
from src.models.constants import MetodoReparto


wm = WorkflowManager(Household(
    budget=Budget(),
    expense_tracker=ExpenseTracker(),
    saving_tracker=SavingTracker(),
    debt_tracker=DebtTracker(),
    method=MetodoReparto.PROPORTIONAL,
))

# Fase REGISTRATION
wm.register_member("Amanda")
wm.register_member("Heri")
wm.set_incomes("Amanda", 2000.0)
wm.set_incomes("Heri", 1500.0)
wm.finish_registration()

# Fase PLANNING
wm.set_budget_by_percentages({"fijos": 50.0, "variables": 20.0})
wm.finish_planning()

# Fase MONTH
wm.register_expense("Amanda", "fijos", 800.0, "Alquiler")
wm.register_expense("Heri", "variables", 120.0, "Supermercado")

# Quién le debe a quién al cerrar
print(wm.get_settlement())
# [{"from": "heri", "to": "amanda", "amount": 45714}]  (en céntimos)

```

---

## Diseño

Arquitectura en 3 capas:

- **`WorkflowManager`** — fachada pública. Valida la fase, convierte euros↔céntimos, normaliza nombres, crea objetos de dominio. Único punto de entrada desde el exterior.

- **`Household`** — núcleo de dominio. Orquesta reglas de negocio, trackers y cálculos.

- **`FinanceCalculator`** — servicio matemático puro (sin estado). Implementa reparto por _largest remainder method_ para garantizar integridad de céntimos.

**Flujo de fases** como máquina de estados explícita:

```
REGISTRATION → PLANNING → MONTH → CLOSING
```

Cada operación solo es válida en ciertas fases. Al cerrar una fase, el estado relevante se congela (snapshot inmutable) — así, si alguien edita un ingreso durante el mes, el acuerdo del mes actual no cambia.

---

### Decisiones de diseño destacables

- **Dinero siempre en céntimos (`int`) internamente.** Conversión a `float` solo en los bordes. Evita errores acumulados de coma flotante.

- **Nombres siempre normalizados a lowercase en storage** — `"Amanda" != "amanda"` es un bug que no va a existir.

- **Inyección de dependencias en `Household`** — trackers inyectados en el constructor, no instanciados internamente. Testeable.

- **Single Source of Truth por responsabilidad** — planificación vive en `Budget`, ejecución en `ExpenseTracker`, balances se derivan on-the-fly (no se guardan).

- **Inmutabilidad selectiva con `@property`** — atributos sensibles como `Expense.amount` son de solo lectura.

---

## Estructura del proyecto

```
examples/
├── full_month_simulation.py
src/
├── cli/                       ← En desarrollo (esqueleto)
├── exceptions/                ← En desarrollo (esqueleto)
├── models/
│   ├── workflow_manager.py    ← FACHADA. Único punto de entrada desde UI.
│   ├── household.py           ← Núcleo de dominio. Orquesta todo.
│   ├── finance_calculator.py  ← Matemática pura (sin estado). Reparto de céntimos.
│   │
│   ├── member.py              ← Persona con ingreso
│   ├── budget.py              ← Plan: dict de BudgetCategory
│   ├── budget_category.py     ← Una categoría con su planned_amount
│   ├── category_library.py    ← Categorías estándar + extendidas + custom
│   ├── subcategory_library.py ← Sugerencias de subcategorías (display only)
│   │
│   ├── expense.py             ← Gasto registrado
│   ├── expense_tracker.py     ← Colección de gastos del mes actual
│   │
│   ├── saving_entry.py        ← Movimiento de ahorro (dataclass inmutable)
│   ├── saving_account.py      ← Cuenta de ahorro de UN miembro
│   ├── saving_tracker.py      ← Gestor de cuentas + orquesta BucketTracker
│   ├── saving_bucket.py       ← Bote con objetivo (vacaciones, ITV...)
│   ├── bucket_entry.py        ← Movimiento de bucket (dataclass inmutable)
│   ├── bucket_tracker.py      ← Gestor de buckets
│   │
│   ├── debt_entry.py          ← Pago de deuda (dataclass inmutable)
│   ├── debt_account.py        ← Cuenta de deuda de UN miembro
│   ├── debt_tracker.py        ← Gestor de cuentas de deuda
│   └── constants.py           ← Enums: Phase, MetodoReparto, CategoryBehavior, SavingScope
│
├── storage/                   ← Futuro (persistencia)
└── utils/
    ├── currency.py            ← to_cents, to_euros, to_percentage_basis
    ├── printer.py             ← Helper de visualización (no crítico)
    └── text.py                ← normalize_name, format_name
```

---

## Cómo correr los tests

Requiere Python 3.10+.

```bash

# Instalar en modo desarrollo

pip install -e ".[dev]"


# Ejecutar todos los tests con cobertura

pytest


# Tests de un módulo concreto

pytest tests/test_household.py


# Filtrar por nombre

pytest -k settlement

```

## Licencia

MIT. Ver `LICENSE`.

---

## Notas sobre el proceso

Kogar es un proyecto de aprendizaje personal, que nace de una necesidad propia para facilitar las finanzas en el hogar.

Todo el proyecto, y su funcionamiento han sido creados y pensados por mi, usando mi propio estilo de organizar las finanzas en papel cada mes. También quiero dejar constancia de que utilicé LLM como mentor técnico, para forzarme a articular las elecciones (qué trade-off aceptaba, qué alternativa descartaba, por qué).

Me ha enseñado a tomar decisiones e integrarlas a medida que el proyecto crecía. A pensar muchas veces en el cliente, más allá de mi uso particular.
Esto último además, me enseñó la importancia de tener claro una trayectoria para el proyecto desde el comienzo, para evitar entrar en el producto infinito.

Finalmente, siento que me llevo claridad para proyectos futuros, y la satisfacción de tener un producto que pueda ir evolucionando y madurando conmigo.
