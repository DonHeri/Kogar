# TODO — Refactor de ecosistemas: Ahorro (buckets) · Deuda (saldo) · Automatización

**Qué es esto:** el desglose en tareas de la refactorización decidida el 2026-07-12. Lo
construyes tú. Diseño y porqué completos en el plan
(`~/.claude/plans/actualmente-el-ahorro-en-pure-rivest.md`); análisis de deuda en
`deuda_rediseno_analisis.md`. Este archivo es la lista de trabajo, no el rodante `TODO.md`
(ese sigue vivo con Fase 4/5 en paralelo).

**Cómo se usa (igual que `TODO.md`):** cada tarea lleva 5 campos + un `#### Mi hipótesis`
debajo donde escribes tu plan de ataque **antes** de abrir el chat. Las _Decisiones a tomar_
son tuyas: no están resueltas a propósito. Cuando cierras una tarea, la marcas hecha (git es el
historial). Orden = orden de dependencia; dentro de cada fase puedes reordenar.

**Espejo maestro:** `SavingBucket` (`src/models/saving_bucket.py`) +
`BucketTracker` (`src/models/bucket_tracker.py`) + sus tests. Deuda y ahorro se apoyan en él.

---

## Restricciones ya decididas (NO son decisiones abiertas)

- **Deuda v1: principal + cuota (la real del usuario), personal (1 owner), SIN interés.** La
  cuota la fija el usuario (fuente de verdad); el nº de cuotas se deriva del saldo. El interés y
  la **deuda compartida** (varios owners → reparto en settlement) se aparcan a versiones futuras.
- **Ahorro: todo es un bucket.** Objetivo opcional; ahorro libre = bucket por defecto; se jubila
  `SavingAccount` y la bandera `scope` de cuenta.
- **Secuencia: dominio de deuda primero** (memoria + tests), persistencia al final. El cimiento
  stateless (`PeriodService`, tarea Fase 4 del `TODO.md`) madura en paralelo.

---

# FASE 1 — Deuda: dominio en memoria

### T1. `DebtBucket` — entidad con saldo que decrece #TODO Tests

- **Objetivo:** una entidad de deuda que declara principal + plazo y deriva saldo restante y
  cuota-guía; el pago real manda y cierra a saldo 0.
- **Por qué:** hoy la deuda es un número plano re-declarado cada mes, sin saldo ni vida. Esta
  entidad es el gemelo del `SavingBucket` con signo opuesto y el corazón del rediseño.
- **Abarca:** clase nueva en `src/models/` espejando `saving_bucket.py`. Declarados: nombre,
  `principal_cents`, `term_months`, `start_date`, owner. Derivados: `paid` (Σ pagos),
  `remaining_balance` (principal − paid), `expected_installment` (saldo/plazo restante),
  `is_closed`. `pay()` reutiliza `DebtEntry` (`src/models/debt_entry.py`) tal cual. Tests nuevos
  espejando `tests/test_saving_bucket.py`.
- **Decisiones a tomar:**
  - ¿Deuda estrictamente personal (1 owner) o admites compartida ya? (Compartida abre reparto
    en settlement — ¿aditivo después?)
  - `expected_installment`: ¿división entera simple o largest-remainder como el resto del
    proyecto? ¿Qué pasa cuando `remaining_term` llega a 0 pero queda saldo?
  - Sobrepago: ¿un pago que excede `remaining_balance` se rechaza, se capa al saldo, o se
    permite dejando saldo negativo? (Esto sustituye al parche `allow_overpayment`.)
- **Hecho cuando:** registras 3.000€ a 12 meses, pagas dos cuotas reales de distinto importe, el
  saldo decrece exacto, (la cuota-guía se recalcula [no se debería recalcular cada mes, el usuario solo debería realizar un pago]0) y la deuda cierra al llegar a 0. Tests verdes.

#### Mi hipótesis:

- Primero que nada he creado una rama para la refactorización, de ese modo aislamos los problemas

Para empezar, creo la entidad de DebtBucket:
Que és DebtBucket:

- Representa cualquier deuda, puede ser personal o compartida dependiendo de los miembros responsables
  Que tiene?
- Tiene un nombre
- Un total a pagar
- Un día del pago
- Cantidad pagada (Verdad)
- Estimación de siguiente cuota (Aproximación) - Aunque las cuotas mensuales suelen ser las mismas, como resuelvo el problema de evitar que el usuario introduzca cada mes la cantidad que va a pagar? Podría hacer que el ultimo pago de la cuota sea el reflejo de lo que pagará el mes siguiente, y así evito poner un nuevo atributo.
- Un interés(futuro)
- Tiene también una fecha límite / O último pago
- Opcional- Cuota por pago anticipado que suele ser el 1% del total restante.

En cuanto al id, prefiero la generación del id en dominio o en bd? por ser fiel a saving, en dominio, aunque también puedo cambiarlo en saving y hacer a bd, id más corto, uuid no aporta más seguridad.

En cuanto a comportamientos, los mismo que savingbucket, ingresar y retirar, balances, responsables, meta y id

El sobrepago, bueno, caso aislado, pero el programa no prohibe lo que pase en la vida real, Kogar solo muestra calculos y números, si hay alguna situación particular, es responsabilidad del usuario.

#### Cierre de decisiones (tras discutir con el agente):

- **Retiro:** no existe. Deuda solo tiene `pay()`. Un pago erróneo se corrige con otro `pay()`
  en negativo (mismo mecanismo que ya permite `DebtEntry`), no con un `withdraw()` simétrico a
  ahorro.
- **Id:** UUID generado en dominio, en `__init__`, mismo patrón que `SavingBucket` (`DECISIONS.md`
  — identidad pública nace antes de persistir, no es tema de seguridad). No se toca `SavingBucket`.
- **Cuota estimada (`expected_installment`):** `remaining_balance / max(remaining_term_months, 1)`,
  asumiendo plazo fijo. No es predicción de comportamiento — es la meta para terminar a tiempo,
  igual que un banco ofrece "reducir cuota" tras una amortización anticipada, no adivina qué
  pagarás. Sin largest-remainder: se recalcula cada mes y el último (`remaining_term_months == 1`)
  absorbe el resto solo. Descartada la idea de "cuota = último pago real" — falla en cuanto el
  usuario paga de más o de menos (ejemplo trabajado: deuda de 1.200€/12 meses, pago extra de 300€
  en el mes 3 rompe la predicción y corrompe `auto_assign_saving_goals`).
- **Sobrepago:** confirmado sin restricción — alineado con el precedente de `missing_money` en
  `DECISIONS.md` ("el backend no decide por el usuario").
- **Personal/compartida:** confirmado que admite ambas vía owners. Cabo suelto sin resolver: el
  reparto en settlement de una deuda compartida — no bloquea T1, queda pendiente para T3/T4.

**Pendiente de decidir (sin resolver — no las cierra el agente, son tuyas):**
- "Fecha límite" vs `start_date + term_months`: parecen redundantes — decide si guardas el campo
  o lo derivas.
- "Día del pago": aclara si es distinto de `start_date` o es la misma fecha con otro nombre.
- "Cuota por pago anticipado (1%)": es complejidad de interés — decide si entra en v1 o se aparca
  junto con el interés, que ya dijiste que era capa aditiva posterior.

---

### T2. `DebtBucketTracker` — registro de deudas del hogar

- **Objetivo:** el orquestador que guarda los `DebtBucket` del hogar, busca por id, delega pagos
  y expone queries agregadas.
- **Por qué:** espeja a `BucketTracker`; es lo que `Household` compondrá en lugar del
  `DebtTracker` viejo.
- **Abarca:** clase nueva espejando `src/models/bucket_tracker.py` (add, get_by_id, delegar
  pay, queries agregadas por miembro / totales). Tests espejando `tests/test_bucket_tracker.py`.
- **Decisiones a tomar:**
  - ¿Clave por UUID (como buckets) o por otra identidad? ¿Query "deudas activas de un miembro"
    la necesitas aquí para la capacidad (T3)?
  - ¿`DebtBucketTracker` reemplaza el nombre `DebtTracker` o convive?
- **Hecho cuando:** puedes añadir varias deudas, recuperarlas por id, pagar la correcta y sumar
  la cuota-guía de las deudas de un miembro. Tests verdes.

#### Mi hipótesis:

- Se queda pendiente refactorizar el calculo de la cuota: mi propuesta es como los bancos, una cuota fija cada mes. Y exponer un metodo que permita adelantar dinero de la deuda. Y entonces recalcular cuota. Además de un método que permita settear la cuota mensual. El usuario siempre debe poder hacer esos cambios. 

- Además, me gustaría que la cuota por dentro siga siendo un entero, para mantener coherencia con todo el sistema



---

# FASE 2 — Deuda: cableado en dominio y fachada (memoria)

### T3. Cablear deuda en `Household`

- **Objetivo:** `Household` declara deudas y registra pagos contra ellas; la capacidad mensual
  consume la cuota derivada, no el compromiso plano.
- **Por qué:** conecta la entidad nueva al núcleo y jubila `_member_debts`.
- **Abarca:** en `src/models/household.py`: `register_debt(...)` (fase PLANNING+, una deuda se
  declara una vez); `register_debt_payment` pasa a apuntar a `debt_id` (fase MONTH); retirar
  `_member_debts` (`:92,:260`); `auto_assign_saving_goals` (`:141`) y
  `validate_debt_and_saving_dont_exceed_capacity` (`:120`) pasan a sumar cuota-guía de las
  deudas activas del miembro; `get_debt_status` (`~:514`) devuelve saldo/principal/pagado/cuota.
- **Decisiones a tomar:**
  - ¿En qué fase se declara una deuda? (PLANNING+ como crear bucket, o también en MONTH.)
  - Con `_member_debts` fuera, ¿cómo se comporta `reset_for_new_month` respecto a las deudas?
    (Las deudas cruzan meses → NO deberían reinstanciarse; ver T9.)
  - ¿La capacidad usa la cuota-guía del mes o el pago real esperado? ¿Qué cuenta como "deuda
    activa"?
- **Hecho cuando:** declaras deuda, pagas por `debt_id`, la capacidad deuda+ahorro cuadra con la
  cuota derivada, y `get_debt_status` refleja el saldo real. Tests de `test_household` adaptados.

#### Mi hipótesis:

Decisión que hemos pasado por alto, y creo que vale la pena destacar:
En una deuda compartida, cuanto paga cada uno? el usuario define la cuota de ambos, la cuota de cada uno por separado? entonces para una misma deuda, se crearian dos buckets, uno por persona con su respectiva cuota.

---

### T4. Cablear deuda en la fachada + smoke end-to-end

- **Objetivo:** las operaciones de deuda nuevas se exponen desde la fachada con euros→céntimos
  en el borde, y la simulación end-to-end pasa con el modelo nuevo.
- **Por qué:** cierra el camino en memoria antes de tocar persistencia; el smoke prueba que las
  firmas nuevas encajan de registro a cierre.
- **Abarca:** `src/workflow/workflow_manager.py` (`set_member_debt:215` → `register_debt`;
  `register_debt_payment:227` por `debt_id`; `get_debt_status:257`); jubilar
  `DebtTracker`/`DebtAccount` (`src/models/debt_tracker.py`, `debt_account.py`); actualizar
  `examples/full_month_simulation.py` (`:147-231`) y `tests/test_workflow_manager.py`.
- **Decisiones a tomar:**
  - ¿Cableas también el camino de `PeriodService` ahora, o solo `WorkflowManager` y dejas
    `PeriodService` para la fase de persistencia (T7)?
  - Firma de `register_debt` desde fuera: ¿qué campos en euros, cuáles opcionales?
- **Hecho cuando:** `python examples/full_month_simulation.py` corre entero con deuda rica, y
  `pytest tests/ -q --no-cov` verde.

#### Mi hipótesis:

---

# FASE 3 — Ahorro: unificar en buckets (dominio)

### T5. `SavingBucket` con objetivo opcional + bucket por defecto (colchón)

- **Objetivo:** un bucket puede no tener objetivo (colchón/informal), y cada miembro tiene un
  bucket por defecto para el ahorro libre.
- **Por qué:** elimina el segundo modelo mental (cuenta con scope) unificándolo en el bucket.
- **Abarca:** `src/models/saving_bucket.py` → `goal_cents: int | None` (espejar cómo `deadline`
  ya es opcional; ajustar validación y `__str__`/progreso); crear el bucket por defecto por
  miembro donde hoy se crea la `SavingAccount` (`household.py:64-75`,
  `freeze_registration_state`). Tests: bucket sin objetivo, bucket por defecto.
- **Decisiones a tomar:**
  - ¿El colchón es un bucket normal o un tipo marcado no-borrable (como la
    `AutoCalculatedCategory` es intocable)?
  - ¿El bucket compartido por defecto se auto-crea al congelar registro o perezosamente al
    primer depósito shared?
  - Con `goal=None`, ¿qué muestra el progreso? ¿Cómo afecta a queries que asumían goal>0?
- **Hecho cuando:** creas un bucket sin objetivo y depositas; existe un colchón por miembro tras
  congelar registro. Tests verdes.

#### Mi hipótesis:
1. He creado un método en Household que crea un bucket personal para cada uno de los miembros del núcleo. Opino que crear de entrada un ahorro compartido para el núcleo es un error, lo veo como una decisión que debe tomar el usuario. 
  Tests
El bucket personal es un acierto ya que me servirá para poder hacer rápida la opción de enviar el dinero de un miembro a ahorro, siempre y cuando no decida un bucket.\\ Es obligatorio para permitir que cualquiero miembro ahorre sin necesidad de crear un bucket personal antes
2. Puedes llegar a tener sentido que el colchón sea un intocable. Eso nos permite tener siempre un acceso para el ahorro de un miembro y evitarle tener que crearlo o eliminarlo sin querer. 
3. No se debería poder hacer un depósito shared sin antes indicar un bucket shared, por tanto el usuario debería crearlo antes. 
4. Progreso solo muestra lo ahorrado, no hay más que mostrar si no tiene una meta, es un ahorro pasivo. Quizás un ahorro medio según los tres ultimos ahorros, pero meramente informativo 
  Cuales queries asumen goal>0?



---

### T6. Jubilar `SavingAccount`/`SavingEntry` y recablear el ahorro libre

- **Objetivo:** el ahorro libre deja de vivir en cuentas y pasa a `BucketEntry` del bucket por
  defecto; la agregación personal/compartida es un único mecanismo.
- **Por qué:** completa la unificación; queda un solo camino para "ahorrar".
- **Abarca:** retirar `src/models/saving_account.py` y `saving_entry.py`; `SavingTracker`
  (`saving_tracker.py`) pierde `_accounts` y sus queries de cuenta; `Househ.
  (`register_savings_deposit:166`, `register_savings_withdrawal:184`,
  `get_member_savings_summary`) y la fachada (`workflow_manager.py:410`) redirigen al bucket por
  defecto; `_saving_goals` (compromiso mensual) sigue existiendo pero "lo ahorrado este mes"
  deriva de las `bucket_entries` del período. Adaptar tests.
- **Decisiones a tomar:**
  - "Depositar ahorro libre" sin nombrar bucket: ¿va siempre al colchón, o exige elegir bucket?
  - ¿Cómo distingue la API un depósito a colchón de uno a un bucket con objetivo? (¿misma
    operación con bucket_id por defecto?)
  - `get_saving_goal_status`: ¿"paid" pasa a ser Σ entries del período en todos mis buckets?
- **Hecho cuando:** un depósito libre y uno con objetivo conviven en el mismo modelo; la meta
  mensual (`_saving_goals`) sigue cuadrando contra lo ahorrado derivado de entries. Tests verdes.

#### Mi hipótesis:

---

# FASE 4 — Persistencia y rehidratación (sobre el cimiento stateless)

### T7. Persistencia de deuda (tabla `debts` + rehidratación)

- **Objetivo:** una deuda y sus pagos se guardan y se reconstruyen entre meses.
- **Por qué:** una entidad multi-mes no vive en el modelo reseteado-cada-mes; sin esto la deuda
  rica no sobrevive.
- **Abarca:** migración Alembic para tabla `debts` (UUID PK como `saving_buckets`,
  `household_id`, `name`, `principal_cents`, `term_months`, `start_date`, owner) + añadir
  `debt_id` FK a `debt_entries`; `DebtRepository` (hoy `debt_entry_repository.py` solo pagos);
  implementar `_hydrate_debts` (`household_loader.py:182`); rellenar stubs de deuda de
  `PeriodService` (`period_service.py:186-189`).
- **Decisiones a tomar:**
  - `debts` cuelga de `household_id` (cruza meses) — confirma el scoping frente a lo period-scoped.
  - ¿`debt_entries` conserva `period_id` y `member_id` además de `debt_id`? (Sí para saber en
    qué mes y quién pagó — útil para el aprendizaje.)
  - ¿Owner en `debts` como FK a `members` o como nombre? (Ver decisión FK vs nombre en
    `DECISIONS.md`.)
- **Hecho cuando:** guardas deuda + pagos, cierras y reabres el mes, y el saldo reaparece exacto
  al rehidratar. Test de rehidratación verde (hoy imposible: `_hydrate_debts` es stub).

#### Mi hipótesis:

---

### T8. Persistencia de ahorro (rehidratar buckets + goal nullable)

- **Objetivo:** los buckets y sus movimientos se reconstruyen entre meses; el ahorro por fin
  acumula de verdad.
- **Por qué:** es el hueco real del ahorro (escribe pero no rehidrata). Sin esto, unificar en
  buckets no arregla nada.
- **Abarca:** migración `saving_buckets.goal_cents` → nullable; implementar `_hydrate_buckets`
  (`household_loader.py:188`) desde `saving_buckets` + `bucket_owners` + `bucket_entries` (repos
  de lectura ya existen: `SavingBucketRepository.find_with_owners`,
  `BucketEntryRepository.find_by_bucket`); resolver el destino de `saving_entries` (reconducir a
  `bucket_entries` del colchón, o deprecar tabla).
- **Decisiones a tomar:**
  - ¿`saving_entries`/`SavingEntryRepository` se reconducen o se deprecan? (Proyecto sin datos
    productivos → libertad.)
  - `_hydrate_savings` (`:185`): ¿desaparece al fundirse todo en `_hydrate_buckets`?
  - Bucket por defecto al rehidratar: ¿se recrea si no existe, o se asume creado en registro?
- **Hecho cuando:** depósito libre + bucket con objetivo se guardan, cierras y reabres el mes, y
  ambos saldos reaparecen íntegros. Test de rehidratación verde.

#### Mi hipótesis:

---

### T9. Reconciliar el ciclo mensual + actualizar docs

- **Objetivo:** `reset_for_new_month` deja de contradecir la persistencia, y los docs reflejan
  el modelo nuevo.
- **Por qué:** hoy el código resetea el `SavingTracker` (`household.py:256`) contra lo que dice
  `DECISIONS.md`; y `DECISIONS.md`/`deuda_rediseno_analisis.md` describen el modelo viejo.
- **Abarca:** ajustar `reset_for_new_month` (`household.py:251`) para que deuda y ahorro
  (household-scoped, multi-mes) no se reinstancien indebidamente; actualizar `DECISIONS.md`
  ("Ciclo mensual" + "Deuda"), pasar `deuda_rediseno_analisis.md` a "implementado", retirar del
  `TODO.md` el ítem del parche `allow_overpayment`; barrer el bug menor de
  `create_saving_bucket` que descarta `description.strip()` (`workflow_manager.py:490`).
- **Decisiones a tomar:**
  - En el mundo stateless cada operación recarga de BD → ¿`reset_for_new_month` sigue teniendo
    sentido, o es un vestigio del modelo en memoria?
  - ¿Qué exactamente sobrevive al nuevo mes ahora (deudas abiertas, buckets, colchón)?
- **Hecho cuando:** abrir un mes nuevo conserva deudas abiertas y saldos de ahorro; ningún doc
  describe el modelo viejo. Tests del ciclo verdes.

#### Mi hipótesis:

---

# FASE 5 — Hacia la automatización (diferido, sobre el cimiento sólido)

### T10. Carry-forward al abrir mes

- **Objetivo:** al abrir un período, las categorías e importes del mes anterior aparecen como
  borrador editable, en vez de arrancar de cero.
- **Por qué:** primer paso concreto de "cada mes creas menos cosas nuevas". `DECISIONS.md` ya lo
  promete ("carry-forward como punto de partida") pero el código no lo hace.
- **Abarca:** enganche en `start_new_month` (`workflow_manager.py:610`) /
  `PeriodService.start_new_month` (stub `period_service.py:174`), leyendo el período cerrado
  previo (`PeriodRepository.find_by_id` + `BudgetCategoryRepository.find_by_period`).
- **Decisiones a tomar:**
  - ¿Se copian importes tal cual, o solo la estructura de categorías?
  - ¿Borrador editable (dirección "PLANNING como borrador" de `DECISIONS.md`) o copia congelada?
- **Hecho cuando:** el segundo mes de un hogar arranca con las categorías/importes del primero
  como punto de partida.

#### Mi hipótesis:

---

### T11. Queries entre períodos + motor de sugerencias (esbozo futuro)

- **Objetivo:** leer el historial de meses cerrados para sugerir presupuestos ("de media pagas
  X en variables") — el sistema propone, tú confirmas.
- **Por qué:** es el destino de automatización. Mismo principio que la cuota-guía: guía, no
  imposición.
- **Abarca:** capa de lectura entre períodos (repos que crucen `household_periods` cerrados);
  servicio que derive sugerencias del historial; considerar el export JSON local (ya en tu
  `TODO.md`/memoria). **No se construye hasta tener T1-T9.**
- **Decisiones a tomar:**
  - ¿Qué estadístico sugiere el importe (media, mediana, últimos N meses)?
  - ¿La sugerencia vive en dominio o en presentación (como el loop del "sobrante honesto")?
  - ¿Lo cubre una query de BD o hace falta el almacén JSON?
- **Hecho cuando:** (esbozo) definido el enganche y el estadístico; implementación cuando el
  cimiento esté cerrado.

#### Mi hipótesis:

---

## Notas de secuencia

- **T1-T4 (deuda dominio + cableado en memoria) arrancan ya** — no dependen de persistencia.
- **T5-T6 (ahorro dominio)** pueden ir en paralelo o después; comparten el espejo `SavingBucket`.
- **T7-T9 (persistencia)** dependen de que el cimiento stateless (`PeriodService`, Fase 4 del
  `TODO.md`) esté maduro; deuda y ahorro comparten el trabajo de rehidratación.
- **T10-T11 (automatización)** van al final, encima del cimiento — nunca antes.
