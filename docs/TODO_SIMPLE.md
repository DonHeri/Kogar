# ================================================ 🔴 EN CURSO ================================================

### TAREA REFACTOR: Limpiar API de métodos de reparto y organización de Household ✅ COMPLETADO

- [x] **Household - Renombrar y clarificar:** ✅
  - [x] `get_budget_contribution_summary(method)` → `preview_budget_contribution_summary(method)` (solo preview, NO modifica state) ✅
  - [x] Crear `get_current_contributions()` → Usa `self.method` ya configurado (requiere método asignado) ✅
- [x] **WorkflowManager - Exponer configuración:** ✅
  - [x] Agregar `set_custom_splits(splits: dict[str, float])` (delega a Household) ✅
  - [x] Validar fase PLANNING ✅
  - [x] Renombrar `get_budget_contribution_summary(method)` → `preview_budget_contribution_summary(method)` ✅
  - [x] Agregar `get_current_contributions()` (usa método ya configurado) ✅
- [x] **Household - Reorganizar secciones:** ✅
- [x] **Tests - Actualizar:** ✅
  - [x] Buscar todos los usos de `get_budget_contribution_summary()` en tests ✅
  - [x] Reemplazar por `preview_budget_contribution_summary()` donde sea preview ✅
  - [x] 5 tests renombrados en test_household.py ✅
- [x] **Sandbox - Actualizar:** ✅
  - [x] Agregar ejemplo de `set_custom_splits()` en sandbox_workflow.py ✅
  - [x] Usar nuevos nombres de métodos ✅
  - [x] Demostrar patrón preview vs current ✅

**Estado: ✅ COMPLETADO** - Todos los tests (252/252) pasando, sandbox actualizado y funcionando.

---

### TAREA 3.5: Cacheo de ingresos al pasar a PLANNING ✅ COMPLETADO

- [x] **Household:** Agregar atributo de caché: ✅
  - [x] `self._registered_incomes = {}` (dict con ingresos congelados por miembro) ✅
- [x] **Household.freeze_registration_state():** ✅
  - [x] Guardar `self._registered_incomes = {name: member.monthly_income, ...}` ✅
- [x] **WorkflowManager.finish_registration():** Llamar `household.freeze_registration_state()` antes de cambiar fase ✅
- [x] **Tests:** ✅
  - [x] Test que `_registered_incomes` se guarda correctamente ✅
  - [x] Test valida valores en céntimos ✅

**Resultado:** 253/253 tests pasando. Patrón consistente: cada transición de fase congela su estado.

---

### TAREA 3.6: Consistencia de datos congelados ✅ COMPLETADO

- [x] **Household - Refactorizar helpers internos:** ✅
  - [x] `get_total_incomes()` usa `_registered_incomes` si está disponible ✅
  - [x] `get_percentages_by_method()` usa `_registered_incomes` si está disponible ✅
  - [x] `_validate_total_incomes_positive()` usa `_registered_incomes` si está disponible ✅
- [x] **Household - Getters para datos congelados:** ✅
  - [x] `get_registered_incomes()` con validación ✅
  - [x] `get_agreed_percentages()` con validación ✅
  - [x] `get_agreed_contributions()` con validación ✅
- [x] **WorkflowManager - Exponer getters:** ✅
  - [x] `get_registered_incomes()` disponible en PLANNING/MONTH ✅
  - [x] `get_agreed_percentages()` disponible en MONTH ✅
  - [x] `get_agreed_contributions()` disponible en MONTH ✅
- [x] **Tests:** ✅
  - [x] Test que PLANNING usa datos congelados (no mutables) ✅
  - [x] Test que modificar datos mutables no afecta a PLANNING ✅
  - [x] Test getters de datos congelados ✅
  - [x] Test validación de fase en getters ✅

**Resultado:** 260/260 tests pasando. Inmutabilidad garantizada a lo largo de todas las fases.

---

### TAREA 4: Cacheo de estado al pasar a MONTH (CRÍTICO) ✅ COMPLETADO

- [x] **Household:** Agregar atributos de caché: ✅
  - [x] `self._agreed_percentages = {}` (dict con % acordado por miembro) ✅
  - [x] `self._agreed_contributions = {}` (dict con contribuciones por categoría) ✅
- [x] **Household.freeze_planning_state():** ✅
  - [x] Calcular y guardar `self._agreed_percentages = self.get_percentages_by_method(self.method)` ✅
  - [x] Calcular y guardar `self._agreed_contributions = self.get_current_contributions()` ✅
  - [x] Validación implícita (finish_planning valida presupuestos antes de freeze) ✅
- [x] **WorkflowManager.finish_planning():** Llamar `household.freeze_planning_state()` antes de cambiar fase ✅
- [x] **Tests:** ✅
  - [x] Test que `_agreed_percentages` se guarda correctamente ✅
  - [x] Test que `_agreed_contributions` se guarda con estructura completa ✅
  - [x] Test valida percentages PROPORTIONAL (60/40) ✅
  - [x] Test valida contributions por categoría ✅

**Resultado:** 253/253 tests pasando. Estado congelado disponible para consultas en fase MONTH.

---

### TAREA 5: Agregaciones en Budget (jerarquía limpia)

- [ ] **Budget.get_total_budgeted():**
  - [ ] Suma `planned_amount` de todas las categorías activas
  - [ ] Retorna int (céntimos)
- [ ] **Budget.get_total_spent():**
  - [ ] Suma `spent` de todas las categorías activas
  - [ ] Retorna int (céntimos)
- [ ] **Budget.get_total_remaining():**
  - [ ] Calcula `total_budgeted - total_spent`
  - [ ] Retorna int (céntimos)
- [ ] **Budget.get_all_categories_status():**
  - [ ] Retorna dict: `{category: {planned, spent, remaining}, ...}`
  - [ ] Evita loops externos para obtener datos de todas las categorías
- [ ] **Refactor Household:** Usar estos métodos en lugar de loops manuales
- [ ] **Tests:** Validar cálculos con múltiples categorías

# ================================================ 📋 SIGUIENTE ================================================

### TAREA 6: Consultas de balance por miembro

- [ ] **Household.get_member_owed_total(member_name):**
  - [ ] Suma todas las contribuciones acordadas del miembro (requiere Tarea 4)
  - [ ] Retorna int (céntimos)
- [ ] **Household.get_member_paid_total(member_name):**
  - [ ] Delega a `expense_tracker.get_total_spent_by_member(member)`
  - [ ] Retorna int (céntimos)
- [ ] **Household.get_member_balance(member_name):**
  - [ ] Calcula `paid - owed`
  - [ ] Retorna int (negativo = debe dinero, positivo = pagó de más)
- [ ] **Household.get_member_status(member_name):**
  - [ ] Retorna dict: `{income, owed, paid, balance, contributions_by_category}`
  - [ ] Helper para obtener toda la info de un miembro de golpe
- [ ] **Tests:** Escenarios con diferentes balances (deudor, acreedor, equilibrado)

---

### TAREA 7: Loose money por miembro

- [ ] **Household.get_loose_money_by_member():**
  - [ ] Calcular loose_money total (`total_incomes - total_budgeted`)
  - [ ] Aplicar porcentajes acordados (requiere Tarea 4)
  - [ ] Retorna dict: `{member: loose_money_cents, ...}`
- [ ] **Tests:** Validar distribución según método (proporcional, equal, custom)

---

### TAREA 8: Summary builders (helpers para queries)

- [ ] **Household.get_category_status(category_name):**
  - [ ] Retorna dict: `{planned, spent, remaining, status}` de UNA categoría
  - [ ] Helper reutilizable
- [ ] **Household.get_budget_overview():**
  - [ ] Retorna dict: `{total_budgeted, total_spent, total_remaining}`
  - [ ] Usa métodos de Tarea 5
- [ ] **Refactor summaries:** Usar estos helpers en `get_planning_summary()` y `get_month_summary()`
- [ ] **Tests:** Validar que helpers funcionan correctamente

---

### TAREA 3: Integrar registro de gastos en fase MONTH

- [ ] Queries mensuales en Household/WorkflowManager:
  - [ ] `get_month_summary()` - Retorna: total (budgeted/spent/remaining), by_category (cada una con planned/spent/remaining), loose_money
  - [ ] Nota: Queries avanzadas de balance por miembro requieren Tarea 4 (cacheo de estado)
- [ ] Tests integración: flujo completo REGISTRATION → PLANNING → MONTH con gastos
- [ ] Actualizar sandboxes de ejemplo

---

### Rastear loose money y opción de ajustar presupuestos con porcentajes #TODO

# ================================================ 🧊 BACKLOG ================================================

### Refactorizar validaciones en módulo centralizado

- [ ] Crear módulo de validadores
- [ ] Refactorizar clases existentes para usar validadores centralizados
- [ ] Tests

---

### Refactorizar BudgetCategory para usar @property

- [ ] Implementar @property para atributos sensibles
- [ ] Tests
- [ ] Convertir `spent` a atributo privado `_spent` con `@property` de solo lectura
- [ ] Convertir `planned_amount` a atributo privado `_planned_amount` con `@property` de solo lectura
- [ ] Actualizar tests para verificar que escritura directa falla (`AttributeError`)
- [ ] Mantener mutación solo via métodos controlados (`register_payment()`)

---

### Paso 3: Método para Calcular Deudas (1h)

- [ ] Después de registrar gastos, necesitas saber quién debe qué:

```
Retorna balance (positivo=acreedor, negativo=deudor)
{
'Amanda': 5000,   # Pagó 50€ más = le deben
'Heri': -5000     # Debe 50€
}
```

---

### Implementar fase CLOSING

- [ ] Implementar `WorkflowManager.finish_month()`:
  - [ ] Validar fase MONTH
  - [ ] Generar reporte final del mes (total spent, by category, by member)
  - [ ] (Opcional v0.2) Archivar en memoria (`monthly_archives`)
  - [ ] Transitar a fase CLOSING
- [ ] Implementar `WorkflowManager.start_new_month()`:
  - [ ] Crear nuevo ExpenseTracker vacío
  - [ ] Reemplazar en Household o crear nuevo Household si presupuesto cambia
  - [ ] Reset a fase MONTH
- [ ] Tests: cerrar mes, iniciar nuevo, verificar tracker limpio

---

### Mejorar preview de contribuciones por categoría

- [ ] Implementar preview de contribuciones
- [ ] Tests

---

### CLI interactivo mejorado para flujo end-to-end

- [ ] Menú principal con opciones por fase
- [ ] Implementar comandos para cada fase
- [ ] Validar output legible

---

### Excepciones Específicas para cada raise

# ================================================ ✅ COMPLETADO ================================================

## 📅 06-03-26

**TAREA REFACTOR: Limpiar API de métodos de reparto** ✅
- Renombrados métodos preview vs current
- Reorganizada estructura de Household (11 secciones)
- Expuesto `set_custom_splits()` en WorkflowManager
- 252/252 tests pasando
- Sandbox actualizado

**TAREA 3.5: Cacheo de ingresos al pasar a PLANNING** ✅
- Implementado `_registered_incomes`
- Congelación en `freeze_registration_state()`
- 253/253 tests pasando

**TAREA 3.6: Consistencia de datos congelados** ✅  
- Helpers internos usan datos congelados transparentemente
- Getters públicos para acceso con validación de fase
- 260/260 tests pasando

**TAREA 4: Cacheo de estado al pasar a MONTH** ✅
- Implementado `_agreed_percentages` y `_agreed_contributions`
- Congelación en `freeze_planning_state()`
- 253/253 tests pasando

⏱️ 7h | 🧪 260 Tests | 📊 98% Cov | 🚩 FLUJO FASE PLANNING

---

## 📅 05-03-26

**Fase MONTH:** ✅
- Registro de gastos funcional
- Worklow REGISTRATION → PLANNING → MONTH completo
- ExpenseTracker integrado con BudgetCategory
- Tests: 252 pasando (98% coverage)

⏱️ 6h | 🧪 252 Tests | 📊 98% Cov | 🚩 FLUJO COMPLETO

---

## 📅 04-03-26

**TAREA 2.1:** ✅
- Método `assign_distribution_method()`
- Worklow REGISTRATION → PLANNING funcional
- Tests: 152 pasando (96% coverage)

**TAREA 2.2:** ✅
- Summary de contribuciones por categoría
- Preview de balance por miembro

⏱️ 5h | 🧪 152 Tests | 📊 96% Cov | 🚩 FLUJO FASE PLANNING

---

## 📅 26-02-26

**TAREA 1:** ✅
- Workflow Manager implementado con fases
- Registration phase completa
- 124 tests pasando

⏱️ 4h | 🧪 124 Tests | 📊 95% Cov | 🚩 WORKFLOW MANAGER

---

## 📅 20-02-26

- Budget: Presupuesto con categorías ✅
- BudgetCategory: spent tracking por miembro ✅
- Tests avanzados configuración ✅

⏱️ 3.5h | 🧪 80 Tests | 📊 93% Cov | 🚩 BUDGET + TRACKING

---

## 📅 19-02-26

- Expense: Registro de gastos ✅
- ExpenseTracker: Colección + queries ✅
- Tests integración ✅  

⏱️ 3h | 🧪 55 Tests | 📊 91% Cov | 🚩 EXPENSES

---

## 📅 18-02-26

- Household: Core logic ✅
- Member: Miembros con ingresos ✅
- Tests unitarios básicos ✅

⏱️ 4h | 🧪 30 Tests | 📊 88% Cov | 🚩 CORE MODEL

---

## 📅 <18-02-26

- Proyecto inicializado ✅
- pytest + coverage configurado ✅
- Currency: Manejo de céntimos ✅

⏱️ 2h | 🧪 15 Tests | 📊 85% Cov | 🚩 SETUP
