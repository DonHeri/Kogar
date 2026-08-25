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

### Ancla de capacidad de deuda+ahorro tras "sobrante honesto" — OBSOLETO

Describía `validate_debt_and_saving_dont_exceed_capacity()` y `auto_assign_saving_goals()`,
ambas retiradas en el rediseño de deuda/ahorro (ver "Deuda" y "Ahorro" más abajo). El ahorro
ya no tiene "capacidad" que anclar a la reserva — es informativo, no se valida. Solo la deuda
se valida contra la reserva (`validate_debt_doesnt_exceed_capacity`). Si el problema de
"sobrante honesto" sigue vivo, es sobre reserva/deuda, no sobre ahorro.

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

- Ciclo vivo: `PLANNING → MONTH → CLOSING`.
- `WorkflowManager` orquesta las transiciones. `Household` no sabe en qué fase está.
- **Motivo:** el dominio es reutilizable. Las fases son un concepto de la aplicación, no del negocio.

### PLANNING absorbe REGISTRATION

Registrar miembros y fijar ingresos deja de ser una fase previa: se hace **dentro** del período
abierto, mientras se planifica. `finish_registration` desaparece; sus validaciones (hay miembros,
hay ingresos > 0) pasan a `finish_planning`.

**Motivo:** el registro solo es una fase de verdad el primer mes. A partir del segundo los miembros
ya existen, y obligar a repasar `REGISTRATION` forzaba a re-declarar ingresos cada mes — lo contrario
de aprovechar los datos del período anterior. Además la fase sobraba para corregir un ingreso mal
puesto: había que esperar al mes siguiente.

**`Phase.REGISTRATION` sigue en el enum y en el CHECK de BD**, sin uso. Se limpiará al migrar la capa
stateless, para no arrastrar ahora una migración de Alembic.

**Consecuencia detectada al quitar el gate:** `set_member_incomes` **sumaba** en vez de asignar
(`Member.add_incomes`). Con el gate solo se llamaba una vez por miembro, así que sumar y asignar
coincidían; con el ingreso editable, corregir 3000 → 4000 dejaba 7000. Se añadió `Member.set_income`
(asigna) y `Household.set_member_income` lo usa. `add_incomes` se mantiene para sumar de verdad.

### Congelar estado en transiciones

- `prepare_period()` (antes `freeze_registration_state`) crea los buckets de ahorro personales y las
  categorías estándar. **Ya no congela ingresos.**
- `freeze_planning_state()` cachea `_agreed_percentages` y `_agreed_contributions`.
- **Motivo:** mientras el período se planifica manda el **ingreso vivo** del miembro y el reparto se
  recalcula solo; lo que se congela es el **acuerdo**, en `finish_planning`. Un solo snapshot, y en el
  momento en que de verdad hay compromiso.

**Decisión cambiada:** existía `_registered_incomes`, una foto de los ingresos tomada al entrar en
PLANNING. Convivía con el ingreso vivo mediante **cinco** ramas `if self._registered_incomes: … else: …`
(cuatro en `Household`, una en `SettlementCalculator`), es decir dos fuentes de verdad para el mismo
dato. Eliminada: el acuerdo congelado ya cubre lo que había que preservar. De paso desaparece un bug
latente — `SettlementCalculator` hacía `if household.get_registered_incomes():` cuando ese getter
**lanzaba** al estar vacío, así que su rama `else` era inalcanzable.

**Lo que se pierde:** el ingreso base ya no queda congelado al entrar en MONTH; el settlement usa el
vivo. En la práctica es equivalente, porque `set_member_incomes` exige PLANNING y nadie puede tocarlo
con el mes en marcha. Si algún día hace falta blindarlo contra mutación directa del `Member`, la vía
es congelarlo en `finish_planning` junto al acuerdo, no reintroducir un registro aparte.

### Dos validadores de fase

- `validate_phase(X)` — estricto. Solo permite si `current_phase == X`. Para mutaciones.
- `validate_phase_accessible(X)` — permisivo. Permite si `X == current_phase` o `X in _completed_phases`. Para consultas.
- **Motivo:** puedes consultar `get_planning_summary()` en `MONTH`, pero no modificar presupuestos.

### Congelar estado en transiciones

- `freeze_registration_state()` cachea `_registered_incomes` y crea las cuentas de savings/debt y las categorías estándar.
- `freeze_planning_state()` cachea `_agreed_percentages` y `_agreed_contributions`.
- **Motivo:** el acuerdo del mes es inmutable. Cambiar un ingreso en `MONTH` no afecta al mes en curso.

### PLANNING como borrador hasta el congelado explícito — IMPLEMENTADO

- El usuario modifica miembros, ingresos, presupuesto y compromisos sin restricción durante todo
  PLANNING. El congelado es una acción deliberada: `finish_planning()` ("confirmar el plan").
- Los cambios de ingreso o categoría recalculan la distribución en vivo sobre los datos existentes.
- **Motivo:** en los primeros días del período una pareja real ajusta una o dos veces antes de
  comprometerse. La fase es un contrato, no un guardián desde el día 1.
- **Estado:** implementado al absorber REGISTRATION (ver arriba). Lo que queda fuera es editar el
  acuerdo una vez empezado el mes: eso sigue exigiendo PLANNING, y es deliberado.

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

## Servicios de aplicación (stateless)

### Reconstrucción completa del Household, no carga parcial

- Cada operación de un servicio reconstruye `Household` completo desde BD (vía `HouseholdLoader`), no carga parcial ad-hoc por operación.
- **Motivo:** el dominio (`Household` + trackers) ya centraliza los invariantes y cálculos. Cargar parcial obligaría a duplicar validaciones fuera del dominio, rompiendo la única fuente de verdad.
- **Matiz:** "completo" no es "todo lo que existe en BD" — es completo dentro de una profundidad elegida. Ver "Recetas de hidratación por profundidad".

### Recetas de hidratación por profundidad en `HouseholdLoader`

- El loader expone varios métodos públicos (`load_base`, `load_for_queries`, `load_members_only`...), cada uno componiendo helpers privados (`_hydrate_members`, `_hydrate_budget`, `_hydrate_expenses`...).
- **Motivo:** un solo `load()` que siempre trae todo sobre-hidrata a servicios que no leen ese estado (`ExpenseService.register_expense` no necesita histórico de gastos). Un loader por servicio duplicaría la construcción del `Household` base.
- **Regla de nombrado:** las recetas se nombran por **profundidad** (`load_with_budget`), no por caso de uso (`load_for_expense`) — dos servicios con la misma necesidad comparten receta sin que el loader conozca a sus llamadores.
- **Regla de cuándo añadir una receta:** solo con un segundo consumidor real. Los stubs (`load_with_debts`, `load_with_savings`, `load_with_buckets`) quedan vacíos hasta tener consumidor.

### Servicios stateless: persistir en cada llamada, no acumular hasta un método final

- `HouseholdService.register_member`/`set_member_income` persisten en BD de inmediato en cada llamada. No replican el patrón antiguo de acumular en memoria y guardar todo de golpe al final.
- **Motivo:** un servicio stateless no tiene memoria entre requests HTTP. Si una llamada no persiste, la siguiente no puede saber que la anterior ocurrió.
- **Consecuencia visible en `finish_planning`:** ahí **no** se persisten las categorías. Ya se guardaron al crearlas (`add_category`, `set_standard_categories`) y al presupuestarlas (`set_planned_amount`). Copiar el bucle equivalente de `WorkflowManager.finish_planning` provocaba `UniqueViolation` contra `UNIQUE (household_period_id, name)`. En la capa stateful ese bucle es correcto porque el presupuesto vive en memoria durante todo PLANNING; aquí no queda nada pendiente de volcar.
- **Corolario:** una llamada al dominio solo vale la pena si necesitas lo que produce. `freeze_planning_state()` se retiró de `finish_planning` por eso: congela en un objeto que se descarta al terminar, y `get_total_contributions_by_member()` calcula en vivo sin leer ese congelado. Lo que guarda el acuerdo es `save_agreed_contributions`.

### `start_new_month` vive en `PeriodService`, no en `HouseholdService`

El período es responsabilidad de `PeriodService`; `HouseholdService` se queda con el alta del hogar y sus miembros. Recibe `household_id` (no `period_id`) porque **crea** el período: no puede recibir el id de algo que aún no existe.

**Decisión cambiada:** lo tenía `HouseholdService` heredado de cuando el período nacía en `finish_registration`. Mantener dos puntos de apertura reproducía en esta capa el mismo bug que se arregló en `WorkflowManager`.

Al mover el método se arrastraron `validate_has_members()` y `validate_total_incomes_positive()`, que ahí **sobran**: los miembros se registran *después* de abrir el período, así que al crear el primero no hay ninguno. Esas validaciones viven en `finish_planning`.

### El orden de fases se deriva del enum, no de un set en memoria

`Phase.order` / `Phase.is_at_least()` dan al ciclo `PLANNING → MONTH → CLOSING` un orden explícito, y `PeriodService.validate_phase_accessible` lo usa.

**Motivo:** `WorkflowManager` se apoya en `_completed_phases`, un set que vive en memoria. Sin estado entre llamadas eso no existe, y la única fuente es `period.status`. Si el período está en MONTH, PLANNING ya pasó necesariamente: el orden basta.

`Phase.REGISTRATION` queda **fuera** del ciclo (`order == -1`), coherente con estar en desuso.

### Arrastre de configuración entre períodos

`start_new_month(carry_over=True)` copia del último período cerrado: categorías con su `planned_amount`, método de reparto y `custom_splits`. **No** copia gastos, pagos ni el acuerdo — eso pertenece al período que cerró, y el plan nuevo está por confirmar.

- **Motivo:** las `budget_categories` cuelgan de `household_period_id`, así que un período nuevo nace con cero categorías. Sin arrastre, el usuario reconstruye su presupuesto cada mes.
- **Cómo:** rehidratando el período anterior con `HouseholdLoader` y reescribiendo con los repos, en vez de un `INSERT … SELECT`. Más lento, pero pasa por el dominio y "qué se copia" se lee en Python en lugar de en SQL.
- **Es un borrador, no una imposición:** el usuario ajusta durante PLANNING lo que haya cambiado. `carry_over=False` para empezar de cero.

---

## Categorías

### Tres categorías estándar, autogeneradas al congelar registro

- `fijos`, `variables`, `reserva` se crean en `freeze_registration_state()`.
- **Motivo:** garantiza que `reserva` existe al entrar en `PLANNING`, sin validaciones extra.

### Dirección futura: solo `AutoCalculatedCategory` predefinida — el resto las crea el usuario

- En el modelo actual hay tres categorías estándar hardcodeadas. La dirección decidida es eliminarlas: la única categoría predefinida del sistema será la `AutoCalculatedCategory` (el tapón/sobrante). Todo lo demás lo crea el usuario.
- **Motivo:** el sistema vive para el usuario, no al revés. Imponer estructura es imponer un modelo de vida que no tiene por qué cuadrar.
- **Prerequisito:** árbol troncal/hoja (Fase 2). Hasta entonces, las tres categorías estándar siguen.
- **Estado:** decidido en dirección, sin implementar.

### Eliminación de categoría con gastos existentes

- Antes de eliminar una categoría, el sistema comprueba si existen gastos bajo ella.
  - Si **no hay gastos**: se elimina directamente.
  - Si **hay gastos**: la operación requiere un destino de reasignación. El usuario elige otra categoría activa; si no especifica, los gastos se mueven a la `AutoCalculatedCategory`.
- La `AutoCalculatedCategory` no se puede eliminar (es la única garantizada por el sistema).
- **Motivo:** borrar una categoría con gastos sin reasignar crearía gastos huérfanos que romperían el settlement. La `AutoCalculatedCategory` como fallback garantiza que los gastos siempre tienen destino.
- **Estado:** pendiente. Se implementa cuando se añada `delete_category()` en `WorkflowManager`.

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

### [IMPLEMENTADO] Jerarquía de categorías: el padre es un techo, no la suma de hijas

- `Category` pasa de plana a árbol: una categoría puede colgar de otra vía `parent`.
- **Decisión — padre con importe propio (techo), NO `Σ hijas`.** Las hijas son un desglose
  acotado (`Σ hijas ≤ techo`). **Motivo:** el usuario que no crea subcategorías debe poder
  presupuestar la raíz a secas, y hay gastos que no caben en ninguna hija. Si el padre fuera
  `Σ hijas`, una raíz sin hijas valdría 0. Esto **descarta el "gasto solo en hojas"** del roadmap:
  la raíz también recibe gasto directo.
- **Decisión — `parent` vive en `BudgetCategory`, por nombre.** No en `Category` (identidad) ni en
  `CategoryLibrary` (catálogo de clase, compartido por todos los hogares). El padre lo elige el
  usuario al planificar → es dato del presupuesto, no de la identidad.
- **Representación por referencia, no por contención.** Dict plano + `parent`=nombre (raíz =
  `None`), en vez de anidar las hijas dentro del padre. **Motivo:** mantiene los lookups O(1) por
  nombre que ya usa todo el código; contener obligaría a reescribirlos. Sin `id` en el objeto,
  coherente con "el dominio no porta el `id` de BD".
- **Dos regímenes en `Household.set_budget_for_category`:** raíz cuenta contra ingresos y recalcula
  `reserva`; hija se valida contra el techo de su raíz y **no** toca `reserva` (burbuja sellada — lo
  liberado en una raíz no fluye a otra; trasvasar entre raíces se hace moviendo los techos).
- **Diferido:** desbordar el techo de una hija tirando de `reserva` (avisar + aceptar). Cuando sea
  un problema real.
- **Estado:** implementado en memoria. Persistencia de categorías sigue siendo Fase D.

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

### [refactor/category-objects · SIN IMPLEMENTAR] Category como objeto con `is_shared`

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

### [26-05-26] `income_entries` con destino explícito

- `Member.monthly_income` sigue existiendo como base congelada del acuerdo del hogar.
- Se añade `income_entries(member, period, amount, destination)` para ingresos variables (pagas extras, bonus, ingresos irregulares).
- **`destination: IncomeDestination` enum — opciones:**
  - `DISTRIBUTION`: el importe se suma al ingreso del período y recalcula el reparto de presupuesto entre miembros.
  - `SAVINGS`: va directamente a la cuenta de ahorro del miembro (el usuario decide si PERSONAL o SHARED).
  - `CATEGORY`: se asigna a una categoría de presupuesto específica (el usuario elige cuál).
  - `DEBT`: se destina a cubrir la deuda comprometida del miembro.
- Cada entrada tiene **un único destino**. Para dividir un ingreso entre varios destinos, el usuario crea múltiples entradas.
- **Motivo:** un bool `affects_distribution` solo cubría "¿cambia el reparto o no?". Un destino explícito devuelve la agencia completa al usuario: el sistema no decide qué hacer con el dinero extra.
- **Nota de diseño:** `CATEGORY` puede requerir un campo adicional `category_name` en la entrada. `SAVINGS` puede requerir `scope: SavingScope`. Se resuelve al implementar.
- **Reemplaza** el diseño anterior con `affects_distribution: bool`.
- **Resuelto [20-06-26] (folio + sesión):**
  - **Campos de la entrada:** miembro, cantidad, `destination`, fecha (hoy o personalizada). Repartos admitidos por cantidad o por porcentaje.
  - **`get_total_incomes` = base + extras `DISTRIBUTION`.** Solo DISTRIBUTION afecta el total distribuible; los demás destinos no cambian el reparto, van directos a su sitio.
  - **DISTRIBUTION:** se avisa al usuario y se recalcula el *plan* (contribuciones). **Lo ejecutado se conserva** — gastos pagados, ahorros y pagos de deuda no se tocan. El usuario manda sobre el sistema. Ej: plan fijos 200→240 tras el extra, pero los 50 ya pagados quedan (ahora debe 190 más). Esto vuelve el acuerdo de planning re-editable: cambia el plan, nunca los hechos.
  - **CATEGORY:** el extra **sube el `planned_amount`** de esa categoría (misma mecánica que un ingreso alimentando el reparto), atribuido al miembro que lo aporta (es su dinero).
  - **DEBT:** el valor del enum existe desde el día 1; su handler se **activa cuando exista la entidad deuda rica** (ver `deuda_rediseno_analisis.md`). Hoy no hay una deuda a la que destinar.
  - **Validación:** no negativos, miembro inscrito, destino existente — salvo que el flujo permita crear categoría o bucket de ahorro al vuelo.
  - **Primer trozo construible:** modelo `IncomeEntry` + enum + `get_total_incomes` con DISTRIBUTION. DEBT/CATEGORY y la fase de recálculo, encima.
- **[01-07-26] Implementado en dominio. Decisiones cerradas:**
  - **Modelo: un entry = un destino.** Para múltiples destinos, el usuario crea múltiples entries.
  - **`_income_entries: list[IncomeEntry]`** es la fuente de verdad en Household. `_registered_incomes` nunca se muta después de `freeze_registration_state()`.
  - **DISTRIBUTION:** lazy — `get_total_incomes` y `preview_budget_contribution_summary` filtran `_income_entries` al calcular. El efecto inmediato es recalcular `_agreed_contributions` vía `get_current_contributions()`.
  - **CATEGORY:** sube el `planned_amount` de la categoría raíz (misma mecánica que asignar presupuesto).
  - **SAVING / DEBT:** delegan en `household.register_savings_deposit` / `register_debt_payment` con sus validaciones intactas.
  - **Dirección futura (no descartada):** `IncomeAllocation` — repartir un único ingreso entre varios destinos rastreando el destino de cada euro. Se implementa cuando el modelo de un destino resulte insuficiente.
- **Pendiente:** persistencia (migración `income_entries` aplicada; falta `IncomeEntryRepository` + wiring en WM).
- **[02-07-26] REDISEÑO — el extra no tiene destino; cae en reserva (vault). Supersede todo el diseño de destinos de arriba.**
  - **Se eliminó `IncomeDestination` y todos los handlers.** `IncomeEntry` es tonto: `member_name, amount_cents, date, description`. Nada de destino/scope/category.
  - **`get_total_incomes` = base congelada + TODAS las entries.** El extra es ingreso real; suma al total sin importar nada más.
  - **Al registrar un extra**, `IncomeEntryService.add_income_entry` hace `append` + `Household.recalculate_reserve()`. Reserva (autocalculada) = `total_incomes − otros_root_budgeted`. Como fijos/variables son números fijos (no %), **todo el extra cae en reserva**.
  - **Reserva es el "vault" del dinero sin presupuestar.** Desde ahí el usuario mueve el dinero con los métodos que ya existen (`set_budget_for_category`, `register_savings_deposit`, `register_debt_payment`). Futuro: entidad de **transferencia interna** para ese movimiento.
  - **Por qué se abandonaron los destinos:** poner destino en el extra era fricción y duplicaba comportamientos que ya viven en reserva y en los trackers. Un extra o se queda en el bote común (reserva) o el usuario lo mueve luego; el entry no tiene por qué decidir.
  - **Settlement:** usa `_agreed_contributions` congelado en `finish_planning`. El extra (MONTH) no reescribe el acuerdo.
  - **`missing_money` NO es fuente de verdad.** Como reserva absorbe el resto, `total_budgeted == total_incomes` por construcción → `missing_money ≈ 0`. La verdad del dinero libre es el `planned_amount` de reserva.
  - **Limitación conocida (diferida):** `get_current_contributions()` (vista en vivo) reparte el `planned_amount` de reserva —ya crecido con el extra— por el método, atribuyendo a otros miembros parte del extra que puso uno solo. El **settlement no se ve afectado** (usa lo congelado); la vista viva sí. Se resolverá con atribución por miembro / la transferencia interna.
  - **`allow_overpayment`** en `register_debt_payment`: se mantiene (sin caller aún) por decisión de Heri.
  - **Pendiente:** persistencia real — `IncomeEntryRepository.save()` listo con esquema simple (`period_id, member_id, amount_cents, entry_date, description`); falta wiring/tests (tarea 2).
  - **[02-07-26] Cerrado en código:** `get_missing_money()`/`get_missing_money_by_member()` eliminados. Sustituidos por `get_reserve_contribution_by_member()`, reutilizado también en `validate_debt_and_saving_dont_exceed_capacity` y `auto_assign_saving_goals` (antes duplicaban el mismo cálculo inline).

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

### `saving_buckets`/`bucket_owners` cuelgan de `household_id`; `bucket_entries` de `period_id`

Un `SavingBucket` se crea en PLANNING+ y vive a través de varios meses (tiene `deadline`,
no es un concepto mensual como `expense`/`saving_entry`/`debt_entry`). Sus movimientos
(`deposit_to_bucket`/`withdraw_from_bucket`) sí son de fase MONTH.

**Decisión:** la entidad (`saving_buckets`, `bucket_owners`) cuelga de `household_id`; solo
los movimientos (`bucket_entries`) cuelgan de `period_id`, igual que `saving_entries`, para
poder consultar qué se metió en buckets cada mes.

### `saving_buckets.id` usa el UUID del dominio como PK directa, no id serial + mapeo

`SavingBucket` ya genera su propio UUID en el constructor (`uuid4()`), usado como identidad
pública en toda la API (`get_bucket_by_id`, `deposit_to_bucket`...).

**Decisión:** usar ese mismo UUID como PK de `saving_buckets`, en vez de un `id` serial +
un dict de mapeo `uuid → id` en `WorkflowManager` (como `member_ids`). La alternativa
serial no elimina el problema, solo lo mueve — el dominio seguiría necesitando el UUID como
identidad pública igualmente.

**Por qué es la única excepción a "los objetos de dominio no portan el `id` de BD":** aquí
el UUID nace en el dominio como identidad pública, no como artefacto de persistencia — a
diferencia de `Member`/`Expense`/`DebtEntry`, que no tienen `id` propio hasta que la BD se
lo asigna.

**Requiere:** `psycopg2.extras.register_uuid()` en los repos que tocan `bucket_id` (ver
LEARNINGS — psycopg2 no adapta `uuid.UUID` por defecto).

---

## Deuda

### DebtBucket: cuota real del usuario, no plazo declarado

- `DebtBucket` recibe `principal_cents` + `installment_cents` (la cuota real de su
  financiación, la del papel del banco) + `owner`. NO recibe plazo.
- El plazo/nº de cuotas restantes se deriva: `remaining_installments = ceil(remaining_balance
  / installment_cents)`.
- **Por qué:** declarar plazo junto a cuota es redundante y puede contradecirse (¿manda el
  plazo o la cuota si no cuadran?). Con principal+cuota como únicas fuentes de verdad, el
  plazo no tiene ambigüedad posible — siempre se recalcula desde datos reales.
- **Sobrepago sin restricción** — mismo precedente que `missing_money`: el backend no decide
  por el usuario.
- **Deuda es personal** (un único `owner`). Deuda compartida (reparto en settlement) queda
  aparcada a una versión futura.

---

## Ahorro

### Todo el ahorro vive en SavingBucket — sin cuentas, sin scope

- Se retiraron `SavingAccount`/`SavingEntry`: había dos modelos para lo mismo (cuenta vs
  bucket), con comportamientos que divergían según cuál tocaras.
- `SavingBucket` no lleva scope. Personal/compartido se deriva de `owners`
  (`is_shared = len(owners) > 1`).
- **No hay bucket "colchón" automático por miembro.** Decisión explícita: el usuario siempre
  elige a qué bucket deposita o de cuál retira — incluido crear uno sin meta si quiere ahorro
  libre. Nada se le asigna de oficio.

### El compromiso de ahorro es informativo, nunca una obligación

- Se retiró `_saving_goals`/`set_member_saving_goal`/`auto_assign_saving_goals`. Antes el
  ahorro se declaraba a mano como un número plano, igual que la deuda vieja.
- **Por qué distinto a deuda:** deuda es casi-obligación (un banco espera su cuota); ahorro es
  elección. Validarle capacidad contradice esa naturaleza.
- Cada `SavingBucket` con `goal`+`deadline` deriva `required_monthly_contribution` en vivo
  (cuánto haría falta este mes para llegar a tiempo) — cálculo de pantalla, nunca un dato
  guardado ni algo que bloquee nada.
- **Recalcula sobre el estado actual, no un snapshot:** cambia con cada depósito/retiro sin
  que nadie lo actualice a mano.
- `validate_debt_and_saving_dont_exceed_capacity` → `validate_debt_doesnt_exceed_capacity`:
  el ahorro sale de la validación, solo la deuda se compara contra la reserva.

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

### Diseño de `start_new_month(start_date)`

`start_new_month()` abre un ciclo nuevo. Fase de destino: **`PLANNING`**.

**`start_new_month` es el único punto por el que nace un período — incluido el primero.** El programa arranca ahí. Si ya hay un período, debe estar cerrado; si no lo hay (arranque en frío), abre el primero sin exigir nada. Cerrar y abrir siguen separados: `finish_month` cierra (pone `end_date` y `status`), `start_new_month` abre el siguiente.

**La fecha de inicio se inyecta; por defecto, hoy.** Se probó heredar el `end_date` del período
anterior para no dejar huecos, y se descartó: si el usuario cierra febrero el 2 de marzo y no vuelve
hasta mayo, heredar abre un período que arranca dos meses atrás, y un gasto fechado en marzo pasa la
validación y se cuela en él. **Un hueco entre períodos es un uso esperado** — el usuario pasó un
tiempo sin usar la aplicación; fingir que ese tiempo pertenece a un período es peor que reconocer que
no lo cubre ninguno. Cualquier automatismo intermedio ("heredar solo si han pasado menos de X días")
sería un umbral inventado.

Lo que sí sostiene el dominio es **una** invariante: el período nuevo no puede empezar antes de que
acabe el anterior. Un hueco es legítimo; un solape no, porque ahí un movimiento caería en las dos
ventanas y contaría dos veces.

**Decisión cambiada:** antes el período nacía dentro de `finish_registration`, y `start_new_month` solo podía dejar `period_id = None` y esperar a que el usuario volviera a llamarla. Eso abría una ventana sin período activo en la que toda persistencia se saltaba en silencio, y si el usuario llamaba a `finish_registration` después de `start_new_month` se creaban **dos** períodos para el mismo ciclo. Con un único punto de apertura, ni ventana ni duplicado.

**El hogar se crea antes que el período.** `household_periods.household_id` es `NOT NULL REFERENCES households(id)`, así que `_ensure_household()` (idempotente) corre dentro de `_start_period` antes de construir el `Period`. Antes el hogar se creaba en `finish_registration`, es decir *después* de abrir el período: con `start_new_month` como arranque, eso reventaba por FK. Los miembros se persisten aparte (`_persist_new_members`, también idempotente) porque al abrir el primer período todavía no existen.

**Decisión cambiada:** antes `start_new_month` se permitía desde PLANNING/MONTH/CLOSING y cerraba él mismo el período — duplicaba lo que ya hacía `finish_month`. Se separó para que cada método haga una cosa (encaja con `/close` vs `POST /periods` del roadmap Fase 5).

**Decisión cambiada — el destino pasa de REGISTRATION a PLANNING:** el argumento original era que `set_member_incomes()` exigía `validate_phase(REGISTRATION)`, así que saltar a PLANNING dejaba al usuario sin poder re-declarar ingresos. Se dio la vuelta al problema: en vez de mantener una fase entera para poder tocar los ingresos, los ingresos pasan a ser editables **dentro** de PLANNING (ver "PLANNING absorbe REGISTRATION"). El ciclo real es `PLANNING → MONTH → CLOSING → (repeat)`.

**Qué se resetea:**

- `ExpenseTracker` → instancia nueva (gastos son por mes)
- `_agreed_contributions`, `_agreed_percentages` → `{}` (se recalculan en `finish_planning()`)
- `_income_entries` → `[]`

**Qué persiste:**

- Miembros (el hogar no cambia cada mes)
- Categorías y presupuestos (carry-forward como punto de partida)
- `DebtBucketTracker` y `SavingBucketTracker` completos — buckets, saldos e histórico de entries. Ambos son household-scoped, no period-scoped: cruzan meses por diseño.
- Método de reparto

**Decisión cambiada:** antes `DebtTracker` se reinstanciaba cada mes (el compromiso de deuda era un valor plano, mensual). Con `DebtBucket` (saldo que decrece desde un principal fijo, multi-mes) reinstanciar el tracker borraría el saldo real de la deuda junto con su histórico. Ahora ni deuda ni ahorro se resetean — ambos son entidades del hogar, no del período. La asimetría vieja ("ahorro acumula, deuda es mensual") desaparece: la deuda también pasa a ser multi-mes. Lo que sigue siendo mensual es la *vista*, no el estado (ver siguiente sección).

**`finish_registration` ya no abre período ni crea el hogar.** Pasa a ser un paso *dentro* de un período ya abierto: valida, congela ingresos y avanza de fase. **Decisión cambiada:** antes hacía las tres cosas, y por eso los guards `not self.household_id` / `not self.period_id` existían — eran el parche de tener la apertura en dos sitios. Al quedar un único punto de apertura, sobran.

### Cerrar un período es el fin de su ventana, no haber completado el ritual

`finish_month` **no exige estar en `MONTH`**: cierra desde cualquier fase mientras el período siga abierto.

**Motivo:** un usuario puede abrir un período, tocar cuatro cosas y no llegar a usarlo. Con la regla estricta quedaba atrapado — no podía cerrarlo (`finish_month` pedía `MONTH`) ni abrir el siguiente (`start_new_month` pedía `CLOSING`), y el período se quedaba con `end_date` a NULL para siempre, tragándose por rango todo lo que viniera después. Cerrar un período que no se usó es legítimo: existió y su ventana acaba ahí.

**Por qué no un flag `force`:** una bandera comunica "esto es anómalo", y no lo es. Compárese con `allow_overpayment`, donde sí lo es. Si la acción es legítima, lo que está mal es la regla, no la falta de un bypass. Además el `force` que se probó falseaba `_completed_phases` marcando `PLANNING`/`MONTH` como completadas sin haberlo estado, lo que habilitaba consultas de `MONTH` sobre un período que nunca se planificó. El "¿seguro que cierras sin usarlo?" es de la capa de presentación.

### El rango del período es semiabierto `[inicio, fin)`

Los filtros de movimientos (`DebtBucket.get_period_balance`, `DebtAccount.get_period_summary`, `SavingBucket.get_period_deposits`, `SavingBucketTracker`) usan `inicio <= fecha < fin`.

**Motivo:** el período siguiente empieza exactamente en el `end_date` del anterior, para no dejar huecos. Con el fin inclusivo, un movimiento hecho **el día del corte** caía dentro de las dos ventanas y se contaba dos veces. Con el fin exclusivo pertenece solo al período que empieza.

**Por qué no `datetime` en vez de `date`:** se valoró y no resuelve nada. El solape no viene de falta de precisión sino de que la regla usaba `<=` en los dos extremos; con hora, el instante exacto del corte sigue perteneciendo a ambos. Además los movimientos ya guardan `datetime`, así que la precisión ya está donde importa; y "mi período acaba el 28" es un concepto de día — pedir una hora de corte complica el modelo y obligaría a migrar `end_date` de `DATE` a `TIMESTAMP`.

**Un período abierto no tiene techo:** `_current_period_range()` devuelve `date.max` como fin mientras no se cierre, para que lo registrado hoy cuente. El techo aparece al cerrar.

### Un movimiento no puede tener fecha anterior al inicio del período abierto

`_validate_movement_date()` rechaza fechas previas al `start_date` en `register_debt_payment`, `deposit_to_saving_bucket` y `withdraw_from_saving_bucket`.

**Motivo:** el usuario entra a empezar período nuevo y apunta pagos atrasados. Si la fecha cae en el período anterior (ya cerrado), el movimiento quedaba guardado pero **invisible**: fuera de la ventana del período actual, y sin forma de consultarlo en uno cerrado, porque el dominio solo conoce `self.period`. Ahora salta el aviso y el usuario decide: registrarlo con fecha de este período (y que cuente aquí) o descartarlo.

**Por qué esto y no un indicador de período en cada movimiento:** ya existen dos formas de decidir a qué período pertenece algo — la fecha (dominio) y el `period_id` con que se persiste (BD) — y pueden contradecirse. Separar "cuándo ocurrió" de "a qué período cuenta" era la alternativa, pero exige propagar imputación por todo el modelo. Validando en la entrada, **la fecha queda como única verdad** y desaparece la contradicción: ya nunca hay un movimiento cuya fecha caiga fuera del período con el que se guardó.

**Consecuencia asumida:** un período cerrado es inmutable. No se registra nada en él hacia atrás. El aviso de "registra todo lo que falte" va **antes** de cerrar, y cerrar no tiene vuelta atrás.

### Consultar deuda por período: `committed`/`paid` se filtran por fecha, el tracker no se resetea

`DebtBucketTracker` ya no se reinstancia en `reset_for_new_month` — los buckets y su histórico de pagos cruzan meses. Por eso `get_debt_status`/`get_all_debts_summary` sí necesitan `start_date`/`end_date` (`WorkflowManager._current_period_range()`) para filtrar qué pagos cuentan como "pagado este período" (`DebtBucket.get_period_balance`). `committed`, en cambio, **no** se filtra por fecha: siempre es `next_installment`, la cuota vigente del bucket en el momento de la consulta — no una cifra declarada por mes.

**Decisión cambiada:** la nota anterior decía que `register_debt_payment` ya no recibía fechas porque el tracker se reiniciaba cada mes. Es al revés: el tracker NO se reinicia, así que es la *consulta* (`get_debt_status`) la que necesita el rango de fechas, para no arrastrar pagos de meses anteriores en el total "pagado este período". `register_debt_payment` en sí sigue sin rango — registra un pago puntual con `payment_date`, igual que antes.

**`payment_date` es `datetime`, no `date`:** `DebtEntry.date` es `datetime` y valida `self.date > datetime.now()` en `__post_init__`. El WM resuelve `payment_date = datetime.now()` una sola vez y lo propaga a dominio y repo (misma fecha en memoria y BD). Pasar un `date` rompería la comparación.

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
