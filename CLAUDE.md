# CLAUDE.md — Estado del proyecto Kogar y tareas para cerrar dominio

## Qué es Kogar

Aplicación de finanzas para parejas. Cada miembro declara ingresos, se presupuestan categorías (fijos, variables, reserva), se reparte proporcionalmente (o igual, o custom), y durante el mes se registran gastos, pagos de deuda y depósitos de ahorro. Al cierre, el settlement calcula quién debe a quién.

**Stack:** Python, pytest. Sin UI/API todavía.

---

## Arquitectura actual

```
WorkflowManager (fachada pública, controla fases)
  └── Household (núcleo de dominio, orquesta todo)
        ├── Budget
        │     ├── BudgetCategory (fijos, variables, reserva)
        │     └── CategoryLibrary (estándar + extended + custom)
        ├── ExpenseTracker
        │     └── Expense
        ├── SavingTracker
        │     ├── SavingAccount (una por miembro)
        │     │     └── SavingEntry
        │     └── BucketTracker
        │           └── SavingBucket
        │                 └── BucketEntry
        ├── DebtTracker (NUEVO, no integrado aún)
        │     ├── DebtAccount (una por miembro)
        │     └── DebtEntry
        ├── FinanceCalculator (estático, sin estado)
        └── Member
```

**Flujo de fases:** `REGISTRATION → PLANNING → MONTH → CLOSING`

**Convenciones:** céntimos (int) internamente, snake_case, nombres normalizados a lowercase, tests con pytest + fixtures.

---

## Estado actual por módulo

| Módulo | Estado | Tests |
|---|---|---|
| Member | ✅ Completo | ✅ |
| Budget + BudgetCategory | ✅ Completo | ✅ |
| CategoryLibrary | ✅ Completo | ✅ |
| FinanceCalculator | ✅ Completo (incluye `calculate_budget_from_percentages`) | ✅ 28 tests |
| Expense | ✅ Completo | ✅ |
| ExpenseTracker | ✅ Completo | ✅ 32 tests |
| SavingEntry | ✅ Completo | ✅ 5 tests |
| SavingAccount | ✅ Completo | ✅ 22 tests |
| SavingTracker | ⚠️ Funcional, falta integrar BucketTracker completo | ✅ 16 tests |
| SavingBucket | ⚠️ Código existe, 0 tests | ❌ 0 tests |
| BucketTracker | ⚠️ Código existe, tests parciales | ⚠️ 13 tests |
| BucketEntry | ✅ Completo | ✅ |
| DebtEntry | 🆕 Creado, no integrado | ❌ Sin tests |
| DebtAccount | 🆕 Creado, no integrado | ❌ Sin tests |
| DebtTracker | 🆕 Creado, no integrado | ❌ Sin tests |
| Household | ⚠️ Funcional pero tests desactualizados tras cambios recientes | ⚠️ 119 tests (algunos rotos) |
| WorkflowManager | ⚠️ Funcional, no expone debt ni nuevos métodos | ⚠️ Sin archivo test propio |

---

## Cambios recientes (esta sesión, no integrados completamente)

### 1. Presupuestos por porcentajes — `calculate_budget_from_percentages`
- **Estado:** Calculator actualizado con largest remainder method. Household tiene `set_budget_by_percentages` que salta reserva.
- **Pendiente:** Tests nuevos para este método en test_calculator.py y test_household.py.

### 2. Reserva se autocalcula
- **Estado:** `set_budget_for_category` bloquea setear "reserva" directamente y la recalcula como complemento.
- **Pendiente:** Tests existentes de `set_budget_for_category` probablemente rotos (asumen que se puede setear reserva). Actualizar.

### 3. DebtTracker (nuevo)
- **Estado:** DebtEntry, DebtAccount, DebtTracker creados como archivos sueltos. NO integrados en Household ni WorkflowManager.
- **Pendiente:** Todo (ver Tarea 2 abajo).

### 4. `auto_assign_saving_goals`
- **Estado:** Propuesto, no implementado en el código del proyecto.
- **Pendiente:** Implementar en Household (ver Tarea 3 abajo).

---

## TAREAS PARA LLEGAR A PERSISTENCIA + CLI

Orden estricto. No saltar tareas. Cada tarea incluye criterio de "terminado".

---

### TAREA 1 — Estabilizar tests existentes

**Por qué:** Los cambios de esta sesión (reserva autocalculada, set_budget_by_percentages) probablemente rompieron tests existentes. No se puede construir encima de tests rotos.

**Pasos:**
1. Ejecutar `pytest` completo. Anotar qué tests fallan.
2. Para cada test roto, evaluar: ¿el test es obsoleto (testeaba comportamiento viejo) o el código tiene un bug?
3. Actualizar tests de `set_budget_for_category` para que no intenten setear "reserva" directamente.
4. Añadir tests nuevos:
   - `test_set_budget_for_category_blocks_reserva` → ValueError
   - `test_set_budget_for_category_autocalculates_reserva` → fijos + variables + reserva == total_incomes
   - `test_set_budget_for_category_reassign_doesnt_double_count` → cambiar fijos de 400 a 500, reserva se recalcula bien
   - `test_set_budget_by_percentages_sum_matches_incomes` → con ingresos 100001 y pct 50/30/20
   - `test_set_budget_by_percentages_skips_reserva` → reserva no se pasa al set sino que se autocalcula
   - `test_calculate_budget_from_percentages_validates_sum_10000` → ValueError si no suma 10000
   - `test_calculate_budget_from_percentages_largest_remainder` → sin pérdida de céntimos

**Terminado cuando:** `pytest` pasa al 100%, 0 fallos.

---

### TAREA 2 — Integrar DebtTracker en el proyecto

**Por qué:** Deuda es un compromiso vacío sin ejecución. El usuario no puede registrar que pagó.

**Pasos:**

1. Mover `debt_entry.py`, `debt_account.py`, `debt_tracker.py` a `src/models/`.
2. Crear tests:
   - `test_debt_entry.py` — misma estructura que test_saving_entry.py (amount > 0, amount == 0, fecha futura)
   - `test_debt_account.py` — misma estructura que test_saving_account.py (pay, total_paid, monthly_summary, validaciones)
   - `test_debt_tracker.py` — misma estructura que test_saving_tracker.py (create_account, pay, get_total_paid, get_member_summary)
3. Integrar en `Household.__init__`:
   - Nuevo parámetro `debt_tracker: DebtTracker`
   - En `register_member`: `self.debt_tracker.create_account(member.name)`
   - En `freeze_registration_state`: `self.debt_tracker.create_account(name)` junto a savings
4. Añadir métodos en Household:
   ```python
   def register_debt_payment(self, member_name, amount_cents, description="", date=None)
   def get_debt_status(self, member_name) -> dict  # {committed, paid, remaining}
   ```
   - `register_debt_payment` valida: miembro existe, pago > 0, paid + amount <= committed
5. Exponer en WorkflowManager:
   ```python
   def register_debt_payment(self, member, amount_euros, description="", date=None)
   ```
   - Valida fase MONTH
6. Actualizar TODOS los lugares donde se instancia Household en tests:
   - Crear fixture `debt_tracker` y pasarla a Household
   - Si no se pasa, los tests viejos pecan. Revisar todas las fixtures de test_household.py.
7. Tests de integración en test_household.py:
   - `test_register_debt_payment_basic`
   - `test_register_debt_payment_exceeds_commitment_raises`
   - `test_get_debt_status_after_partial_payment`
   - `test_get_debt_status_after_full_payment`

**Terminado cuando:** `pytest` pasa al 100%. Se puede registrar un pago de deuda y consultar progreso.

---

### TAREA 3 — Implementar `auto_assign_saving_goals`

**Por qué:** El sobrante de reserva tras deuda no tiene destino. El ahorro debe autocalcularse como reserva_miembro - deuda_miembro.

**Pasos:**
1. Implementar en Household:
   ```python
   def auto_assign_saving_goals(self):
       contributions = self.get_current_contributions()
       reserva_contributions = contributions.get("reserva", {}).get("contributions", {})
       for member in self.members:
           capacity = reserva_contributions.get(member, 0)
           debt = self._member_debts.get(member, 0)
           self._saving_goals[member] = capacity - debt
   ```
2. Implementar `get_saving_goal_status` en Household:
   ```python
   def get_saving_goal_status(self, member_name) -> dict  # {committed, paid, remaining}
   ```
3. Tests:
   - `test_auto_assign_saving_goals_basic` → dos miembros, deuda distinta, ahorro = reserva - deuda
   - `test_auto_assign_saving_goals_no_debt` → sin deuda, ahorro == cuota reserva completa
   - `test_auto_assign_saving_goals_proportional` → reparto proporcional, cuotas de reserva distintas
   - `test_get_saving_goal_status_after_deposit`

**Terminado cuando:** `pytest` pasa. `auto_assign_saving_goals` calcula correctamente con cualquier método de reparto.

---

### TAREA 4 — Cerrar SavingBucket + BucketTracker

**Por qué:** Está a medio hacer. 0 tests en SavingBucket, integración incompleta en SavingTracker.

**Pasos:**
1. Escribir tests para SavingBucket:
   - Creación con/sin goal, con/sin deadline
   - deposit y withdraw por miembro
   - balance, balance_by_member
   - Validaciones: miembro no en bucket, monto inválido, saldo insuficiente
2. Completar integración BucketTracker ↔ SavingTracker:
   - Verificar que SavingTracker expone métodos de bucket (deposit_to_bucket, withdraw_from_bucket, get_bucket_summary)
   - Si no los expone, añadirlos
3. Exponer en Household los métodos de bucket que falten
4. Exponer en WorkflowManager
5. Tests de integración

**Terminado cuando:** Flujo completo funciona: crear bucket → depositar → consultar balance → retirar. Todo con tests.

---

### TAREA 5 — Limpiar WorkflowManager

**Por qué:** WM tiene métodos obsoletos (`set_budget_by_percentage` singular en línea 80) y no expone los métodos nuevos.

**Pasos:**
1. Eliminar `set_budget_by_percentage` (singular) de WM — ya no existe en Household.
2. Añadir `set_budget_by_percentages` (plural) en WM con validación de fase PLANNING.
3. Añadir `register_debt_payment` en WM (si no se hizo en Tarea 2).
4. Añadir `get_debt_status` y `get_saving_goal_status` en WM.
5. Revisar `apply_percentage_distribution` — probablemente obsoleto o redundante con `set_budget_by_percentages`. Si lo es, eliminar.
6. Crear `test_workflow_manager.py` con tests de integración:
   - Flujo completo REGISTRATION → PLANNING → MONTH → CLOSING
   - Validaciones de fase (intentar registrar gasto en PLANNING → error)
   - Debt payment en MONTH
   - Settlement al cierre

**Terminado cuando:** WM es la fachada completa. Cualquier operación que Household pueda hacer, WM la expone con validación de fase.

---

## Qué NO hacer hasta terminar las 5 tareas

- Transferencias internas entre montos
- Categorías custom creadas por el usuario en MONTH
- Cuentas bancarias reales
- Analytics, gráficos, exportación
- Método de reparto por categoría
- Subcategorías
- Persistencia, CLI, ciclo mensual (`start_new_month`)

Todo esto va a `TODO.md > v2`. No se toca hasta cerrar las 5 tareas de dominio.

---

## Reglas de negocio que no se rompen

- `sum(fijos + variables + reserva) == total_incomes` siempre
- Reserva se autocalcula, nunca se setea desde fuera
- No registrar gastos ni deuda ni ahorro fuera de fase MONTH
- No modificar ingresos tras freeze_registration_state
- `amount` siempre > 0, ingresos siempre >= 0
- Settlement solo opera sobre gastos con `is_shared=True`
- `deuda + ahorro <= cuota_reserva_miembro`
- Nombres normalizados a lowercase en punto de entrada