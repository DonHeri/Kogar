# Decisiones de diseño — Kogar

**Propósito:** responder "¿por qué el código hace esto?" sin tener que leer el código.
**Cuándo escribir aquí:** cuando eliges entre dos opciones válidas. Si hay una sola opción obvia, no es una decisión.
**Cuándo actualizar:** cuando una decisión cambia. El motivo del cambio va en la misma entrada.
**Si hay conflicto con el código:** el código manda.

> Este documento reemplaza al `DECISIONS.md` cronológico original y a `Para_publicar/DECISIONS_2.md`.
> Agrupa por tema. No es un log de fechas.

---

## Pendientes (abiertas)

### `Expense` con UUID o identidad por memoria

Hoy `Expense` no tiene `id`. La identidad es el objeto en memoria.
Opciones: UUID generado en `__init__`, o sin ID hasta que llegue persistencia.
**Decisión provisional:** `Expense` sigue sin `id` de dominio. `ExpenseRepository.save()` devuelve el int suelto igual que los demás repos. Editar/borrar gastos individuales queda diferido — cuando llegue, se revisará si hace falta llevar el id en el objeto o basta con que el llamador lo enhebra aparte.
**Estado:** diferido hasta necesitar editar/borrar gastos.

### Alcance de la tabla `categories`: ¿global o por hogar?

La migración diferida define `name VARCHAR UNIQUE` (una sola "fijos" para todo el sistema). Pero las custom son hoy **por instancia de `Budget`** (`CategoryLibrary._custom_categories`). Choque: dos hogares no podrían tener cada uno su custom "gimnasio".
**Opciones:** (a) todas globales; (b) todas por hogar; (c) híbrido.
**Solución óptima (c):** dos niveles. Estándar/extendidas globales (`household_id NULL`, `is_standard=true`) con índice único parcial sobre `name WHERE household_id IS NULL`. Custom con `household_id` poblado y `UNIQUE(household_id, name)`. Ojo Postgres: `NULL` se trata como distinto en UNIQUE, por eso el índice parcial para las globales en vez de un `UNIQUE(household_id, name)` a secas.
**Blocker:** condiciona el esquema entero. Decidir antes de escribir la migración de T2.

### Dos fuentes de verdad: librería hardcodeada vs BD

Hoy `STANDARD_CATEGORIES`/`EXTENDED_CATEGORIES` viven hardcodeadas en `category_library.py`. Con la tabla `categories`, el mismo dato estaría en dos sitios.
**Solución óptima:** la BD es la única fuente de verdad. La librería conserva solo la **lógica de factory/mapeo** (`name`/`type` → subclase) pero lee el catálogo desde un `CategoryRepository`, no desde dicts de clase. Los estándar se cargan como **seed en la migración** de T2.
**Estado:** resolver junto con el punto anterior y `CategoryRepository`.

### Identidad de `Category` al reconstruir desde BD

El objeto de dominio `Category` **no porta el `id` de BD** (sigue a `Member`, no a `Period`). La identidad persistente vive en la tabla y en el repositorio.
**Solución óptima:** `CategoryRepository.create(category)` devuelve el `id` como `int`; el llamador lo enhebra aparte (mismo patrón que `WorkflowManager.period_id`), sin backfill sobre el objeto. Al cargar (T6), el repo instancia la clase según la columna `type` (`'normal'` → `Category`, `'auto_calculated'` → `AutoCalculatedCategory`) y rellena `distribution` desde su columna.
**Por qué sin `id` en el objeto:** es el patrón vivo del código. `Member` no lo lleva; y aunque `Period` lo declara, **nadie lo consume** — la orquestación enhebra el int suelto de `create()` (`WorkflowManager.period_id`). La regla se sostiene **aunque** Fase D añada un `category_id` FK: el id lo devolvería el repo y lo sostendría el llamador, igual que `period_id`, sin cargarlo en el objeto.
**Cabo suelto (esquema Fase D):** los planes de Fase D mencionan `expenses.category_id (FK)`, pero T2 fijó `expenses.category` como `VARCHAR` (enlace por nombre). Reconciliar antes de la migración de Fase D — NO afecta a la decisión de no llevar `id` en el objeto.
**Nota modelo implementado:** `type` distingue normal vs auto-calculada. El "shared/personal" vive en la columna `is_shared` (BOOLEAN), NO en `distribution` (que no se implementó). La tabla `categories` llevaría `name`, `is_shared`, `type`, `is_standard`, `household_id` (el `id` PK es de la fila, no del objeto de dominio).
**Estado:** decidir al implementar persistencia de categorías (T2/T6).

### Ancla de capacidad de deuda+ahorro tras "sobrante honesto"

`validate_debt_and_saving_dont_exceed_capacity()` y `auto_assign_saving_goals()` calculan la capacidad como "tu parte de la `reserva`". Cuando `reserva` → `sobrante` (forzado a 0), **desaparece el ancla**. Además `set_budget_by_percentages` mete hoy `reserva` dentro del 50/30/20.
**Solución óptima:** con `ahorro` y `deuda` como troncales explícitos, la capacidad pasa a derivarse del presupuesto de esos troncales (parte del miembro en ahorro+deuda), no de la reserva. El reparto por porcentajes aplica solo sobre categorías asignables; `sobrante` no es destino y su invariante es `== 0` al cerrar PLANNING.
**Estado:** parte de la tarea "Sobrante honesto" (ver "Visión futura de categorías").

---

## Modelo de gastos

### Método de reparto por gasto — DIFERIDO

Hoy el reparto de un gasto compartido usa el método global del hogar (`self.method`),
aplicado solo sobre los `expense.participants`. Es funcional pero inflexible.

**Diseño futuro:** aislar los métodos de reparto en una clase independiente e inyectable.
`Expense` podrá llevar su propio método; si no se especifica, hereda el de su `Category`;
si la categoría tampoco lo tiene, cae al método del hogar. Mismo patrón que `Category.is_shared`.

**Por qué diferido:** requiere añadir un campo a `Expense` y diseñar la jerarquía de
fallback. No bloquea nada hoy — el cambio será aditivo cuando llegue.

**Estado:** pendiente para cuando se implemente reparto por categoría (roadmap Fase 2).

---

### `Expense.participants` en lugar de `is_shared: bool`

`Expense` ya no lleva un booleano `is_shared`. En su lugar lleva `participants: list[str]`.
`is_shared` es ahora una propiedad derivada: `len(participants) > 1`.

**Por qué:** el booleano no capturaba _quién_ participa — perdía información para el
settlement. Con la lista, el cálculo de deudas puede operar por expense, no por hogar.

**Contrato de `WorkflowManager.register_expense()`:**

- `participants=None` → auto-deriva de `category.is_shared`
  (True → todos los miembros del hogar; False → solo el pagador)
- `participants=[...]` → se usan tal cual (lista vacía es caso muerto, no derivar).

**Implementado:** `get_settlement()` acumula balances por gasto usando `expense.participants`.
Solo participan los miembros de cada gasto, no todos los del hogar.

---

## Dinero y precisión

### Céntimos internos, euros en los bordes

- El dominio trabaja con `int` (céntimos). Nada de `float` en cálculos.
- Conversión única en `WorkflowManager`: `to_cents(euros)` al entrar, `to_euros(cents)` al salir.
- **Motivo:** `float` tiene errores de representación binaria (`0.1 + 0.2 != 0.3`). Inaceptable en finanzas.
- **Helpers:** `src/utils/currency.py` — `to_cents`, `to_euros`, `to_percentage_basis`, `format_percentage`.

### Largest remainder para reparto de céntimos

- Cuando repartes un presupuesto entre miembros, la suma de los truncados puede quedar 1¢ corta. El céntimo sobrante va al miembro con mayor resto de truncamiento.
- **Garantía:** `sum(contributions.values()) == budget_amount` siempre. Las funciones de `FinanceCalculator` lanzan `ValueError` si la suma no cuadra.
- **Por qué "mayor resto" y no "mayor porcentaje":** evita que siempre le toque el céntimo al mismo miembro en múltiples categorías.
- **Dónde:** `FinanceCalculator` — todas las funciones de distribución usan este patrón.

### Porcentajes en basis points ×100

- `53.57%` se representa como `5357` (int).
- **Motivo:** misma razón que céntimos. Permite `sum(percentages) == 10000` exacto.

---

## Fases (workflow)

### Máquina de estados separada del dominio

- `Phase` enum: `REGISTRATION → PLANNING → MONTH → CLOSING`.
- `WorkflowManager` orquesta las transiciones. `Household` no sabe en qué fase está.
- **Motivo:** el dominio es reutilizable. Las fases son un concepto de la aplicación, no del negocio.

### Dos validadores de fase

- `validate_phase(X)` — estricto. Solo permite si `current_phase == X`. Para mutaciones.
- `validate_phase_accessible(X)` — permisivo. Permite si `X == current_phase` o `X in _completed_phases`. Para consultas.
- **Motivo:** puedes consultar `get_planning_summary()` en `MONTH`, pero no modificar presupuestos.

### Congelar estado en transiciones

- `freeze_registration_state()` cachea `_registered_incomes` y crea las cuentas de savings/debt y las categorías estándar.
- `freeze_planning_state()` cachea `_agreed_percentages` y `_agreed_contributions`.
- **Motivo:** el acuerdo del mes es inmutable. Cambiar un ingreso en `MONTH` no afecta al mes en curso.

---

## Arquitectura de capas

### `WorkflowManager` como única fachada pública

- Recibe primitivos del exterior (euros, nombres sin normalizar) y produce objetos de dominio.
- Es la única capa que convierte euros ↔ céntimos.
- **Motivo:** desacopla el dominio de la interfaz. Si mañana hay una API REST, el dominio no cambia.

### `Household` como núcleo de dominio

- Dependencias por inyección en el constructor: `Budget`, `ExpenseTracker`, `SavingTracker`, `DebtTracker`.
- **Motivo:** testeabilidad (mocks), extensibilidad, bajo acoplamiento.

### Trackers no validan negocio, solo almacenan y filtran

- Patrón: WM crea → Household valida → Tracker almacena.
- `ExpenseTracker.add_expense()` no valida que el miembro existe. Eso es Household.
- **Motivo:** cada capa tiene un nivel de responsabilidad. Los trackers son colecciones con queries.

### Single Source of Truth para ejecución

- `ExpenseTracker` es la única fuente de "gastado". `Budget` no lo sabe.
- `Budget` es la única fuente de "presupuestado". `ExpenseTracker` no lo sabe.
- `Household` coordina con métodos como `get_category_remaining()` = budget − tracker.
- **Motivo:** estado duplicado es fuente de bugs. Se eliminó `BudgetCategory.spent` por esto.

### Los objetos de dominio no portan el `id` de BD

- La identidad persistente vive en la tabla y en el repositorio, no en el objeto de dominio. `repo.create()` devuelve el `id` como `int`; el llamador lo enhebra aparte (p. ej. `WorkflowManager.period_id`).
- `Member` cumple la regla (no lleva `id`). `Category` la sigue.
- **`Period` la viola:** declara `id: int | None` en el dataclass, pero **nadie lo consume** — la orquestación usa el int suelto de `create()`. Campo muerto → deuda anotada, no patrón a imitar.
- **Motivo:** Data Mapper — el dominio es ignorante de cómo se persiste. Meter el `id` de BD en el objeto acopla dos preocupaciones que esta arquitectura separa.

---

## Categorías

### Tres categorías estándar, autogeneradas al congelar registro

- `fijos`, `variables`, `reserva` se crean en `freeze_registration_state()`.
- **Motivo:** garantiza que `reserva` existe al entrar en `PLANNING`, sin validaciones extra.

### [refactor/category-objects · IMPLEMENTADO] Category como objeto con `is_shared`

- `Category` es una **clase concreta** que lleva `name` + `is_shared: bool`. Única subclase:
  `AutoCalculatedCategory`. El `id` de BD **no** vive en el objeto (ver "Identidad de `Category`...").
- `is_shared` es un **bool guardado, NO derivado**. Dos ejes ortogonales: `is_shared` = ¿el gasto
  entra al settlement?; el **método de reparto** = cómo se divide el dinero compartido, y sigue
  siendo **global** en `Household.method`.
- **Decisión cambiada respecto al plan inicial:** el diseño previo (documentado antes en esta
  entrada) derivaba `is_shared` de un campo `distribution` (`personal == MetodoReparto.INDIVIDUAL`).
  Se descartó a mitad del refactor por dos razones: (1) `INDIVIDUAL` **no existe** en el CHECK de
  `household_periods.method` (`proportional/equal/custom`) → habría roto la persistencia; (2) un
  bool basta para lo único que hoy se necesita (entra / no entra al settlement). El reparto por
  categoría se difiere (ver "Reparto por categoría — DIFERIDO").
- **Por qué NO 3 subclases (Shared/Personal/AutoCalculated):** Shared y Personal diferirían solo en
  el valor de `is_shared` → es un campo, no un tipo.
- **Por qué NO `ABC`:** una vez `calculate_own_budget()` sale de la base (Liskov), no queda método
  abstracto. Un `ABC` sin método abstracto es ceremonia.
- `CategoryBehavior` enum **eliminado** — sustituido por el bool `is_shared` del objeto.
- **Fábrica ≠ getter (nombres distintos a propósito):** `CategoryLibrary.create_category(name)`
  _fabrica_ el objeto (única frontera string→objeto); `Budget.get_category(name)` _obtiene_ la
  instancia viva del presupuesto. `Budget.get_auto_calculated_category()` localiza la reserva por
  `isinstance`, nunca por el string `"reserva"`.
- `calculate_own_budget()` vive **solo** en `AutoCalculatedCategory`.
- **`planned_amount` NO vive en `Category`:** es estado por período → se queda en `BudgetCategory`.
- **Motivo:** saca el comportamiento de los strings y lo mete en el objeto. Como `Category` ya es
  objeto, añadir `distribution` más adelante es **aditivo** (no toca strings ni la fábrica).

### `reserva` es autocalculada — implementada en `AutoCalculatedCategory`

- Asignar presupuesto a mano a una `AutoCalculatedCategory` lanza `ValueError` (el guard usa `isinstance`, no comparación de string).
- Su presupuesto se calcula como `total_incomes − suma_de_otros` en cada asignación, llamando a `auto_cat.calculate_own_budget(...)` — **no inline**. Si se calcula inline, el método abstracto es decoración y el refactor no cumple su objetivo.
- `Budget.get_auto_calculated_category()` es el punto único que localiza esa categoría. Household nunca busca categorías por nombre de string. **Invariante:** debe existir exactamente una `AutoCalculatedCategory` activa.
- **Antes:** seis usos de `"reserva"` (comparaciones y lookups) repartidos por Household. **Después:** todos pasan por `get_auto_calculated_category()` / `isinstance`.
- **Motivo:** el comportamiento especial de reserva está en el objeto, no en comparaciones de string.

### Reparto por categoría y por gasto — DIFERIDO (no implementado)

- **Estado actual:** el método de reparto es **único y global** (`Household.method`). Ni la
  categoría ni el gasto llevan método propio. `Category` solo lleva `is_shared` (bool).
- **Plan futuro (aditivo):** añadir `distribution: MetodoReparto` a `Category` (default = método del
  hogar) y, más adelante, un override por gasto. Reescribir el bucle del settlement para agrupar por
  categoría y usar `category.distribution`; el neteo greedy no se toca.
- **Por qué es seguro dejarlo para después:** `Category` ya es objeto, así que el campo es aditivo.
  Mientras todas las categorías usen el método del hogar, el resultado es idéntico al de hoy.
- **Cabo suelto al implementarlo:** la columna `method` en `household_periods` pasaría a ser solo el
  default del hogar; y `CUSTOM` por categoría/gasto necesitaría sus propios splits
  (`_custom_splits` es hoy único a nivel hogar).

### `missing_money` puede ser negativo

- El backend no bloquea presupuestos que superen los ingresos.
- `missing_money < 0` indica over-budget. La UI es responsable de advertir.
- **Motivo (24-03-26):** el backend no toma decisiones por el usuario. Si quiere presupuestar más de lo que ingresa, puede — cuadrará con pagas extras.

---

## Visión futura de categorías (Fase 2 — post T6)

Estas decisiones están tomadas en dirección pero no implementadas. Se revisarán cuando el árbol troncal/hoja se implemente.

### Sobrante honesto: separar el tapón estructural de la semántica de ahorro

- **Diagnóstico:** hoy `reserva` lleva tres sombreros a la vez — (1) el "20%" del 50/30/20, (2) el tapón que absorbe el remanente para que el presupuesto cuadre con los ingresos, (3) el techo de capacidad de deuda+ahorro. Conflación de tapón estructural con semántica.
- **Consecuencia del modelo actual:** el dinero sin presupuestar es invisible — `set_budget_for_category` fuerza `reserva = ingresos − otros`, así que `missing_money` sale siempre 0. El sistema llama "ahorro" a lo que el usuario no asignó, aunque nunca lo decidiera.
- **Dirección tomada (Opción 2):** el tapón pasa a ser una categoría honesta `sobrante`/`no_asignado` (la `AutoCalculatedCategory` pura). `ahorro` y `deuda` se separan en troncales que el usuario **sí** asigna. El descuadre se vuelve visible: _"tienes 600€ sin asignar, ¿a dónde?"_.
- **Regla de cierre:** `finish_planning()` valida `sobrante == 0` y lanza si no. **Motivo:** no es realista tener dinero suelto sin objetivo; el colchón legítimo es `ahorro`, del que luego se puede retirar.
- **Capa correcta:** el loop _"tienes X → ¿a dónde? → ¿cuánto?"_ es presentación (CLI/API/UI), no dominio. El núcleo solo expone tres primitivas, todas ya existentes: leer el sobrante, `set_budget_for_category` (sube/baja), `add_category`. Reasignar dinero NO necesita operación nueva: subes una categoría y el sink reabsorbe la diferencia.
- **Cabo suelto:** si el sobrante debe ser 0 al entrar en MONTH, solo existe durante PLANNING como guía → ¿es una categoría de verdad o es `missing_money` (ingresos − asignado) mostrado como guía? Si es lo segundo, `AutoCalculatedCategory` podría disolverse y "auto-calculada" dejar de ser un tipo de categoría. Decidir al implementar.
- **Modifica al implementarse:** las entradas "missing_money puede ser negativo" y "reserva absorbe el sobrante (loose_money=0)" de este documento.
- **Por qué diferido:** es cambio de producto (toca 50/30/20, `validate_debt_and_saving`, `auto_assign_saving_goals`), no el refactor puro de objetos Category. Se hace como tarea aparte encima de la base honesta que deja este refactor.

### MetodoReparto evoluciona de enum a clases de distribución — DIFERIDO (solo las clases)

- **Lo que YA entra en el refactor (no diferido):** el método de reparto pasa a vivir por categoría (y por gasto), reutilizando el **enum** `MetodoReparto` + nuevo valor `INDIVIDUAL`. El default de cada categoría se hereda de `self.method` del hogar. Ver "Reparto por categoría y por gasto".
- **Lo que se difiere:** convertir el enum en clases de estrategia (`ProportionalDistribution`, etc.). Hoy hay 4 métodos; el trigger del proyecto es 5+ (Rule of Three). Mientras tanto el enum elige qué función de `FinanceCalculator` llamar.
- **Consecuencia pendiente:** cuando el método por hogar deje de ser el único, la columna `method` en `household_periods` pasa a ser solo el default; se revisa si se elimina.
- **Por qué se difieren las clases:** sin variaciones que justifiquen abstracción, un enum + dispatch es más simple. Strategy sería sobre-ingeniería con 4 valores.

### Árbol troncal → categorías hija

- Ya documentado en este archivo ([26-05-26]).
- Las troncales (`fijos`, `variables`, `ahorro/deuda`) son fijas del sistema. El usuario crea categorías hija.
- El dinero fluye top-down: ingresos → troncales → hijas.
- Los gastos solo se registran en categorías hoja (ya documentado).
- **Prerequisito:** Category como objeto sólido (este refactor).

### Clases de distribución (si llega el trigger Rule of Three)

- **Obsoleto el plan de "doble herencia behavior × distribución":** ya no hay eje
  comportamiento como clases (`Shared`/`Personal` se colapsaron en el campo `distribution`).
  Solo quedaría un eje: el método de reparto.
- Si algún día hay 5+ métodos de reparto, el enum `MetodoReparto` se convertiría en clases
  de estrategia (`DistributionStrategy(Protocol)`). Mientras tanto, enum + dispatch.
- **Prerequisito:** superar el trigger Rule of Three (5+ métodos). Hoy 4.

### [26-05-26] Jerarquía padre/hijo; gastos solo en hojas

- Las categorías padre son agrupadores visuales y de agregación. No destino de gastos.
- Un `Expense` solo puede apuntar a una categoría hoja.
- **Motivo:** si se permiten gastos en categorías padre, la suma de subcategorías no cuadra con el total del padre. Con leaf-only, las queries de agregación son exactas.
- **Pendiente de implementar** (roadmap Fase 2).

---

## Gastos y reparto

### [26-05-26] `expense_participants` — el eje "quién participa" (Fase 2)

- **Dos ejes ortogonales, no confundir:**
  - _Cómo se reparte_ → método de reparto. Hoy es **global** (`Household.method`); por categoría/gasto está DIFERIDO (ver "Reparto por categoría — DIFERIDO"). El `is_shared: bool` actual NO se elimina vía participants.
  - _Quién participa_ → `expense_participants`. Subconjunto de miembros que comparten un gasto. **Fase 2.**
- `expense_participants(expense_id, member_id, weight)`: 1 participante = personal; todos = compartido total; subconjunto = compartido parcial; `weight = NULL` = partes iguales.
- **Motivo:** el caso "Ana y Luis comparten este gasto, no Marta" no lo cubre ni el bool ni `distribution` — es otra dimensión (el conjunto de participantes). Con participants sale gratis.
- **Modelo de dominio:** implementado — `Expense.participants: list[str]`, `is_shared` derivado, `get_settlement()` opera por gasto.
- **Persistencia:** migraciones `expenses` + `expense_participants` aplicadas. `ExpenseRepository` en curso (Bloque 3).

### Settlement calculado on-demand, no almacenado durante PLANNING ni MONTH

- `get_settlement()` calcula en vivo desde los gastos del mes.
- No se guarda durante el mes porque si cambia un gasto, el snapshot queda obsoleto.
- Solo se congela al cerrar el mes (`month_settlements`).
- **Motivo:** las proyecciones intermedias crean inconsistencias. Solo los hechos cerrados merecen snapshot.

### Tres métodos de reparto: PROPORTIONAL, EQUAL, CUSTOM

- EQUAL se implementa como `{name: 1}` en el mismo algoritmo que PROPORTIONAL.
- CUSTOM almacena `_custom_splits`. PROPORTIONAL/EQUAL se calculan dinámicamente.
- **`INDIVIDUAL` se consideró y se descartó:** el plan del refactor category-objects iba a añadirlo ("cada uno paga lo suyo", neto 0) para derivar `is_shared` de él. No entró: no está en el CHECK de la BD y `is_shared` como bool guardado lo hace innecesario. Los valores quedan en los tres que admite la BD.
- **Motivo:** EQUAL via `{name: 1}` reutiliza el código de PROPORTIONAL y mantiene la garantía de integridad de céntimos.

---

## Ingresos

### [26-05-26] `income_entries` con `affects_distribution`

- `Member.monthly_income` sigue existiendo como base congelada del acuerdo del hogar.
- Se añade `income_entries(member, period, amount, affects_distribution)` para ingresos variables.
- El cálculo del mes usa: `base_congelada + extras_del_periodo_que_afectan`.
- **Motivo:** una paga extra puede o no cambiar el reparto del mes — esa decisión le pertenece al miembro, no al sistema. Un campo booleano da esa agencia sin complicar el modelo base.
- **Pendiente de implementar** (roadmap Fase 1).

---

## Ahorro

### Tres niveles: Tracker → Account → Bucket

- `SavingTracker` → una instancia en el hogar.
- `SavingAccount` → una por miembro, creada en `freeze_registration_state()`.
- `SavingBucket` → ahorro finalista (vacaciones, ITV). Puede ser PERSONAL o SHARED.

### Retiros validados por destino, no por total

- `withdraw(destination=PERSONAL, amount=X)` valida contra `balance_personal`, no el total.
- **Motivo:** los fondos PERSONAL y SHARED no se mezclan automáticamente.

### Buckets SHARED: cada miembro retira solo lo que aportó

- `SavingBucket.withdraw()` valida contra `balance_by_member.get(member)`.
- Si un miembro retira más de su aportación, la diferencia genera deuda con el otro. **No implementado aún.**

---

## Deuda

### Compromiso (PLANNING) vs ejecución (MONTH) en sitios distintos

- Compromiso: `Household._member_debts[member]`. Declarado en PLANNING.
- Ejecución: `DebtAccount._entries`. Pagos reales en MONTH.
- **Motivo:** el compromiso es plan, la ejecución es hecho. Separación explícita.

### Capacidad de deuda+ahorro limitada a la parte de `reserva` del miembro

- `validate_debt_and_saving_dont_exceed_capacity()` comprueba `debt + saving_goal <= parte_reserva`.
- No incluye `loose_money` en la fórmula.
- **Motivo (24-03-26):** con el modelo actual `reserva` absorbe el sobrante y `loose_money = 0`. Incluirlo complicaba el modelo y fallaba en over-budget.

---

## Normalización

### `period_agreed_contributions.member_id` como FK a `members`

- Se eligió FK sobre nombre normalizado para tener integridad referencial real en BD.
- El riesgo de buscar por `full_name` sin UNIQUE constraint existe pero es manejable con 2-5 miembros por hogar.
- El repo traduce nombre→id internamente; el dominio nunca ve el id.
- **Motivo:** FK garantiza que no puedes guardar un acuerdo para un miembro que no existe. El nombre normalizado dependía de que la capa de arriba funcione bien — fragilidad silenciosa.

### `period_agreed_contributions` guarda total por miembro, no desglose por categoría

- El dominio congela `_agreed_contributions` como `{categoría: {miembro: amount}}`.
- La tabla solo guarda `{miembro: total}` porque las categorías no tienen `id` en BD todavía — no hay FK posible.
- Se pierde granularidad al leer desde BD, pero no hay descuadre: el total viene de sumar la misma fuente (`_agreed_contributions`).
- **Se amplía** cuando llegue `CategoryRepository` — el cambio es aditivo.
- **Motivo:** no añadir deuda técnica de FK a VARCHAR cuando la solución limpia (FK real a categorías) llega en el siguiente bloque.

---

### Nombres en lowercase en storage, Title Case en display

- `normalize_name()` en `src/utils/text.py`: strip + lowercase, valida no vacío.
- Aplicado en puntos de entrada: `Member.__init__`, `Expense.__init__`, lookups en WM/Household/Tracker.
- `format_name()` hace Title Case solo para mostrar.
- **Motivo:** `"Amanda" != "amanda"` es un bug esperando a pasar.

---

## Repositorios

### Verbo unificado `save` para inserts en repositorios

Todos los métodos de inserción usan `save`: `HouseholdRepository.save()`, `MemberRepository.save()`, `PeriodRepository.save()`, `ExpenseRepository.save()`.

**Por qué:** los repos anteriores usaban `add_household`, `add_member`, `create` — tres verbos para la misma operación. `save` es agnóstico (semánticamente: persiste el estado), consistente, y reduce fricción al leer el código.

---

## Ciclo mensual (`start_new_month`)

### Diseño de `start_new_month(year, month)`

`start_new_month()` cierra el mes actual (requiere fase `CLOSING`) y arranca un ciclo nuevo. Fase de destino: **`REGISTRATION`** — no `PLANNING` ni `MONTH`.

**Por qué REGISTRATION:** `set_member_incomes()` tiene `validate_phase(REGISTRATION)`. Si se salta a PLANNING, el usuario no puede re-declarar ingresos. El ciclo mensual real es `REGISTRATION → PLANNING → MONTH → CLOSING → (repeat)`.

**Qué se resetea:**

- `ExpenseTracker` → instancia nueva (gastos son por mes)
- `_registered_incomes` → `{}` (usuario re-declara)
- `_agreed_contributions`, `_agreed_percentages` → `{}` (se recalculan en `finish_planning()`)
- `_member_debts`, `_saving_goals` → `{name: 0}` (usuario re-declara)
- `_completed_phases` → `{REGISTRATION}`

**Qué persiste:**

- Miembros (el hogar no cambia cada mes)
- Categorías y presupuestos (carry-forward como punto de partida)
- `SavingTracker` (acumula saldo entre meses; la vista mensual filtra por fecha)
- `DebtTracker` (ídem — pero requiere el fix de filtro mensual)
- Método de reparto

**Guard necesario en `freeze_registration_state()`:** añadir `if not self.budget.categories:` antes de `budget.set_standard_categories()`. Sin esto, el segundo ciclo sobreescribe categorías y presupuestos con 0.

### Bug en `DebtTracker`: filtro mensual debe usar el período, no `datetime.now()`

`DebtAccount.total_paid` es acumulativo de toda la vida. `register_debt_payment()` lo usa para comprobar el límite mensual — en el mes 2, el contador ya arranca en el tope del mes 1.

**Fix:** añadir `DebtTracker.get_monthly_paid(member_name, month, year)` que delegue en `DebtAccount.get_monthly_summary`. `register_debt_payment()` lo llama con el mes/año del **período activo**, NO con `datetime.now().month`.

**Por qué no `datetime.now()`:** si hoy es 5 de febrero pero el período activo es enero (el usuario cobra el 7), el filtro devolvería 0 pagos de febrero y el límite de enero quedaría sin comprobar.

---

## Testing

### Un archivo de test por módulo

- `test_household.py` para `household.py`, etc.

### Estructura interna de los tests

- Sección `# FIXTURES` al principio, con docstring por fixture.
- Secciones `# ==== TESTS: <descripción> ====` con separadores visibles.

---

## SOLID pragmático

### Rule of Three: refactoriza al ver el patrón 3 veces, no antes

- Los trackers comparten patrón pero no hay interfaz común ni herencia.
- **Motivo:** hasta que el patrón necesite variaciones que justifiquen abstracción, duplicarlo es más simple.

### Triggers concretos para futuros refactors

- `Household > 300 líneas` → extraer `BudgetDistributionService`.
- `5+ métodos de reparto` → Strategy Pattern con `DistributionStrategy(Protocol)`.
- `BudgetCategory > 150 líneas` → dividir en `BudgetCategory` + `CategoryExpenseTracker`.
- `ExpenseRepository` → `Protocol` + implementaciones cuando llegue persistencia.
