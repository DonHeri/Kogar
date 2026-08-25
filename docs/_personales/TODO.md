# TODO — Kogar

**Propósito:** las próximas tareas de jornada, listas para arrancar en frío, sin necesitar el
contexto de ninguna conversación previa.

**La vista de todo lo pendiente está en `ROADMAP.md` → "Tablero".** Aquí solo lo de ahora, con el
detalle para ejecutarlo. La numeración es la misma en los dos archivos: la tarea 12 de aquí es la
12 de allí.

---

## Cómo se mantiene este archivo (para cualquier agente)

### Los seis campos de cada tarea

| Campo                  | Qué dice                                                             |
| ---------------------- | -------------------------------------------------------------------- |
| **Etiqueta**           | 🧠 APRENDER o ⚙️ DESPACHAR (ver abajo)                               |
| **Tiempo**             | estimación honesta de foco real, no de calendario                    |
| **Objetivo**           | qué se consigue. Solo en tareas de cola                              |
| **Por qué**            | qué se rompe o se bloquea si no se hace. Solo en tareas de cola      |
| **Abarca**             | el alcance. En 🧠 describe el **destino**; en ⚙️ puede dar el camino |
| **Decisiones a tomar** | lo que queda genuinamente abierto. **El agente NO las resuelve**     |
| **Hecho cuando**       | la condición de terminado, comprobable                               |

### Las etiquetas [06-08-26]

- 🧠 **APRENDER** — el agente da el destino y **ningún paso**. Aquí está el valor: son las tareas
  que te hacen mejor programador. Mentalízate a no tirar del agente.
- ⚙️ **DESPACHAR** — mecánico o repetido. Pide el camino entero, código incluido, sin culpa y sin
  que nadie te sermonee: aprenderlo despacio no te compra nada.

La propone el agente, la decide Heri. Explicada a fondo en `CLAUDE.md`.

### Las secciones

- **🟡 Ahora** — remates de menos de una jornada. No ocupan plaza de tarea.
- **🔴 Cola** — siempre **3 tareas**, en orden de roadmap. Ni menos, ni rellenos. Cada una cubre
  ≥ 4 h de foco. Al cerrar una se borra (git es el historial, no este archivo) y entra la
  siguiente, ya desarrollada con sus campos.
- **🟠 Entra en cola** — la siguiente tarea, ya desarrollada, esperando plaza. No cuenta para el 3.
- **🔵 En paralelo** — no bloquea ni la bloquean. Se hace cuando apetece. No cuenta para el 3.
- **⚪ Algún día lejano** — el cajón. Nada de aquí bloquea nada.

### El apartado "Mi hipótesis"

Debajo de cada tarea de cola hay un `#### Mi hipótesis` donde Heri escribe su plan de ataque
**antes** de abrir el chat. El agente siempre debe:

- Leerlo antes de responder nada sobre esa tarea.
- Si está vacío → preguntar cómo la abordaría. No continuar sin respuesta.
- Si tiene contenido → señalar aciertos, errores y vacíos, y discutirlos **antes** de proponer nada.
  No corregir sin explicar el porqué.
- No resolver las "Decisiones a tomar". Plantearlas como preguntas si la hipótesis no las cubre.
- Si detecta dependencia excesiva (hipótesis vacías repetidas, preguntas sin razonamiento previo),
  decirlo explícitamente.
- Si Heri no sabe cómo proceder → **no dar pasos**. Transferir conocimiento real: qué hay que
  construir y por qué existe, cómo encaja con el resto, qué trade-offs hay. El objetivo es que
  pase de no tener criterio a poder ejecutar solo, no que siga un guión.

---

# 🟡 Ahora — remates cortos

---

# 🔴 Cola — 3 tareas

> ⚠️ **`Transfer` ya NO se borra.** El plan archivado lo listaba como código muerto junto a las
> tareas 7 y 8. Desde el [06-08-26] es la pieza de la liquidación del settlement (tarea 15). Ver
> DECISIONS, "Liquidar el settlement es un movimiento propio".

> **Orden nuevo [06-08-26].** Todo lo que cambia el modelo va **antes** de la API, para no
> reescribir endpoints y schemas Pydantic dos veces. FastAPI no desaparece: baja a "En paralelo"
> porque su primer tramo no toca nada de esto.

---

# 0 · Refactor del presupuesto — el usuario declara sus categorías

**Va antes que todo lo demás.** Lleva el número 0 porque bloquea a la tarea 13 y porque ninguna
otra numeración cambia por meterla.

**Tiempo total:** ~23 h · 4 jornadas · **siete pasos, un commit por paso**

**Qué se persigue:** el presupuesto deja de ser una estrategia de porcentajes sobre un total y
pasa a ser una lista de categorías que el usuario crea. Cada categoría lleva su techo (en € o en
%), sus participantes y su método de reparto. La reserva deja de existir como categoría: se
convierte en el número que dice cuánto queda sin presupuestar, y ese número debe ser 0 para entrar
en MONTH.

**Por qué ahora:** el modelo actual obliga a que la estrategia sea un 50/30/20 sobre un total, con
tres categorías impuestas y una reserva que finge ser categoría para que las cuentas cuadren. Al
usar el CLI se vio que eso no es lo que una pareja real necesita. Y es la última zona del sistema
que sigue dando números que no significan lo que dicen.

**Esto remata dos decisiones que ya estaban escritas y a medias:** el cabo suelto de "Sobrante
honesto" en DECISIONS (_"¿es una categoría de verdad o es `missing_money` mostrado como guía?"_) y
la dirección de "solo la autocalculada predefinida".

La tercera, _"forzar decisión de destino de la reserva antes de `finish_month`"_, ya no se remata:
**se descarta** el [07-08-26]. El sobrante avisa y no bloquea.

## Las tres reglas cerradas [06-08-26]

Ninguna es un invento nuevo: las dos primeras son doctrina que ya estaba en `DECISIONS.md`, la
tercera sale sola del facturable. El porqué de cada una está en DECISIONS, "El presupuesto deja de
ser una estrategia sobre un total".

**1 · Un techo en % se recalcula en vivo durante PLANNING y se congela en `finish_planning`.**
No hace falta un campo que distinga "% fijo" de "% vivo": euros significa _sé el número exacto_, y
porcentaje significa _quiero esta fracción de lo que entre_. Elegir el modo ya declara la intención.

**2 · El sobrante avisa siempre y no bloquea nunca [07-08-26].**

| Sobrante   | Qué es                           | Qué hace el sistema |
| ---------- | -------------------------------- | ------------------- |
| **+200 €** | dinero sin decidir               | avisa               |
| **0 €**    | todo tiene destino               | nada que decir      |
| **−200 €** | presupuestas más de lo que entra | avisa               |

Dinero sin presupuestar puede existir en cualquier fase. Recomendar dónde asignarlo es trabajo de la
interfaz. El porqué está en DECISIONS, "El sobrante avisa siempre y no bloquea nunca".

**3 · Una subcategoría hereda los participantes de su padre, puede restringirlos, y nunca
ampliarlos.** Son siempre un subconjunto de los del padre. Ampliarlos metería dinero de un tercero
en una bolsa que no es suya y el techo del padre dejaría de significar nada.

## La simplificación que ahorra construir el doble

Bote común y sueldos separados **no son dos modos del sistema**. Un techo en % se calcula sobre el
ingreso de los participantes de esa categoría:

| Categoría   | Participantes | Techo | Sale                       |
| ----------- | ------------- | ----- | -------------------------- |
| Alquiler    | Amanda, Heri  | 20 %  | 20 % de 2538.35 = 507.67 € |
| Gym de Heri | Heri          | 3 %   | 3 % de 1124.50 = 33.74 €   |

Bote común es _"todas las categorías llevan a todos"_. Separado es _"cada uno tiene las suyas"_.
Mismo mecanismo, distintos participantes. La pregunta del arranque se queda en el flujo, pero como
**preset**: decide qué participantes trae por defecto una categoría nueva.

---

## P7 · ⚙️ DESPACHAR · Persistencia y CLI

**Tiempo:** ~6 h

**Abarca dos frentes, y solo uno está cerrado:**

**[COMPLETADO 12-08-26] Persistencia.** `budget_categories` gana `method` (NULL = hereda del
hogar) y una tabla `budget_category_participants` que copia `expense_participants` tal cual, con
`weight` incluido para los splits de CUSTOM. `BudgetCategoryRepository.save()` pide `member_ids`
igual que `ExpenseRepository.save()`; `household_loader._hydrate_budget` ya rehidrata las tres
cosas. De paso: `WorkflowManager.finish_planning()` llamaba a `budget_categories_repository.save()`
sin `member_ids` — código muerto, ningún test construía un `WorkflowManager` con ese repositorio
inyectado. Arreglado, con test de regresión.

**Bug encontrado y NO arreglado, pendiente de decisión:** `Household.add_category` resuelve
`method=None` a `self.method` **en el momento de crear la categoría**, en vez de dejarlo en `None`
para que siga heredando el método del hogar **en vivo**, que es lo que dice DECISIONS.md ("nunca
congelado en el momento de crear la categoría"). Hoy es inofensivo porque nada cambia
`Household.method` después de tener categorías creadas — pero el día que eso pase, las categorías
viejas se quedan con el método congelado en vez de seguir al hogar. Vive en `household.py`, fuera
del alcance de la persistencia.

**[PENDIENTE, parado a propósito el 12-08-26] CLI.** No existe ningún CLI en el repositorio
todavía — ni `src/cli.py` ni nada parecido, solo scripts de ejemplo como
`full_month_simulation.py`. Escribir "el flujo de PLANNING" implica construir una aplicación
interactiva desde cero, no tocar una que ya exista — eso cambia el tamaño real de la tarea, así que
se paró aquí en vez de asumirlo. Antes de retomar: decidir si sigue siendo DESPACHAR tal cual, o si
"construir un CLI entero" merece su propio mapa.

**Hecho cuando:** creas un presupuesto entero desde el CLI, cierras el programa, lo vuelves a
abrir, y todo está donde lo dejaste — participantes y métodos incluidos. Y
`full_month_simulation.py` corre de principio a fin.

---

## Verificación al terminar los siete

```bash
pytest tests/ -q --no-cov
```

```bash
python examples/full_month_simulation.py
```

- Una categoría con un solo participante solo se le pide a él.
- Dos categorías con métodos distintos reparten distinto.
- Un techo en % y otro en € conviven.
- El sobrante es visible y distinto de 0 cuando sobra dinero.
- No se puede entrar en MONTH con dinero sin presupuestar.
- Un período nuevo nace vacío; el siguiente hereda lo declarado.
- Nada del sistema menciona `reserva` como categoría.

#### Mi hipótesis:

---

### 12 · 🧠 APRENDER · Modelo rico de deuda y ahorro (dominio puro)

**Bloquea a las tareas 13 y 14.**

**Tiempo:** ~2 jornadas (10-12 h)

**Objetivo:** que se pueda declarar cualquier deuda real —con total, sin total, con plazo, sin
plazo, empezada hace meses— y que el ahorro complete su tercera esquina de cálculo.

**Por qué:** hoy `principal_cents` es obligatorio, así que un seguro de vida o un curso mensual
solo se declaran **inventándose un total**, y esa cifra falsa entra en `remaining_balance`,
`is_closed` y `remaining_installments`. En la prueba del CLI, un "Entierro" de 8 €/mes acabó
mostrando **1250 cuotas — 104 años**. Va primero porque `DebtBucket` es la base de la tarea 14:
construir `DebtService` sobre el modelo pobre significa reescribirlo entero después, más su
repositorio y su migración.

**Abarca** — cinco destinos, ninguno con pasos:

1. **El triángulo total · cuota · plazo.** Con dos cualesquiera sale la tercera. Único campo
   obligatorio: `installment_cents`. `principal_cents` y `term_months` pasan a opcionales.
   `term_months` deja de ser campo muerto: cobra sentido justo cuando hay plazo y no hay total.
2. **Las cuatro properties que se quedan sin suelo** al desaparecer el total: `remaining_balance`,
   `is_closed`, `remaining_installments`, `next_installment`. Sin total y sin plazo → saldo `None`,
   nunca cierra, cuota sin el `min(cuota, saldo)` final. `remaining_installments` **no cambia de
   fórmula**, solo de dónde saca el saldo.
3. **Saldo de apertura declarado.** `pagado = apertura + Σ entries`. Se declara al dar de alta y
   nunca se deduce de las fechas.
4. **Consultas que explican qué falta** en vez de lanzar. El patrón ya existe en
   `SavingBucket.required_monthly_contribution`.
5. **La esquina que falta en ahorro:** meta + capacidad mensual → plazo y fecha de fin.

Todo el porqué está en DECISIONS, sección "Deuda", entradas del [06-08-26].

**Decisiones a tomar:**

- Cómo viaja el motivo —_"me falta la fecha de fin, el total, o el nº de cuotas"_— desde el bucket
  hasta la pantalla: ¿property paralela, objeto resultado, método `can_compute_*`? Lo único cerrado
  es que sea **valor de retorno y no un `raise`**.
- Si el saldo de apertura es un campo del bucket o una entry especial con la fecha de alta.
- ⚠️ **Decide aquí** si `DebtEntry` gana el campo de imputación mes-cuota (ver "Algún día lejano").
  Es lo único que sale más caro si esperas.

**Hecho cuando:** se pueden declarar los cuatro casos —total+cuota, total+plazo, cuota+plazo, solo
cuota— y cada uno responde o explica qué le falta. Con tests para los cuatro.

#### Mi hipótesis:

---

### 13 · 🧠 + ⚙️ MIXTA · Carga completa + servicio de consultas (Fase 4, primera mitad)

> **Decidir qué compone el mapa general es APRENDER** — es diseño y es tuyo. **Cablear las recetas
> del loader es DESPACHAR**: pide el camino, ya has escrito ese patrón varias veces.

**Tiempo:** ~1,5 jornadas (8-10 h)

**⚠️ Va después de la tarea 0.** El resumen del mes cambia entero cuando muere la reserva como
categoría y el reparto pasa a ser por categoría. Escribir el mapa general antes significa
reescribirlo después.

**Objetivo:** que una request pueda reconstruir el hogar entero y responder una consulta sin
`WorkflowManager`.

**Por qué:** es lo único que bloquea de verdad los endpoints de lectura. Hoy ninguna receta del
loader carga todo, y `SummaryService` recibe un `Household` ya montado, así que nadie puede pedirle
un resumen dando solo un `period_id`.

**Abarca:**

1. Una receta que componga base + gastos + deuda + ahorro.
2. Métodos de consulta que reciban `period_id`, carguen y respondan — el patrón que `PeriodService`
   ya usa. Con eso quedan cubiertos `GET /periods/{id}`, el resumen del mes y el settlement.
3. **El mapa general del hogar.** Una sola implementación por número, varias formas de pedirla: el
   mapa _compone_ piezas que existen sueltas y los summaries pequeños llaman solo a la que
   necesitan. El limitador de fase es `validate_phase_accessible`, que ya existe; la excepción es
   deuda y ahorro, que cruzan meses por diseño. **No lleva el detalle personal por miembro**, por
   privacidad.
4. **Dos números cambian de significado.** El "pagado" por categoría mide **caja** y lleva pegada la
   parte ajena: `43.29 € (+13.50 € te debe Heri)`. Y la reserva se muestra como **espacio personal
   por miembro**, descontando su cuota de deuda y lo depositado en buckets. Las dos son vistas de
   la matriz `get_agreed_contributions()`, que ya existe: presentación, no modelo.

**Decisiones a tomar:** ¿el servicio de consultas es un `QueryService` nuevo o `SummaryService`
gana métodos que cargan? ¿Dónde vive el settlement, que hoy solo existe en `WorkflowManager`?

**Hecho cuando:** un resumen del mes completo sale a partir de `household_id` + `period_id`, con
tests de integración, y la reserva de cada miembro refleja su deuda y su ahorro.

#### Mi hipótesis:

---

---

# 🟠 Entra en cola en cuanto se cierre una

Dos esperando, en este orden.

---

### 14 · ⚙️ DESPACHAR · Deuda y ahorro stateless (Fase 4, segunda mitad)

> Es el quinto y el sexto servicio con el mismo patrón que ya escribiste cuatro veces. Pide el
> camino entero y despáchalo.

**Tiempo:** ~1 jornada (5-6 h)

**Objetivo:** que declarar deuda, pagarla, crear buckets y mover dinero funcione sin
`WorkflowManager`.

**Por qué:** es la mitad del producto que hoy solo existe en la fachada stateful. Sin esto no hay
endpoints de `/buckets` ni de deuda.

**Abarca:** `DebtService` (declarar bucket, cambiar cuota, registrar pago) y `SavingService` (crear
bucket, depositar, retirar). Los cinco repositorios ya existen.

**Depende de la tarea 12, y el orden importa:** los campos que persiste cambian (total y plazo
opcionales, saldo de apertura). Escribirlo antes significa rehacer servicio, repositorio y
migración.

**Decisiones a tomar:** ¿un servicio por dominio o uno solo de "compromisos"? ¿Qué receta de carga
necesita cada operación — pagar deuda no necesita el presupuesto, pero
`validate_debt_doesnt_exceed_capacity` sí? ¿Qué columnas de `debt_buckets` pasan a nullable?

**Hecho cuando:** un pago de deuda y un depósito en bucket persisten vía servicio, con tests.

#### Mi hipótesis:

---

### 15 · 🧠 APRENDER · Settlement honesto: reparto extraíble, liquidación y reserva personal

**Tiempo:** ~2 jornadas (10-12 h), y **menos si la tarea 0 va primero**: su paso P2 necesita el
reparto fuera del bucle igual que esta tarea, así que ese trozo llegará ya hecho.

**Objetivo:** que el settlement se pueda **saldar**, y que el reparto por participante sea
reutilizable fuera de su propio bucle.

**Por qué:** al medir el presupuesto en caja, el de quien adelanta dinero queda comido hasta que le
paguen. Y hoy **no hay forma de registrar que te han pagado**: el settlement se recalcula siempre
desde cero desde los gastos, y `Transfer` es un dataclass con un `# TODO` y nada más.

**Abarca:**

1. **Sacar el reparto de dentro del bucle.** La lógica que decide cuánto de un gasto corresponde a
   cada participante vive incrustada en `SettlementCalculator.calculate` y nadie más puede
   llamarla. Mientras siga ahí, cualquier vista que necesite el reparto lo duplicará, y dos copias
   del mismo cálculo acaban dando números distintos. **Esto desbloquea todo lo demás.**
2. **Liquidar contra una persona.** El usuario elige con quién salda y se le ofrece el mapa del
   settlement con lo que debe a cada uno. Con más de dos miembros es imprescindible: si debe 40 € a
   B y 30 € a C, "liquidar 70 €" no significa nada.
3. **Las tres granularidades solo cambian el importe sugerido** (total, categoría, gasto). Lo que se
   guarda es siempre lo mismo: de X a Y, importe, fecha. El importe se reparte entre los gastos
   compartidos con esa persona, que es lo que devuelve el dinero a las categorías correctas.
4. **Vive fuera del reset mensual**, igual que deuda y ahorro. Disponible en MONTH y CLOSING.

**Decisiones a tomar:** si la liquidación es una entidad nueva con su tabla o una entry dentro de
algo existente. Y cómo avisar de que liquidar por partes descompensa temporalmente el neto — Heri
debe 193.82 € en neto pero 250 € solo por el alquiler; si paga el alquiler entero, Amanda pasa a
deberle 56.18 €.

**Hecho cuando:** se puede registrar que un miembro ha pagado a otro, el settlement lo refleja, y
el presupuesto por categoría del que adelantó recupera su dinero.

#### Mi hipótesis:

---

# 🔵 En paralelo — aprender FastAPI sin bloquear nada

> Bajada de la cola el [06-08-26] **sin recortarla**. El motivo no es prioridad: su primer tramo
> —esqueleto, estructura, handler de errores, alta de hogar y de período— **no toca deuda, ni
> settlement, ni reserva, ni el resumen del mes**. Nada de lo decidido la obliga a reescribirse.
> Los endpoints de deuda y de resumen sí esperan a las tareas 12 y 13.

---

### 16 · 🧠 APRENDER · FastAPI: esqueleto + primeros endpoints (Fase 5)

> Lleva APRENDER **por decisión tuya, no por su valor de dominio**: es lo nuevo que querías tocar
> para no estancarte. El cableado repetitivo de los endpoints siguientes ya será DESPACHAR.

**Tiempo:** ~1 jornada (5-6 h)

**Objetivo:** exponer los servicios como API HTTP consumible.

**Por qué:** objetivo del roadmap — hacer el sistema accesible desde cualquier cliente.

**Abarca:** setup FastAPI + Pydantic, estructura `routers/` + `schemas/`, handler de errores dominio
→ HTTP, y los endpoints `POST /households` y `POST /households/{id}/periods`.

**Media base ya hecha:** `src/models/exceptions.py` tiene `DomainError` como raíz, así que un
`except DomainError` en el handler cubre todos los casos de golpe, y cada excepción concreta lleva
sus datos para componer el mensaje. Hoy solo hereda `CeilingBelowChildrenError`; el resto del
dominio sigue lanzando `ValueError` pelado.

**Decisiones a tomar:** estructura de carpetas del módulo API; cómo se inyectan los servicios; qué
excepciones merecen tipo propio antes de mapearlas.

**No hace falta antes:** el `id` de categorías en BD, la autorización entre miembros, el rediseño de
`reserva` ni el catálogo. Nada de eso bloquea una API que funcione.

**Hecho cuando:** abrir un período funciona desde Postman con respuesta JSON correcta.

#### Mi hipótesis:

---

# ⚪ Algún día lejano

Nada de aquí bloquea la API ni produce números incorrectos hoy.

## ⚠️ Con fecha de caducidad

### Campo de imputación mes-cuota en `DebtEntry`

**Decídelo dentro de la tarea 12.** `DebtEntry` guarda quién, cuánto y cuándo, pero **no a qué
mes-cuota imputa** el pago. Es un campo opcional de un minuto ahora. Añadido en v2, todos los pagos
anteriores quedan sin poder reconstruir a qué mes correspondían, y el dato no se puede deducir
después. Es la única pieza del calendario de cuotas que no admite esperar.

### Bomba de relojería: gastos huérfanos al borrar una categoría

`Household.remove_category` sube los gastos de una hija a su padre **en memoria**, pero
`PeriodService.remove_category` (`period_service.py:173`) solo borra la fila de `budget_categories`
— **nadie actualiza `expenses.category`**.

Hoy es inofensivo porque borrar exige PLANNING y registrar gasto exige MONTH, así que dentro de un
período no coinciden. **En cuanto borrar salga de PLANNING**, un gasto apunta a una categoría que ya
no existe y `_hydrate_expenses` deja de poder cargar el período entero.

Hace falta un `UPDATE` de `expenses.category` por período y nombre antiguo en `ExpenseRepository`,
llamado **antes** del delete.

## Diseñado, esperando turno

### Calendario de cuotas por mes (v2 de la deuda)

Cada cuota completa pagada marca un período como pagado. Un período pertenece al mes en el que
**más tiempo esté**: del 25 de febrero al 25 de marzo son 24 días en marzo contra 4 en febrero,
luego es marzo. Más un método que valore cuánto tiempo ha pasado desde el último pago, con un botón
que **pregunta** —"han pasado X meses, ¿pagaste esas cuotas?, ¿a qué mes corresponde esta?"— en vez
de deducirlo. Cambia el modelo de "saldo continuo" a "casillas de calendario": más potente y
bastante más caro. Nace de la sesión del [06-08-26].

### Retirar de un bucket compartido más de lo aportado: avisar, no bloquear

Hoy `SavingBucket.withdraw` lanza `ValueError("Saldo insuficiente")` comparando contra lo que puso
ese miembro. Es un uso real —parejas que sacan del bote común— y **Kogar no debe impedir, solo
notificar**, igual que ya hace con `missing_money` negativo y con el sobrepago de deuda.

El matiz: el tope del bucket **personal** se queda (no puedes sacar dinero que no está); el que cae
es el de la aportación individual en buckets compartidos (el dinero está, pero parte es de otro).
La diferencia genera deuda entre miembros.

**Lo que hay que decidir antes de escribir nada:** si esa deuda entra en el settlement del mes o
vive aparte, porque nace de un movimiento que cruza meses y el settlement se calcula sobre los
gastos del período. Ver DECISIONS, "Buckets SHARED: retirar más de lo aportado avisa, no bloquea".

### Flujo del CLI para presupuestar de abajo arriba

Las subcategorías no son organización, son el método para averiguar cuánto asignar: nadie sabe
cuánto va a "fijos", pero todo el mundo sabe lo que paga de alquiler. El techo deja de ser un número
inventado y pasa a ser lo que ya sabes más el margen que quieras.

La conversación va al revés que la escritura, y eso lo resuelve el CLI — el dominio no cambia. Si le
pones importe a una hija antes de que su raíz tenga techo, lanza, porque el techo vale 0:

1. Preguntar los gastos concretos (alquiler, agua, luz) **sin llamar al dominio**: son números en
   memoria.
2. Sumarlos y devolvérselo: "has declarado 930 € en fijos, ¿cuánto le asignas?", con ese total como
   mínimo y como valor por defecto.
3. `set_budget_for_category("fijos", techo)`.
4. Ya con techo, `add_category` + importe de cada hija.

Dos cosas que el dominio valida pero no anticipa, y que el CLI tiene que llevar de la mano:

- **Cuánto ingreso queda.** El techo no puede pasar de `ingresos − otras raíces`. Ir diciendo "te
  quedan X" en cada paso, en vez de dejar que choque.
- **El colchón.** Si acepta el mínimo exacto, `sin desglosar` queda en 0 y cualquier gasto fijo
  imprevisto se sale del techo. Sugerir margen, o al menos nombrar qué significa ese 0.

Al bajar un techo por debajo de lo repartido, `CeilingBelowChildrenError` ya trae el mínimo en
`children_total_cents` — el CLI no tiene que recalcularlo.

### Categorías del hogar, no del mes

`budget_categories` cuelga de `household_period_id` y `add_category` exige PLANNING, así que no
puedes crear categorías hasta haber cerrado los ingresos. Es también lo que impide darles `id` y
guardar las contribuciones desglosadas con FK.

### 🧠 APRENDER · `SubcategoryLibrary` se convierte en plantilla, conectada a `CategoryLibrary`

**Estado [12-08-26]:** propuesta, sin sección ni número todavía. Decide Heri dónde entra.

**Solo la importa `src/models/__init__.py:16`.** Ningún otro archivo la toca: ni `CategoryLibrary`,
ni `Budget`, ni `WorkflowManager`. Vive aislada desde que se escribió.

**Por qué ahora es el momento.** Antes no había dónde enchufarla: el árbol de categorías no
existía. Con la tarea 0 cerrada, `Budget.add_category(parent=...)` ya soporta 2 niveles
(`budget.py:28-85`), así que ahora sí hay una hija real que poblar con sugerencias.

**Destino:** un usuario que crea la categoría raíz "fijos" puede pedir subcategorías sugeridas
("alquiler", "luz", "agua"...) en vez de inventárselas de cero. Si crea una raíz custom que no está
en ninguna librería (p. ej. "criptomonedas"), pedir sugerencias no lanza: simplemente no hay
ninguna. Aceptar una sugerencia como hija sigue pasando por todas las validaciones que ya existen en
`add_category` — la plantilla propone nombres, nunca se salta una regla de dominio.

**Lo que hay que resolver, porque hoy no cuadra:** las claves de `SubcategoryLibrary.SUGGESTIONS`
incluyen `"deuda"` y `"ahorro"`, que **no existen** en `CategoryLibrary` (ni en `STANDARD_CATEGORIES`
ni en `EXTENDED_CATEGORIES`). El resto de claves sí coinciden hoy (`fijos`, `variables`, `salud`,
`transporte`, `ocio`, `educacion`, `mascotas`, `regalos`, `viajes`, `tecnologia`) — la nota vieja de
que "no coinciden" ya no es cierta en general, pero esas dos sí quedan huérfanas.

**Decisiones a tomar:**

- ¿El puente vive dentro de `CategoryLibrary` (que ya es "la librería de categorías") o es un objeto
  nuevo, tipo plantilla, que conoce a las dos librerías desde fuera?
- `"deuda"` y `"ahorro"` — ¿se dan de alta en `CategoryLibrary` para que el catálogo quede completo,
  o se quedan fuera a propósito porque no son categorías de presupuesto?
- Una sugerencia que el usuario ya creó como hija, ¿se sigue ofreciendo o se filtra de la lista?

**Hecho cuando:** pedir sugerencias de subcategoría para una raíz estándar devuelve la lista
esperada; pedirlas para una raíz custom no lanza; y `"deuda"`/`"ahorro"` tienen un destino decidido
en vez de quedar huérfanas por descuido.

#### Mi hipótesis:

### Pago globo (cuota final grande)

Típico en financiaciones de coche o moto con valor futuro garantizado: el total supera
`cuota × plazo` y la última cuota es mucho mayor, no menor. El modelo del triángulo asume lo
contrario (última cuota corta o igual) y trataría el exceso como plazo adicional.

### Método de reparto por categoría y por gasto

Campo `distribution` en `Category`; aditivo. Ver DECISIONS, "Reparto por categoría — DIFERIDO". **La
interfaz ya está decidida [06-08-26]:** un radio button por método en cada gasto compartido, con el
del hogar premarcado.

Ojo, _custom no es un método, es un método más unos porcentajes_ — marcar el radio no basta, hay que
decir 70/30. Ahí entra `expense_participants.weight`, que existe en el esquema como nullable y
**queda siempre NULL** porque `Expense.participants` es `list[str]` sin peso. Poblarlo exige antes
diseñar cómo declara el usuario ese reparto. Las dos cosas son la misma tarea.

### Estrategia de borrado de household y period

`del_household`/`del_member` hacen DELETE físico sin `ON DELETE CASCADE`, y solo se han probado
contra filas vacías — con members, periods y expenses colgando fallarían por FK. `households` y
`members` ya tienen `status BOOLEAN` (soft-delete arrancado y no usado en ningún flujo). Decidir:
CASCADE solo para borrado administrativo real, archivado/export antes de purgar, o aceptar
crecimiento indefinido con soft-delete puro. Nace de la sesión de persistencia de buckets
[03-07-26].

### Reorganizar `src/workflow/`

Hoy mezcla la fachada (`workflow_manager.py`) con 6 servicios, `household_loader.py` y
`settlement_calculator.py` en una carpeta plana. Separar en `workflow/` (solo la fachada) +
`services/` (servicios, loader y calculadora) — son roles que DECISIONS ya distingue por nombre,
solo falta que la carpeta lo refleje. Después de cerrar las tareas 13 y 14, no a mitad.

### Autorización entre miembros del mismo hogar

Nada valida que el `household_id`/`period_id` que llega a un servicio pertenezca a quien hace la
petición. En cuanto haya login, cualquier miembro autenticado podría leer o escribir datos de otro
hogar cambiando el id en la llamada. Diseñar dónde vive el check (¿servicio, middleware?) cuando
llegue el login. No antes: no hay usuarios que aislar todavía.

## Cajón — una línea cada uno

- Deuda compartida entre varios miembros, con cuota mensual y por miembros.
- Permitir cambiar el nombre de un `SavingBucket`.
- `SavingBucket.owners` → `participants`, por coherencia: gastos y categorías ya usan esa palabra
  para lo mismo. Tres nombres para un concepto obligan a traducir mentalmente en cada salto de capa.
- Estandarizar el estilo de docstrings (Args/Returns/Raises) en `workflow/` y `models/`, no solo en
  `HouseholdService`.
- Refactorizar validaciones en un módulo centralizado.
- `BudgetCategory` → `planned_amount` a `_planned_amount` + `@property`.
- Buscador de similitudes en `CategoryLibrary` (typos: "fijoss" → "fijos").
- "Sobrante honesto": separar el tapón estructural de la semántica de ahorro. Depende de la
  jerarquía de categorías — ver DECISIONS, "Visión futura de categorías".
- Bug latente del invariante `AutoCalculatedCategory`, heredado de la tarea de jerarquía. Verificar
  si sigue vivo: no se tocó al implementar el árbol.
- `InternalTransfer` cuando sea necesario. **No confundir con la liquidación de la tarea 15:** esa
  paga a otro miembro, esta mueve dinero propio entre destinos.
- Sobrepago de deuda: `register_debt_payment(allow_overpay=True)` salta el tope del compromiso para
  pagos vía income extra. Es un parche; la tarea 12 debe resolverlo validando contra el saldo
  pendiente, no contra el compromiso.
- Export JSON local de métricas por período para análisis. Validar antes si la BD ya lo cubre.
- Validar que los participantes de un `Expense` sean subconjunto de los participantes de su
  categoría. Hoy `Household.register_expense` (`household.py:234-244`) solo comprueba que cada
  participante sea miembro del hogar, no que esté en `category.participants` — se puede registrar
  un gasto con alguien ajeno a la categoría sin que nada avise. El comportamiento pedido: `Expense`
  lanza `ValueError`, y la fachada lo atrapa y le pregunta al usuario si quiere añadir a esa persona
  a la categoría en vez de rechazar el gasto sin más.
