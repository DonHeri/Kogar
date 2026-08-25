# TODO — Kogar

**Propósito:** solo lo que tienes que hacer ahora o pronto.
**Cuándo escribir aquí:** cuando sabes lo que necesitas hacer a continuación.
**Cuándo borrar:** cuando lo terminas. Git es el historial, no este archivo.
**La sección COMPLETADO no existe.** Lo terminado desaparece de aquí.

---

## 🔴 Ahora

### `start_new_month` + fix `DebtTracker`

**Prerequisito — fix `DebtTracker`:**

- Añadir `DebtTracker.get_monthly_paid(member_name, month, year) -> int`
- `Household.register_debt_payment()` usa ese método con el mes/año del período activo (no `datetime.now()`)

**`Household.reset_for_new_month()`:**

- `self.expense_tracker = ExpenseTracker()`
- `self._registered_incomes = {}`
- `self._agreed_contributions = {}` · `self._agreed_percentages = {}`
- `self._member_debts = {name: 0 for name in self.members}`
- `self._saving_goals = {name: 0 for name in self.members}`

**Guard en `Household.freeze_registration_state()`:**

- `if not self.budget.categories:` antes de `budget.set_standard_categories()`

**`WorkflowManager.start_new_month(year, month)`:**

- `validate_phase(CLOSING)`
- `self.household.reset_for_new_month()`
- `self.current_phase = Phase.REGISTRATION`
- `self._completed_phases = {Phase.REGISTRATION}`
- Si `period_repo`: crear nuevo período, actualizar `self.period_id`

**Tests** — en `test_workflow_persistence.py`:

- Tras `start_new_month()` la fase es `REGISTRATION`
- Un gasto del mes anterior no aparece en el nuevo (tracker vacío)
- El límite de deuda mensual funciona correctamente en el segundo mes

`pytest -q --no-cov` verde → commit `feat: add start_new_month and fix DebtTracker monthly filter`.

---

## ⚪ Algún día

Las tres primeras son decisiones ya cerradas (ver DECISIONS.md — 26-05-26).
Su implementación queda para cuando llegue la fase correspondiente del roadmap.

- Categorías jerárquicas padre/hijo, gastos solo en hojas → roadmap Fase 2
- `income_entries` con `affects_distribution` → roadmap Fase 1
- Ingresos extras: diseño e implementación completa
- Refactorizar validaciones en módulo centralizado
- `BudgetCategory` → convertir `planned_amount` a `_planned_amount` + `@property`
- Buscador de similitudes en `CategoryLibrary` (detectar typos: "fijoss" → "fijos")
- Método de reparto por categoría (v0.3+) → añadir campo `distribution` a `Category` (ya es objeto; el cambio es aditivo, ver DECISIONS "Reparto por categoría — DIFERIDO")
- `InternalTransfer` cuando sea necesario (hoy no lo es)
- **[BUG latente] Invariante `AutoCalculatedCategory` documentado pero no defendido.** `Budget.get_auto_calculated_category()` devuelve la _primera_ auto-calculada por orden de inserción y no comprueba si hay una segunda — se la traga en silencio (la segunda queda zombi, sin recalcular). Hoy se sostiene por construcción (solo `"reserva"` es `auto_calculated` y `add_category` siempre crea con `auto_calculated=False`), pero estalla en cuanto haya otra auto-calculada en el catálogo o un `CategoryRepository` (T6) que las cargue desde BD. Delimitar: o se enforcea el "exactamente una" (conteo + `ValueError`), o se redefine el invariante.
