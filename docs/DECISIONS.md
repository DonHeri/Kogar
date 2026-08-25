# ================================================ ⏳ EN NEVERA (Ideas/Dudas que no urgen) ================================================

- [SavingsAccount] Performance: cuando exista histórico multi-año,
  considerar monthly_snapshot — un resumen precalculado por mes
  que se congela en finish_month(). Balance = último snapshot +
  entries del mes actual. Evita recalcular toda la historia.
  Implementar cuando el histórico sea un problema real, no antes.
  [SavingsBuckets] Caso de uso principal: gastos recurrentes no mensuales
  (seguro anual, ITV, vacaciones). Usuario aparta X€/mes en un bucket
  con nombre y meta opcional. Cuando llega el gasto, retira del bucket
  y registra como Expense.
- **[General]** Tracker de IVA: registrar IVA por gasto, saber total al final del mes
- **[ExpensesTracker]** Filtrar por: día, rango días, rango precios, nombre
- **[CategoryLibrary]** Verificador similitudes: detectar si usuario quiso decir categoría existente
- **[BudgetCategory]** Gastos usan `MetodoReparto`, ahorros usan `individual_goals` por miembro
- **[Expense]** `Expense` = solo gastos externos. Transferencias internas NO son Expense, se calculan con `get_settlement()`. Futuro: `InternalTransfer` si necesario. Usa strings para member/category.

- **[Workflow] Ingresos incompletos/asíncronos:** Responsabilidad del usuario decidir estrategia en REGISTRATION. Software NO gestiona automáticamente. Helper `preview_liquidity_impact()` muestra warnings antes de `finish_planning()` si detecta member con liquidez ajustada (>50% comprometido). CLI advierte pero no bloquea. Patterns documentados: EQUAL + adelantos informales, usar montos absolutos para fijos cuando ingresos faltan, usar pagas extras para rebalancear después. Feature futura (v0.3+): "recalcular presupuestos con nuevos ingresos" para flexibilidad avanzada. Por ahora, arquitectura soporta el 90% de casos: user elige herramienta correcta (% o absolutos) según su situación. ✅ DISEÑO

---

### **MEJORAS SOLID (Futuras)**

- **[Household]** Si >250-300 líneas → extraer `BudgetDistributionService`
- **[MetodoReparto]** Si 5+ métodos → Strategy Pattern con `DistributionStrategy(Protocol)`
- **[BudgetCategory]** Si >150 líneas → dividir en `BudgetCategory` + `CategoryExpenseTracker`
- **[Repositories]** Cuando SQLite → `ExpenseRepository(Protocol)`

---

# ================================================ 🏗️ DEFINIENDO ================================================

- **[Expense]** ¿ID único (UUID) o objeto en memoria suficiente?
- **[Budget] Pagas extras:** `register_extra_income(member, amount, strategy)` en fase MONTH. Estrategias: `proportional` (distribución según método actual), `equal` (split igual entre categorías), `transfer` (todo a categoría específica), `custom` (usuario define splits). Modifica presupuestos directamente (aumenta planned_amount de categorías), NO recalcula contribuciones acordadas. La paga extra es "bonus" del receptor, puede decidir destino. Acuerdo inicial (\_agreed_contributions) permanece inmutable. Tracking separado innecesario: `get_category_budget()` ya refleja total efectivo. ✅ DISEÑO

# ================================================ 🏁 CERRADAS (Funcionamiento actual) ================================================
### **====== 16-04-26 ======**
[Household] `set_budget_by_percentages` Ahora recibe dict de porcentajes por categorías. 
  [Motivo]: Generaba descuadres al settear cada categoría de forma independiente

[Household] Category["reserva"] Ahora se autocalcula desde `set_budget_for_category` [L90-108]
  [Motivo] evitar que usuario pueda planificar reserva, y evitar dinero flotante
[Household] `Categorías estándar` se crean al congelar registro: De ese modo me aseguro de que reserva existe


### **====== 27-03-26 ======**

**- [Expense] `is_shared` llegará a workflow con un valor que se le preguntará al usuario -> Este gasto es compartido o no?**

- **[Budget] Presupuestos por porcentaje:** Sistema híbrido. WorkflowManager ofrece `set_budget_by_percentage(category, pct)` y `set_budget_for_category(category, amount)`. Usuario elige según caso de uso: porcentajes para gastos variables que escalan con ingresos, montos absolutos para gastos fijos (alquiler, préstamos). Conversión: WM multiplica pct×100 (basis points), Household calcula `(total_incomes * pct_basis) // 10000`. Mismo patrón que `to_percentage_basis()`. Helpers: `get_budget_as_percentage(category)` retorna % que representa, `get_remaining_budget_percentage()` retorna % no presupuestado.
- **[Arquitectura]** Normalización: WM hace `.strip()` pero NO lowercase. Nombres propios mantienen capitalización. CategoryLibrary ya normaliza categorías.
- **[CLI_EXPERIENCIA]** En la creación de categorías de presupuesto. El usuario no recibirá una pregunta de que categorías quiere crear. Recibirá información de lo que la app busca registrar, y el usuario decide como llamarlo:
  _Ej._ App: Los gastos fijos son ... Te recomendamos llamarlo "Gastos fijos", deseas cambiarle el nombre?... Tienes deudas? Las deudas son gastos de financiaciones, letras etc...
  De esta forma, podemos conseguir que el usuario personalice a su antojo, pero el programa por dentro funciona como toca, sin dejar todo completamente flexible.

### **====== 24-03-26 ======**

- **[Household] `get_loose_money()` puede retornar negativo:** El backend no bloquea
  presupuestos que superen los ingresos. `loose_money < 0` indica over-budget; el frontend
  es responsable de advertir al usuario. Antes lanzaba ValueError — eliminado.
- **[Household] `validate_debt_and_saving_dont_exceed_capacity` usa solo `reserva`:**
  La capacidad de cada miembro para deuda+ahorro es exclusivamente su parte de la categoría
  `reserva`. `loose_money` no computa como capacidad (con el modelo actual, reserva absorbe
  el sobrante y loose_money siempre es 0). Eliminar `loose_money` de la fórmula evita fallos
  cuando hay over-budget y clarifica el modelo mental.

### **====== 20-03-26 ======**

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

### **====== 13-03-26 ======**

[FinanceCalculator] Sobrante de céntimos por categoría va al miembro con mayor resto
de truncamiento ((budget \* pct) % 10000), no siempre al de mayor porcentaje.
Evita acumulación de céntimos en el mismo miembro con múltiples categorías.
[FinanceCalculator] Rounding policy: el descuadre de céntimos por
aritmética entera se tolera en categorías (máx 1¢ por categoría),
nunca en el total por miembro. Prioridad: integridad del ingreso >
exactitud por categoría.
[FinanceCalculator] EQUAL: el céntimo sobrante por categoría va siempre
al primer miembro del dict. Con presupuestos normales el impacto es
≤1¢ por categoría. Aceptado por simplicidad.

### **====== 10-03-26 ======**

- **[Arquitectura] Normalización de nombres:** Sistema unificado siguiendo patrón de currency.py. **Storage**: nombres siempre en minúsculas (lowercase) internamente para consistencia. **Display**: usar `format_name()` (Title Case) cuando sea necesario en UI. **Normalización**: ocurre en puntos de entrada (Member.**init**, Expense.**init**, todos los lookups en Household/ExpenseTracker/WorkflowManager). Implementado en `src/utils/text.py` con `normalize_name()` (valida, strip, lowercase) y `format_name()` (Title Case). Beneficios: elimina bugs de "Amanda" != "amanda", consistencia con CategoryLibrary que ya normalizaba, zero acoplamiento (normalización independiente de lógica de negocio). ✅ IMPLEMENTADO

### **====== 06-03-26 ======**

- **[Arquitectura] Single Source of Truth para gastos:** ExpenseTracker es la única fuente de verdad para execution (gastado). Budget solo maneja planning (presupuestado). Household coordina entre ambos con métodos `get_category_spent()`, `get_total_spent()`, `get_category_remaining()`, `get_total_remaining()`. Eliminada duplicación de estado: `BudgetCategory.spent` borrado, `Budget.register_payment()` borrado. Principios aplicados: Separation of Concerns (Budget planifica, Tracker ejecuta, Household coordina) + YAGNI (evitamos BudgetExecution service class innecesario). Zero acoplamiento entre Budget y ExpenseTracker. ✅ IMPLEMENTADO

- **[Household] Congelar estado en transiciones:** `finish_registration()` cachea `_registered_incomes`. `finish_planning()` cachea `_agreed_percentages` y `_agreed_contributions`. Así fases posteriores usan siempre los datos oficiales acordados, no recalculan dinámicamente. Helpers como `get_total_incomes()` comprueban si hay frozen data y la usan; si no, calculan. ✅ IMPLEMENTADO

- **[WorkflowManager] Doble validación:** `validate_phase()` estricta (solo current_phase), `validate_phase_accessible()` permisiva (current_phase OR fase ya completada). Modificaciones usan estricta, consultas/summaries usan permisiva. Así puedes consultar planning_summary en MONTH. ✅ IMPLEMENTADO

- **[WorkflowManager] `_completed_phases = set()`:** Registra fases alcanzadas. Se inicializa con `{Phase.REGISTRATION}`. Cada `finish_X()` añade la siguiente fase ANTES de cambiar current_phase (ej: finish_planning añade Phase.MONTH). validate_phase_accessible comprueba membership en este set. ✅ IMPLEMENTADO

- **[Household] `preview_budget_contribution_summary(method)` vs `get_current_contributions()`:** Preview simula "qué pasaría si" sin modificar nada. get_current usa self.method ya configurado. Separamos para claridad API. ✅ IMPLEMENTADO

- **[Código] Organización por secciones:** Household y WorkflowManager tienen comentarios claros tipo `# ====== REGISTRATION PHASE ======`. Facilita navegación en archivos de 200+ líneas. ✅ IMPLEMENTADO

### **====== 05-03-26 ======**

- **[WorkflowManager]** Única capa de conversión euros↔céntimos. Dominio 100% en céntimos (int). Usuario → WM convierte → Dominio → WM convierte → Usuario. Bug corregido: antes se convertía 2 veces (gastos x100). ✅

- **[WorkflowManager]** Recibe primitivos del CLI, crea objetos del dominio. CLI no importa Member/Expense. WM hace `.strip()` pero NO normaliza. ✅

### **====== 03-03-26 ======**

- **[Household]** ExpenseTracker se inyecta en constructor, no se instancia. Permite mocks. ✅
- **[ExpenseTracker]** NO valida, solo almacena/filtra. Validaciones en Household. WM crea → Household valida → Tracker almacena. ✅
- **[ExpenseTracker]** Un tracker = un mes. Siguiente mes = nuevo tracker. Histórico multi-mes para v0.4. ✅
- **[ExpenseTracker vs Calculator]** Tracker usa `sum()` directo. Calculator para distribuciones complejas. ✅

### **====== 02-03-26 ======**

- **[Budget]** 4 categorías rígidas por ahora, futuro flexibles. ✅
- **[Household]** Gestiona percentages y contributions. ✅
- **[General]** 100% ingresos con destino. `get_planning_summary()` expone "loose_money". ✅
- **[CLI]** `finish_registration` y `finish_planning` validan antes de avanzar fase. ✅

#### **27-02-26**

- **[MetodoReparto]** Método único global v0.2. Todas categorías mismo reparto. v0.3: per-category. ✅
- **[Arquitectura]** `Protocol` mejor que ABC para repos. Duck typing, mypy. ✅

#### **20-02-26**

- **[Phases]** Fases NO en Household. WorkflowManager orquesta transiciones. Entidades dominio no conocen fases. ✅
- **[utils]** `change_eur_cent.py` → `currency.py` ✅
- **[Budget]** Si >150 líneas, `BudgetCategory` a archivo propio. ✅
- **[Member]** `participante.py` → `member.py` ✅

#### **19-02-26**

- **[Household]** `set_custom_splits` recibe floats, valida y convierte. CUSTOM se almacena, PROPORTIONAL/EQUAL se calculan dinámicamente. ✅
- **[Household]** `assign_distribution_method` settea método. `get_percentages_by_method` delega según método. ✅
- **[Calculator]** Diferencia en percentages se asigna a mayor ingreso. ✅

#### **18-02-26**

- **[Household]** `calculate_member_contribution_for_category` recibe percentages externos para evitar acoplamiento. ✅
- **[Calculator]** `calculate_contribution`: división entera (`//`), céntimo sobrante al de mayor porcentaje. ✅

#### **< 18-02-26**

- **[Budget]** Orquestador con dict de `BudgetCategory`. ✅
- **[Member]** Nombre obligatorio, no espacios. ✅
- **[BudgetCategory]** Presupuesto y pagos > 0. ✅
- **[Household]** Lógica de sumas delegada a `Calculator`. ✅
- **[Calculator]** Migrado a céntimos (enteros) para precisión. ✅
