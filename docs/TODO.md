# ================================================ Zona de trabajo ================================================



**Falta:**

- [X] Terminar testing [BucketTracker], [SavingBucket]

- Integrar [BucketTracker] en [SavingTracker]
  deposit_to_bucket(member_name, bucket_id, amount_cents) — valida y delega
  withdraw_from_bucket(member_name, bucket_id, amount_cents) — misma lógica inversa

  Para withdraw_from_bucket la validación es diferente. ¿Qué estás validando ahí — saldo en SavingAccount o saldo en el propio bucket?

- Exponer métodos en [Household], [WorkflowManager]

# ================================================ SIGUIENTES PASOS ================================================

# TODO: Si member retira más de su aportación en bucket SHARED,
# la diferencia genera deuda con el otro miembro → incluir en settlement

### 🟠 PRIORIDAD 3 — Cierre de mes

- [x] `finish_month()` → reporte final + reconciliación savings planned vs actual
- [ ] `start_new_month()` → nuevo ExpenseTracker, reset fase a MONTH
- [ ] Tests



### v0.4 - Persistencia e Histórico

- [ ] MonthlySnapshotRepository: guardar snapshots de meses cerrados en SQLite
- [ ] Protocol ExpenseRepository + InMemoryExpenseRepository + SQLiteExpenseRepository
- [ ] Queries histórico: ver meses anteriores, comparar gastos entre meses
- [ ] Exportar reportes (CSV, PDF)
- [ ] Ver: `docs/Integraciones_Futuras/GESTION_MENSUAL_EXPENSE_TRACKER.md`

## ============================================ FUTURO=============================================

### 5. Ingresos extras (3-4h)

- [ ] Diseño: ¿individual o compartido?
- [ ] Implementación
- [ ] Tests

### 4. Transacciones internas (3-4h)

- [ ] Clase `InternalTransfer`
- [ ] Clase `TransferTracker`
- [ ] Integrar con balances
- [ ] Tests

### Refactorizar validaciones en módulo centralizado

**Objetivo:** Centralizar validaciones repetidas en un módulo reutilizable.

- [ ] Crear módulo de validadores
- [ ] Refactorizar clases existentes para usar validadores centralizados
- [ ] Tests

---

### Refactorizar BudgetCategory para usar @property

**Objetivo:** Proteger atributos mutables usando @property (mismo patrón que Expense).

- [ ] Implementar @property para atributos sensibles
- [ ] Tests

**Qué implementar:**

- [ ] Convertir `spent` a atributo privado `_spent` con `@property` de solo lectura
- [ ] Convertir `planned_amount` a atributo privado `_planned_amount` con `@property` de solo lectura
- [ ] Actualizar tests para verificar que escritura directa falla (`AttributeError`)
- [ ] Mantener mutación solo via métodos controlados (`register_payment()`)

**Beneficios:**

- Inmutabilidad: Previene `category.spent = 999999` accidental
- API clara: Separación entre estado interno privado y lectura pública
- Consistencia: Mismo patrón que Expense

### Implementar buscador de similitudes en CategoryLibrary

**Objetivo:** Detectar typos y sugerir categorías similares.

- [ ] Implementar detección de similitud
- [ ] Integrar con add_category
- [ ] Tests

### 🧊 BACKLOG
- [ ] Método de reparto por categoría (v0.3) → `CategoryConfig(behavior, split_method)` **Objetivo:** Permitir asignar un método de reparto diferente a cada categoría.
- [ ] Subcategorías con entidad propia (v0.3) -> fijos → [alquiler, luz, agua, internet]
- [ ] Cuentas bancarias (v0.4)
- [ ] Persistencia SQLite (v0.4)
- [ ] Analytics (v0.5)

### v0.5 - Analytics e Inteligencia

- [ ] ExpenseAnalyzer: comparaciones multi-mes, tendencias, predicciones
- [ ] Alertas inteligentes basadas en histórico
- [ ] Gráficos y dashboards

# ================================================ ✅ COMPLETADO ================================================

### ====== 16-04-26 ======
## Tarea urgente: set_budget_by_percentages
el método antiguo provocaba descuadres
[Solución] a Household llegan los porcentajes para las tres categorías. De ese modo se comprueba que se aplican los porcentajes correctamente y todo cuadra. Se seguirá la misma forma que `calculate_contribution_from_incomes`
`sandbox_household` probandolo todo
[Household] creado método
Falta completar en [FinanceCalculator] -> Devuelve presupuestos
[Household] settea [presupuestos]

### ====== 02-04-26 ======

- Terminar Creación de Buckets
- Renombrar SavingDestination -> SavingScope
- Test [BucketEntry]
- Creé metodos `deposit` `withdraw` [BucketTracker]

### ====== 28-03-26 ======

#### Settlement

- [x] `get_settlement()` filtrando por CategoryBehavior.SHARED
      Para solucionar lo que se deben los usuarios entre si, primero tengo que decidir que datos se van a utilizar en el balance. Pues si cuento todos, estaría haciendo que si un miembro ahorra más, el otro deba pagarle y eso no tiene sentido.
      Aquí surgen dos puntos distintos, por una parte, tenemos que independizar el ahorro [[SavingTracker],[SavinAccount] -> [SavingBuckets]] futuro
      Por otra parte, tenemos que - [ ] `Household.get_settlement()` → [{from, to, amount}]
- [x] Tests settlement

## Ya hecho:

get_settlement() — lógica:

Solo opera sobre is_shared=True
Calcula should_pay por miembro usando el método de reparto acordado (EQUAL/PROPORTIONAL/CUSTOM)
balance = paid_shared - should_pay → positivo = acreedor, negativo = deudor
Algoritmo greedy con dos punteros: mayor deudor paga al mayor acreedor, actualiza balances restantes y avanza — sin los bugs de estado que tenía el ejemplo
Devuelve [] si no hay gastos compartidos
Bugs corregidos respecto al ejemplo:

Fórmula de balance invertida
Filtro de acreedores usaba b < 0 (igual que deudores)
Variable debtor sobreescrita en el loop
"to": creditors (lista) en lugar del string del acreedor
i y j nunca avanzaban → loop infinito
Faltaba return

### ====== 27-03-26 ======

- [x] `get_month_summary` → igual
- [x] Warning en `finish_planning()` si deuda + ahorro_goal > parte_reserva del miembro
- [x] Tests savings (Entry, Account, Tracker, integración Household, WorkflowManager)

#### Gestionar cambios en loose_money

- Cuando puse los atributos para guardar deuda y ahorro, omitimos del flujo el loose_money, ya que el total presupuestado será como mínimo, igual al total de dinero.
  Si usuario quiere crear nuevas categorías, lo hara sobre **"reserva"**.
  Pero luego decidí que el usuario puede presupuestar mas de lo que ingreso. Luego podría cuadrarlo todo mediante transferencias o pagas extras.
  Entonces, tendría que ajustar el comportamiento de loose_money, he integrar deuda y saving de una mejor forma
- [x] Cambiar nombre: `loose_money` -> `missing_money` : Refleja lo que és, dinero presupuestado que falta
- No se mostrará a menos que exista.

#### Settlement - Clasificar cada gasto como personal o compartido

- [x] `is_shared` flag en `Expense` (default por categoría: fijos=True, variables=True, reserva=False)
- [x] `CategoryBehavior` en `BudgetCategory` (SHARED/EXCLUDED)
  - Expense.**init**: firma corregida — description="" antes, is_shared=True después (opcional)
  - Household.get_category_behavior(category) — delega a budget.categories[category].behavior
  - WorkflowManager.register_expense(): is_shared=None → deriva de CategoryBehavior; valor explícito → override
  - fijos (SHARED) → is_shared=True automático
  - variables / reserva (PERSONAL) → is_shared=False automático
  - Usuario pasa is_shared=True en gasto de variables → se respeta

#### Saving - Ahorro personal y compartido

- [x] Crear [SavingEntry]
- [x] Crear [SavingTracker]
- [x] Crear [SavingAccount]
- [x] Tests

- [x] Integrar en [Household]
  - [x] _register_savings_deposit_
  - [x] _register_savings_withdrawal_
  - [x] _get_member_savings_summary_
  - [x] Tests

- [x] Integrar en [Workflow]
  - [x] set_member_debt
  - [x] register_savings_deposit
  - [x] register_savings_withdrawal
  - [x] get_member_savings_summary
  - [x] Tests
- [x] `set_savings_goal` en `WorkflowManager` y `Household` (PLANNING, opcional)
- [x] `get_planning_summary` → incluir deuda y ahorro por miembro

### ====== 20-03-26 ======

- [x] Actualizar `CategoryLibrary` → STANDARD_CATEGORIES: fijos, variables, reserva

#### Decisiones cerradas

- `reserva` es la tercera categoría estándar — contenedor personal de deuda y ahorro
- STANDARD_CATEGORIES: fijos, variables, reserva. `deuda` pasa a EXTENDED como sugerencia
- `deuda` y `ahorro` son personales — se gestionan dentro de la parte de `reserva` de cada miembro
- Método de reparto en `reserva` → responsabilidad del usuario en MVP, igual que fijos/variables
- Warning si deuda + ahorro_goal > parte_reserva, pero no bloquea
- `SavingsAccount` no nace en `Member` — se crea en `freeze_registration_state()`
- Cuenta conjunta no es entidad separada — es query agregada sobre SavingsAccounts
- `SavingsDestination`: PERSONAL y SHARED
- Retiros son por destino — no se mezclan fondos automáticamente
- `CategoryBehavior` en `BudgetCategory` → diseño v0.3 anotado
- Settlement filtrará por CategoryBehavior.SHARED — reserva será EXCLUDED

### ====== 19-03-26 ======

- [x] `SavingDestination` en `constants.py`
- [x] `SavingEntry`, `SavingAccount`, `SavingTracker`
- [x] `Household` → `register_savings_deposit`, `register_savings_withdrawal`, `get_member_savings_summary`

### ====== 11-03-26 ======

#### Sistema porcentajes

- [x] `WorkflowManager.set_budget_by_percentage(category, pct)`
- [x] `WorkflowManager.get_budget_as_percentage(category)`
- [x] `WorkflowManager.apply_percentage_distribution(dict)`
- [x] Tests

### ====== 10-03-26 ======

#### TAREA 6: Consultas de balance por miembro

**Objetivo:** Saber si cada miembro está cumpliendo su parte del acuerdo.

**Estado:** Funcionalidad implementada, solo falta completar tests.

**Implementación:**

- [x] **Household.get_member_owed_total(member_name)**
- [x] **Household.get_member_paid_total(member_name)**
- [x] **Household.get_member_balance(member_name)**
- [x] **Household.get_member_status(member_name)**

- [x] **Tests:** Escenarios con diferentes balances (deudor, acreedor, equilibrado)

**Beneficio:** Base para fase CLOSING (calcular quién debe a quién).

#### TAREA 7: Loose money por miembro

**Objetivo:** Saber cuánto dinero "no presupuestado" le corresponde a cada miembro.

**Implementación:**

- [x] **Household.get_loose_money_by_member(member_name):**
  - [x] Calcula loose_money total
  - [x] Aplica porcentaje acordado del miembro
  - [x] Retorna int (céntimos)
- [x] **Tests:** Validar distribución según método (proporcional, equal, custom)

**Beneficio:** Transparencia total sobre dinero disponible por miembro.

### ====== 5/6-03-26 ======

#### Limpiar API de métodos de reparto y organización de Household

**Objetivo:** Resolver problemas arquitecturales antes de implementar freeze_planning_state().

**Problemas actuales:**

1. **Método de reparto desconectado:**
   - Usuario configura método con `assign_distribution_method()`
   - Pero luego tiene que pasar método de nuevo a `get_budget_contribution_summary(method)`
   - Confusión entre "preview" (comparar opciones) vs "configurado" (ver plan elegido)

2. **`set_custom_splits()` no expuesto en WorkflowManager:**
   - Existe en Household pero no hay forma de llamarlo desde interfaz

3. **Duplicación de cálculos:**
   - `get_planning_summary()` calcula percentages + contributions
   - `freeze_planning_state()` hará los mismos cálculos
   - Necesitamos helper interno compartido

4. **Organización de Household confusa:**
   - Sección "QUERIES" demasiado amplia
   - Secciones con 1 solo método
   - `get_registration_summary()` está en "INCOME CALCULATIONS" pero es un query

**Implementación:**

- [x] **Household - Renombrar y clarificar:** ✅
  - [x] `get_budget_contribution_summary(method)` → `preview_budget_contribution_summary(method)` (solo preview, NO modifica state) ✅
  - [x] Crear `get_current_contributions()` → Usa `self.method` ya configurado (requiere método asignado) ✅
- [x] **WorkflowManager - Exponer configuración:** ✅
  - [x] Agregar `set_custom_splits(splits: dict[str, float])` (delega a Household) ✅
  - [x] Validar fase PLANNING ✅
  - [x] Renombrar `get_budget_contribution_summary(method)` → `preview_budget_contribution_summary(method)` ✅
  - [x] Agregar `get_current_contributions()` (usa método ya configurado) ✅

- [x] **Household - Reorganizar secciones:** ✅

  ```
  Nueva estructura implementada con 11 secciones claramente definidas
  ```

- [x] **Tests - Actualizar:** ✅
  - [x] Buscar todos los usos de `get_budget_contribution_summary()` en tests ✅
  - [x] Reemplazar por `preview_budget_contribution_summary()` donde sea preview ✅
  - [x] 5 tests renombrados en test_household.py ✅

- [x] **Sandbox - Actualizar:** ✅
  - [x] Agregar ejemplo de `set_custom_splits()` en sandbox_workflow.py ✅
  - [x] Usar nuevos nombres de métodos ✅
  - [x] Demostrar patrón preview vs current ✅

**Beneficio:** Código más claro, sin duplicación, API intuitiva antes de implementar Tarea 4.

**Estado: ✅ COMPLETADO** - Todos los tests (252/252) pasando, sandbox actualizado y funcionando.

---

#### Cacheo de ingresos al pasar a PLANNING ✅ COMPLETADO

**Objetivo:** Congelar ingresos registrados para garantizar inmutabilidad de datos base de planificación.

**Problema resuelto:**

- ✅ Ingresos se congelan al finalizar REGISTRATION
- ✅ Percentages siempre coherentes con ingresos aceptados
- ✅ Base inmutable para cálculos posteriores
- ✅ Auditoría: trazabilidad de ingresos registrados

**Implementación:**

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

#### Consistencia de datos congelados ✅ COMPLETADO

**Objetivo:** Garantizar que cada fase trabaje exclusivamente con sus datos congelados, evitando bugs por recálculos o mutaciones inesperadas.

**Problema resuelto:**

- ✅ REGISTRATION trabaja con datos mutables (`members[].monthly_income`)
- ✅ PLANNING trabaja con `_registered_incomes` (congelado)
- ✅ MONTH trabaja con `_agreed_percentages` y `_agreed_contributions` (congelado)
- ✅ Métodos internos transparentemente usan datos correctos según disponibilidad
- ✅ Getters explícitos para acceder a datos congelados con validación de fase

**Implementación:**

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

#### Cacheo de estado al pasar a MONTH (CRÍTICO) ✅ COMPLETADO

**Objetivo:** Guardar el acuerdo de planificación para poder comparar "acordado vs pagado" en fase MONTH.

**Problema resuelto:**

- ✅ Los porcentajes y contribuciones acordadas se congelan al pasar a MONTH
- ✅ Estado inmutable para comparar "acordado vs pagado"
- ✅ Base para implementar `get_member_balance()` correctamente

**Implementación:**

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

#### Agregaciones en Budget (jerarquía limpia) ✅ COMPLETADO (modificado por refactor)

**Problema resuelto:**

- ✅ Budget expone `get_total_budgeted()` para planning
- ✅ ExpenseTracker es single source of truth para spent (no en Budget)
- ✅ Household coordina entre ambos con métodos bridge

**Implementación:**

- [x] **Budget.get_total_budgeted():** ✅
  - [x] Suma `planned_amount` de todas las categorías activas ✅
  - [x] Retorna int (céntimos) ✅
- [x] **Household coordinación Budget ↔ ExpenseTracker:** ✅
  - [x] `get_category_spent(category)` → delega a tracker ✅
  - [x] `get_total_spent()` → delega a tracker ✅
  - [x] `get_category_remaining(category)` → budget - spent ✅
  - [x] `get_total_remaining()` → total_budgeted - total_spent ✅
- [x] **Tests:** 14 nuevos tests de coordinación, 261 pasando ✅

**Decisión arquitectónica:** Budget no gestiona spent (eliminado `get_total_spent()` de Budget). ExpenseTracker es single source of truth. Ver DECISIONS.md 06-03-26.

**Beneficio:** Zero duplicación de estado, responsabilidades claras, 91% coverage.

### ====== 4-03-26 ======

#### TAREA 3: Integrar registro de gastos en fase MONTH

- [x] Modificar `Household.__init__()` para inyectar `expense_tracker: ExpenseTracker`
- [x] Implementar `Household.register_expense(expense: Expense)`:
  - [x] Validar `expense.member in self.members`
  - [x] Validar `expense.category in self.budget.categories`
  - [x] Llamar `self.expense_tracker.add_expense(expense)`
  - [x] Llamar `self.budget.categories[category].register_payment(member, amount)`
- [x] Implementar `WorkflowManager.register_expense(member, category, amount, desc="")`:
  - [x] Validar fase MONTH
  - [x] Crear `expense = Expense(member, category, amount, desc)`
  - [x] Delegar `self.household.register_expense(expense)`

Me quedo creando el summary del mes + métodos creados necesarios para summary

### ====== 3-03-26 ======

#### TAREA 2: Crear ExpenseTracker (Gestor de gastos)

**Objetivo:** Gestor de colección de gastos del mes actual. Almacena, filtra y calcula. NO valida.

**Arquitectura definida:**

- ExpenseTracker se INYECTA en Household (no se instancia interno)
- Solo gestiona mes actual (un ciclo MONTH)
- NO valida member/category (eso es Household)
- NO usa FinanceCalculator (usa `sum()` directo)
- WorkflowManager crea Expense → Household valida → ExpenseTracker almacena

**Implementación:**

- [x] Crear clase ExpenseTracker con `__init__(self)`
- [x] Método `add_expense(expense: Expense)` - almacenar sin validar
- [x] Método `get_all()` - retorna copia de gastos
- [x] Filtros: `get_expenses_by_category(category)`, `get_expenses_by_member(member)`
- [x] Agregaciones: `get_total_spent()`, `get_total_by_category()`, `get_total_by_member()`
- [x] Desgloses: `get_category_breakdown()`, `get_member_breakdown()`

- [x] Tests exhaustivos (sin mocks de Household, tracker independiente)

### ====== 2-03-26 ======

#### TAREA 1: Diseñar y crear clase Expense (Gasto individual)

**Contexto:** Ya tienes BudgetCategory que sabe cuánto DEBERÍA gastarse. Ahora necesitas representar un gasto REAL que alguien pagó.

**Qué definir:**

- [x] Estructura de datos: qué información debe guardar un gasto - ¿Quién lo pagó? (validar que existe en household) - ¿Cuánto? (validar positivo, manejar euros→céntimos) - ¿A qué categoría pertenece? (validar que existe) - ¿Cuándo? (fecha, opcional o requerida?) - ¿Descripción/concepto? (opcional para trazabilidad)
- [x] Validaciones necesarias en `__init__` - Monto debe ser > 0 - Miembro debe existir (¿o solo guardar nombre sin validar?) - Categoría debe existir (¿o se valida al registrar?)
- [x] Métodos getter simples si los necesitas
- [x] `__repr__` para debugging
- [x] Tests básicos: construcción válida, validaciones, casos borde

**Decisiones clave a tomar:**

- [x] ¿Expense valida miembro/categoría por sí mismo o delega esa responsabilidad a quien lo registra? [Household valida]
- [x] ¿La fecha es obligatoria o por defecto usa datetime.now()? - Usa datetime.now()
- [ ] ¿Necesitas un ID único para cada gasto o el objeto en sí es suficiente? → Ver docs/DECISIONS.md "EN DEFINICIÓN"

---

- [x] TESTS [budget] - Lineas [23-28, 40-42, 58-59, 73, 77-80]
- [x] TESTS [category_library] - Lineas [26-27, 38, 43, 48, 53-55, 66, 84]
- [x] TESTS [constants] - Lineas [11, 15, 26, 30]
- [x] TESTS [household] - Lineas [48, 52, 55, 76, 195]
- [x] TESTS [subcategory_library] - Lineas
- [x] TESTS [workflow_manager] - Lineas [30, 38, 42-43, 47, 51-52, 98]

**Total tests:** 152/152 pasando, 98%+ cobertura
⏱️ 4h | 🧪 217 Tests | 📊 97% Cov | 🚩 CREAR DEFINICIÓN DE GASTO

### ====== 27-02-26 ======

#### Completar fase PLANNING - Asignación de presupuestos y transición a MONTH

Implementación completa del flujo PLANNING con validaciones de estado

- [x] [Household] `set_budget_for_category(category: str, amount: float)` - Asigna presupuesto a categoría normalizada
- [x] [Household] `get_planning_summary()` - Retorna estado completo: miembros, ingresos, categorías, presupuestos, dinero suelto, y preview de contribuciones por categoría
- [x] [WorkflowManager] `finish_planning()` - Valida presupuestos asignados (≥1 categoría, monto > 0) y transita de PLANNING → MONTH
- [x] [WorkflowManager] `get_planning_summary()` - Query phase-aware que retorna el resumen de planificación
- [x] [Budget] Revertir validador en `get_category_budget()` - Cambiar `_validate_active_category()` → `_validate_category_exists()` (lógica invertida)
- [x] Tests: 22 nuevos tests (11 en test_household.py, 11 en test_workflow_manager.py)
  - Budget assignment: asignación, normalización, múltiples categorías, validaciones
  - Planning summary: estructura, dinero suelto, contribuciones, percentages, validaciones
  - Phase transition: transción correcta, validaciones de categorías y presupuestos, múltiples miembros
- [x] **Total tests:** 152/152 pasando, 98%+ cobertura
      ⏱️ 7h | 🧪 152 Tests | 📊 98% Cov | 🚩 CREAR FLUJO DE FASE DE PLANNING

### ====== 26-02-26 ======

#### [Household] - Crear método que cree presupuestos.

Para crear presupuesto, necesito que [Budget] tenga categorías predefinidas, y luego un método que me permita crear otras categorías.

- [x] Crear librerías de categorías estándar + extended
- [x] Crear librerías de subcategorías
- [X][Budget] setear categorías estándar `set_standard_categories`
- [X][Budget] `add_category` agregar categoría, también a librería
- [X][Budget] `remove_category `
- [X][Budget] `get_categories_list`
- [X][Budget] `get_category_library`
- [X][Budget] `_validate_category_exists`
- [X][Budget] `_validate_amount`
- [X][Budget] `_validate_category_is_deletable`

### ====== 20-02-26 ======

#### Desarrollar workflow de fases del proyecto

- [DECISION] - Decidir como crear el flujo de fases ⏱️3h

- [x] Crear clase WorkflowManager -> Esta es la abstracción que englobará todo el código. Es decir, será el comienzo de mi programa y el director de todo.
  - [x] TESTS
- [x] Primero, crear el helper que valide si el método se puede correr en la fase actual
  - [x] TESTS
- [x] registrar usuarios `register_member`
  - [x] TESTS
- [x] registrar ingresos `set_incomes`
  - [x] TESTS
- [x] `get_registered_members`
  - [x] TESTS
- [x] `get_registered_members`
  - [x] TESTS
- [x] `get_member_income`
  - [x] TESTS
- [x] `get_total_incomes`
  - [x] TESTS
- [x] `validate_phase`
  - [x] TESTS

⏱️ 7h | 🧪 121 Tests | 📊 98% Cov | 🚩 CREAR FLUJO DE FASE DE REGISTRO

```bash
Name                               Stmts   Miss  Cover   Missing
----------------------------------------------------------------
src\models\__init__.py                 0      0   100%
src\models\budget.py                  14      1    93%   27
src\models\budget_category.py         22      0   100%
src\models\constants.py               10      0   100%
src\models\finance_calculator.py      42      1    98%   86
src\models\household.py               59      0   100%
src\models\member.py                  12      0   100%
src\utils\__init__.py                  0      0   100%
src\utils\currency.py                  8      0   100%
src\workflow\__init__.py               0      0   100%
src\workflow\workflow_manager.py      31      1    97%   31
----------------------------------------------------------------
TOTAL                                198      3    98%
```

### ====== 19-02-26 ======

#### Implementar Métodos de reparto

- [x] [Household] `get_percentages_by_method` Integrar; CASE _PROPORTIONAL_, _EQUAL_
  - [x] TESTS
  - [x] _CUSTOM_ -> Crear intefaz para que el usuario elija porcentaje para cada miembro
        Para el ultimo miembro se calcula solo.
- [x] `set_method` -> Settear método definitivo

- [x] [Calculator] `calculate_percentage_based_on_weight_of_income` - Calcula porcentajes proporcional al sueldo
  - [x] TESTS
- [x] `calculate_equal_percentage` - Calcula porcentajes proporcional al sueldo
  - [x] TESTS
- [x] - `sandbox_main` - Hacer un printer del summary

⏱️ 7h | 🧪 75 Tests | 📊 98% Cov | 🚩 Implementar contribución Equal y Custom

```bash
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
src\models\__init__.py             0      0   100%
src\models\budget.py              31      0   100%
src\models\calculator.py          43      1    98%   91
src\models\constants.py           10      0   100%
src\models\household.py           57      0   100%
src\models\participante.py        12      0   100%
src\utils\change_eur_cent.py       8      2    75%   8, 17
------------------------------------------------------------
TOTAL                            161      3    98%
```

---

### ====== 18-02-26 ====== Resurgir como el Fénix

#### Implementar cálculo de contribución proporcional de cada presupuesto

- [x] Método `calculate_contribution()` en Calculator recibe (percentages, total_expense)
  - [x] Test
- [x] Integrar con `obtain_contribution_member()` en Household
  - [x] Test
- [x] Método que calcule la contribución para cada una de las categorías[z]()
  - [x] Test

⏱️ 3h | 🧪 52 Tests | 📊 98% Cov | 🚩 Implementar contribución proporcional

```python
Name                         Stmts   Miss  Cover   Missing
----------------------------------------------------------
src\models\__init__.py           0      0   100%
src\models\budget.py            31      0   100%
src\models\calculator.py        26      1    96%   55
src\models\constants.py         10      0   100%
src\models\household.py         38      0   100%
src\models\participante.py      12      0   100%
src\models\utils.py              4      1    75%   7
----------------------------------------------------------
TOTAL                          121      2    98%
```

### ====== 17-02-26 ======

- [x] Crear método calculate_contribution en calculator
- [x] Migrar código a cálculos en centésimas (enteros)

#### Implementar definición de presupuestos totales `Budget`

- [x] integrate into householder.

### ====== 16-02-26 ======

Crisis existencial con el código

### ====== 14-02-26 -> 15-02-26 ======

Finde libre

### ====== 13/02/2026 ======

#### Implementar definición de presupuestos totales `Budget`

- [x] FEAT: Crear clase; self.categories{"fiujos":BudgetCategory("fijos",0),"variables": BudgetCategory("variables", 0)}...
  - [x] TEST: instancia `Budget`
- [x] FEAT: Crear método `set_budget`
  - [x] TEST: instancia `Budget`
- [x] Sandbox: `household` usar budget

```bash
commit 24380c170b8b6d3255368ec2844e709588cef844 (HEAD -> feature/budget-tracking-system)
Author: Heriberto Rojas <herivallejo18@gmail.com>
Date:   Fri Feb 13 11:13:18 2026 +0100
```

    feat: Create class budget, set_budget. Test 37/37 passed, cov=100%

⏱️ 4h | 🧪 37 Tests | 📊 100% Cov | 🚩 Capa 1: Budget
📈 Total: ~ 19H (9H Diseño + 10 Estudio)

### ====== 12/02/2026 ======

#### Implementar definición de presupuestos por categorías

- [x] FEAT: Crear una clase `BudgetCategory` (nombre:str,monto:float,gastado:dict[Participante:float(gastado)])
- [x] Tests: instancia `test_create_valid_budget_category():`
  - [x] TEST: `test_negative_budget_must_raise_error():`
- [x] FEAT: `register_payment` Método para registrar un pago de un miembro
- [x] Tests: `test_register_payment_adds_amount_to_member(budget):`
  - [x] Tests: `test_register_payment_accumulates_multiple_payments(budget):`
  - [x] Tests: `test_register_payment_tracks_multiple_members(budget):`
  - [x] Tests: `test_register_payment_zero_raises_error(budget):`
  - [x] Tests: `test_register_payment_negative_raises_error(budget):`
  - [x] Tests: `test_create_budget_negative_planned_raises_error():`
  - [x] Tests:`test_create_budget_zero_planned_raises_error():`

- [x] FEAT: `def remaining()` - Calcular dinero restante _total - spent_
  - [x] Tests: `test_remaining_returns_difference_between_planned_and_spent(budget):`
  - [x] Tests: `test_remaining_returns_zero_when_fully_paid(budget):`
  - [x] Tests: `test_remaining_returns_negative_when_overpaid(budget):`
- [x] FEAT: `member_pending` Consultar pendiente por pagar de un miembro
  - [x] Tests: `test_member_pending_returns_amount_owed_minus_paid(budget):`
  - [x] Tests: `test_member_pending_when_member_hasnt_paid(budget):`
  - [x] Tests: `test_member_pending_when_overpaid(budget):`
- [x] SETUP: `sandbox_budget.py` actualizar remaining, member_pending + Validaciones
- [x] COMMIT (): feat(budget): implement BudgetCategory with payment tracking - Add BudgetCategory class (planned, payments, remaining, member_pending) - Validate amounts > 0 in constructor and register_payment() - Add 13 tests covering happy paths and edge cases - Update sandbox with demos and validations

⏱️ 4h | 🧪 15 Tests | 📊 98% Cov | 🚩 Capa 1: BudgetCategory
📈 Total: ~ 15H (7H Diseño + Estudio)

### ====== 11/02/2026 ======

#### Creación clases iniciales + testing completo

- [x] Modelo Participante + tests

  ```python
  class Participante:
  """Representa a una persona con su ingreso base mensual."""

  def __init__(self, name: str):

      if not name or not name.strip():
          raise ValueError("Nombre no puede estar vacío")

      # ====== Atributos ======
      self.name: str = name
      self.monthly_income: float = 0.0

  # Suma ingresos
  def add_incomes(self, income: float) -> None:
      if income < 0:
          raise ValueError("Ingreso no puede ser negativo")
      self.monthly_income += income

  def __repr__(self):
      return f"Participante('{self.name}', {self.monthly_income}€)"
  ```

- [x] Calculator (sum_total_incomes, calculate_member_percentage) + tests

  ```python
  from src.models.participante import Participante
  from typing import Dict


  class Calculator:

      @staticmethod
      def sum_total_incomes(members: dict[str, Participante]) -> float:
          """Calcula el total de ingresos entre los miembros"""
          return sum(m.monthly_income for m in members.values())

      @staticmethod
      def calculate_member_percentage(dict_members: Dict[str, Participante]) -> dict:
          """
          Parámetros:
          members: Miembros registrados
          """
          total = Calculator.sum_total_incomes(dict_members)

          if total <= 0:
              raise ValueError("Total de ingresos debe ser > 0")

          # almacenar porcentajes de cada usuario
          percentages = {}

          for name, member in dict_members.items():
              percentages[name] = (member.monthly_income / total) * 100

          return percentages
  ```

- [x] Household (registro miembros, ingresos, totales, porcentajes) + tests

  ```python
  class Household:

  def __init__(self) -> None:  # phase=Fase.REGISTRO

      self.members: Dict[str, Participante] = {}

  def register_member(self, member: Participante):
      """Crear instancias de miembros de la unidad e incorporar en dict de miembros"""
      self.members[member.name] = member

  def set_members_incomes(self, name: str, amount: float):
      """Interfaz para que usuario introduzca ingreso del mes."""
      if name not in self.members:
          raise ValueError(f"{name} no existe en el hogar")

      self.members[name].add_incomes(amount)

  def get_total_incomes(self):
      """
      Calcula el total de ingresos entre los miembros
      """
      if not self.members:
          raise ValueError("No hay miembros registrados")

      total = Calculator.sum_total_incomes(self.members)

      if total <= 0:
          raise ValueError("Al menos un miembro debe tener ingresos > 0")

      return total

  def get_percentages(self) -> dict:
      """Calcula el porcentaje que representa el sueldo de cada usuario frente al total de ingresos"""
      if not self.members:
          raise ValueError("No hay miembros registrados")

      percentages = Calculator.calculate_member_percentage(self.members)

      return percentages
  ```

- [x] Testing completo de módulos base (Participante, Calculator, Household)
  ```python
  Name                         Stmts   Miss  Cover   Missing
  ----------------------------------------------------------
  src\models\__init__.py           0      0   100%
  src\models\calculadora.py       16      0   100%
  src\models\constants.py         10      0   100%
  src\models\household.py         25      0   100%
  src\models\participante.py      12      1    92%   20
  ----------------------------------------------------------
  TOTAL                           63      1    98%
  ```
