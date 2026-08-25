# Categorías sin bugs — alcance mínimo

Objetivo: dejar la jerarquía de categorías sin errores de cálculo y pasar a FastAPI. No es el
refactor grande de categorías; ese se hace cuando la app esté en uso y los problemas se sientan
de verdad. Lo aparcado está al final, en una línea cada cosa, para no perder el razonamiento.

`reserva`, ahorro y deuda **no se tocan**. Siguen exactamente como están.

Un paso por sesión, un commit por paso. Seis pasos.

---

## Decisiones

1. **El resto sin desglosar de un padre es un cálculo, no un dato.** `fijos` vale 1590, sus
   hijas suman 940, el resto son 650 = `techo − Σ hijas`. No hay fila para eso: guardar un
   número que se deduce de otros dos es pedir que se descuadren.

2. **La contribución se calcula sobre el importe facturable**, no sobre `planned_amount`:

   ```
   billable(cat) = planned_amount(cat) − Σ planned_amount(hijas directas)
   billable(hoja) = planned_amount(cat)
   ```

   fijos 650 + alquiler 800 + luz 90 + internet 50 + variables 600 + reserva 810 = 3000, que es
   justo la suma de las raíces. Una fórmula para padres y para hijas, sin casos especiales, y
   es la misma resta de la decisión 1 aplicada a todos los niveles. Para mostrar el total de
   `fijos` (1590) se agrega el subárbol hacia arriba; al revés no se podría.

3. **El gasto sí puede superar el techo.** No se limita, se reporta. El `remaining` de un padre
   puede salir negativo y eso es correcto.

4. **Techo estricto en los dos sentidos.** Ni Σ hijas puede pasar del techo, ni el techo puede
   bajar por debajo de Σ hijas. No crece solo: mientras `reserva` siga absorbiendo el
   remanente, crecer solo significaría bajarle la reserva al usuario sin decírselo.

5. **Las hijas no tienen clase propia.** `parent` sigue siendo un campo. Raíz/hija es un rol
   que cambia, y `Expense` guarda el objeto `Category` entero: cambiar de clase dejaría gastos
   apuntando a un objeto zombi.

6. **Una hija hereda el `is_shared` de su padre.** Hoy `add_category` fabrica toda categoría
   custom con `is_shared=True` (`budget.py:28`), así que una hija de `variables` sale
   compartida y sus gastos se reparten entre todos. Eso ya es un bug.

7. **Profundidad máxima 2, validada.** Toda la lógica lo asume; permitir nietos sin recursión
   es abrir errores silenciosos.

---

## El bug, con números

3000€ de ingresos. fijos 1590 (alquiler 800 + luz 90 + internet 50), variables 600, reserva 810.

| | |
|---|---|
| `get_total_budgeted()` | 3000 ✓ — filtra por `parent is None` |
| Σ `get_total_contributions_by_member()` | **3940** ✗ — recorre el dict plano |

Los 940 fantasma se congelan en `freeze_planning_state` (`household.py:150`), se persisten vía
`finish_planning` (`workflow_manager.py:356` y `period_service.py:300`) y de ahí salen
`get_member_owed_total`, `get_member_balance` y el settlement.

---

## Pasos

### 1. El test que falla

`tests/test_household.py`, con la fixture `household_with_members_and_child_categories`
(`:115`). Aserta que la suma de `get_total_contributions_by_member()` es igual a
`get_total_incomes()`. Debe fallar 3940 vs 3000.

### 2. `Budget` se hace dueño del árbol

`src/models/budget.py`. Índice `padre → [hijas]` mantenido en `add_category`,
`delete_budget_category` y `set_standard_categories`, más la API que hoy no existe: hijas de un
nombre, si es hoja, y el **facturable** de la decisión 2.

Ojo con una trampa: el facturable **no** puede reutilizar `get_child_total_planned`. Ese método
resuelve primero el padre, así que si le pasas una hija te contesta por sus hermanas —
`get_child_total_planned("alquiler")` devuelve 940, no 0, y el facturable saldría 800 − 940 =
−140. Son dos preguntas distintas: el techo pregunta "cuánto suman las hijas de mi grupo", el
facturable pregunta "cuánto suman mis hijas". El facturable necesita su propia suma sobre
`self._children.get(nombre, [])`, que además resuelve el caso hoja sola: sin hijas suma 0 y el
facturable es su propio importe.

Escribe primero la llamada donde se necesita (`household.py:368`) y luego implementa lo que
hayas escrito. Diseñar desde dentro es lo que bloquea.

Aquí caen cuatro bugs baratos:

- [IMPLEMENTADO]`delete_budget_category` (`:45-49`) deja hijas apuntando a un padre que ya no existe.
- [IMPLEMENTADO]`set_standard_categories` (`:15-19`) escribe directo en el dict sin pasar por `add_category`:
  llamarlo dos veces resetea los techos a 0 dejando las hijas vivas.
- [IMPLEMENTADO]`add_category` no valida profundidad (decisión 7).
- [IMPLEMENTADO]`add_category` (`:28`) ignora el `is_shared` del padre (decisión 6).

**Trampa:** `household_loader.py:77-80` ordena las filas para insertar padres antes que hijas,
porque `add_category` exige que el padre exista. Si construyes el índice en `add_category`, esa
dependencia sigue viva.

**Reglas de borrado** (decididas; las dos preguntas son independientes):

*¿Tiene hijas?* → **lanza**. No las promuevas a raíz: `alquiler` 800, `luz` 90 e `internet` 50
viven dentro de un techo de 1590 sin contar contra el ingreso; promoverlas mete 940 nuevos
contra el ingreso y recalcula reserva sola. Le has cambiado el presupuesto al usuario sin que
lo pida. Que borre o mueva las hijas primero.

*¿Tiene gastos?* → ya está decidido en `DECISIONS.md:284-289`: la operación pide destino de
reasignación, y sin destino los gastos van a reserva, que no se puede borrar. Refinamiento para
las hijas: su destino natural es el padre, y además es neutro — el gasto ya contaba contra el
techo del padre por rollup, así que reasignarlo no mueve ningún total.

`Budget` no conoce los gastos, así que la comprobación vive en `Household.remove_category`, que
tiene `budget` y `expense_tracker` a mano. `delete_budget_category` se queda tonto.

Y lo que rompe hoy: borrar una hija la saca de `self.categories` pero deja su nombre en la
lista de `_children` del padre → el siguiente `get_child_total_planned` peta con `KeyError`.

### 3. La contribución deja de duplicar [IMPLEMENTADO]

`Household.preview_budget_contribution_summary` reparte sobre el facturable en vez de sobre
`category.planned_amount`. El test del paso 1 se pone verde.

Requiere que `get_billable` del paso 2 esté hecho. `category.planned_amount` aparece cuatro
veces dentro del bucle: las tres llamadas a `FinanceCalculator` (una por método de reparto) y
el campo `"planned"` del dict que se devuelve. Calcula el facturable una sola vez antes del
`if` y usa esa variable en las cuatro.

La forma del dict no cambia —cada categoría conserva su clave y sus `contributions`—, así que
toda la cadena de abajo se arregla sola: `get_total_contributions_by_member` (`:399`),
`get_member_owed_total` (`:444`), `freeze_planning_state` (`:150`) y `summary_service`.
Confírmalo leyéndolos, no lo des por hecho.

El `planned` de cada fila pasa a ser el facturable (650 para fijos), no el techo. Así la fila
cuadra consigo misma y sumar esa columna vuelve a dar 3000.

**Trampa:** hay dos rutas paralelas, la stateful y la stateless. Arreglar una y olvidar la otra
es el error fácil.

### 4. El techo se defiende por abajo

`budget_distribution_service._set_root_budget` (`:27-51`) rechaza dejar la raíz por debajo del
planificado de sus hijas, diciendo cuál es el mínimo. Simétrico al `raise` que ya hace
`_set_child_budget` (`:66-69`).

La validación va en `Budget`, no en el servicio: `household_loader` llama a `set_planned_amount`
directo y se saltaría el servicio. Eso te obliga a resolver el estado intermedio de la
rehidratación (hijas cargadas, padre todavía a 0) — carga los importes de raíz antes que los de
hija, igual que ya haces con la estructura.

### 5. El gasto de una hija cuenta contra su padre

`get_category_spent` (`household.py:469`) pasa a incluir el subárbol; el gasto propio se queda
en un método aparte con otro nombre. Sin esto, `by_category["fijos"]` sale con `spent: 0`
mientras `totals.total_spent` sí cuenta los 800 del alquiler.

`ExpenseTracker` se queda agnóstico de la jerarquía: le añades un método que sume varias
categorías a la vez y es `Household` quien le pasa los nombres del subárbol.

`get_category_remaining` de un padre pasa a ser techo − gasto profundo, y puede salir negativo
(decisión 3). No lo claves a 0.

Con eso, `summary_service.py:184-191` cuadra: Σ de `by_category` == `total_budgeted`.

### 6. La simulación

`examples/full_month_simulation.py`, bloques `:117-132`, `:138-144` y `:351-359`. Necesitas una
consulta que devuelva raíces con sus hijas y el resto calculado — la mínima que sirva para
imprimir, sin tocar la firma de `get_active_categories`, que usan cuatro sitios.

Hijas tabuladas bajo su padre y el resto como última línea del grupo. `printer.py` no sabe de
jerarquía; la indentación va en el ejemplo.

---

## Verificación

```bash
pytest tests/ -q --no-cov
```

```bash
python examples/full_month_simulation.py
```

- Σ `get_total_contributions_by_member()` == `get_total_incomes()` con hijas presentes.
- Σ de los facturables de todas las categorías == `get_total_budgeted()`.
- La contribución de `fijos` se calcula sobre 650, no sobre 1590.
- Σ de `by_category["budget"]` == `totals.total_budgeted`.
- Un gasto en `alquiler` mueve el `spent` de `fijos`.
- Gastar 1700 en el subárbol de `fijos` (techo 1590) deja `remaining` en −110, sin lanzar.
- Bajar `fijos` por debajo de Σ hijas lanza; subir una hija por encima del techo lanza.
- Crear una hija de una hija lanza.
- Una hija de `variables` sale personal, no compartida.
- Borrar `fijos` no deja a `alquiler` apuntando al vacío.
- Las hijas salen tabuladas bajo su padre, con su resto visible.

---

## Aparcado para el refactor grande

No son bugs: ninguno produce un número incorrecto. Se rediseñan cuando la app esté en uso.

- **Categorías del hogar, no del mes** — hoy `budget_categories` cuelga de
  `household_period_id` y `add_category` exige PLANNING, así que no puedes crear categorías
  hasta haber cerrado los ingresos. También es lo que impide darles `id` y guardar las
  contribuciones desglosadas con FK (`DECISIONS.md:595`).

  **Cabo suelto que se activa con esto:** `Household.remove_category` sube los gastos de una
  hija a su padre en memoria, pero `PeriodService.remove_category` (`:184-199`) solo borra la
  fila de `budget_categories` — nadie actualiza `expenses.category`. Hoy es inofensivo porque
  borrar exige PLANNING y registrar gasto exige MONTH, y dentro de un período no coinciden.
  En cuanto borrar salga de PLANNING, un gasto puede quedar apuntando a una categoría que ya
  no existe y `_hydrate_expenses` deja de poder cargar el período. Hace falta un `UPDATE` de
  `expenses.category` por período y nombre antiguo en `ExpenseRepository`, llamado antes del
  delete.

- **Presupuesto personal por miembro** — `is_shared` solo decide hoy los participantes de un
  gasto (`expense_service.py:51`); en el presupuesto no pinta nada, así que `variables` es una
  bolsa del hogar. Un miembro con mucha deuda no puede bajarse su parte sin tocar la del otro.

- **Techo bottom-up** — declarar alquiler y agua y que `fijos` suba solo. Depende de que
  `reserva` deje de absorber.

- **Catálogo único, folio en blanco y packs** — `subcategory_library.py` está importada y no la
  usa nadie, y sus claves no coinciden con las de `CategoryLibrary`. Ojo al diseñarlo: el
  sistema exige hoy exactamente una `AutoCalculatedCategory`, resuelta por `isinstance` en
  `budget.py:85-90`, que lanza si no hay ninguna.

- **`reserva` con responsabilidades prestadas** — ver el anexo al final.

---

# Anexo: rediseño de `reserva`

Reserva es el **bote de dinero libre**, no ahorro: `DECISIONS.md:484` ("el extra se queda en
el bote común o el usuario lo mueve luego"), `:486` ("la verdad del dinero libre es el
`planned_amount` de reserva"), `:48-50` (el ahorro es informativo, solo la deuda se valida
contra ella). De ahí puede salir una cuota de deuda, una meta de ahorro o una categoría nueva.

**Su única responsabilidad:** ser la tercera pata del presupuesto que absorbe lo no asignado, y
la fuente desde la que el dinero se mueve a otros sitios.

## Diagnóstico: no es un almacén, es una resta que finge serlo

Nada la llena a propósito y nada la vacía.

| Responsabilidad prestada | Dónde | Por qué no le toca |
|---|---|---|
| Techo de capacidad de deuda | `household.py:136-148`, llamado en `workflow_manager.py:345` y `period_service.py:298` | Subir `fijos` baja la reserva y la deuda deja de caber, con el mismo ingreso y la misma cuota. La capacidad depende de lo que ganas, no de un residuo móvil |
| Entra en `owed` y en `balance` | `household.py:444-453` | Es dinero personal (`is_shared=False`) que no se paga a nadie; contarlo como deuda del mes distorsiona el settlement |
| Es `missing_money` | `summary_service.py:44` y `:169` | "Sin asignar" y "reserva" son el mismo número por construcción → imposible distinguir lo guardado a propósito de lo olvidado |
| Absorbe los ingresos extra | `incomes_entries_service.py:12` | La vista viva reparte entre todos el extra que puso uno solo (`DECISIONS.md:487`) |
| Es una categoría de gasto más | `register_expense` no la excluye; `remove_category` no la protege | Borrarla deja `get_auto_calculated_category()` lanzando en cada asignación. **Esto es un bug** |
| No se vacía nunca | `register_debt_payment` y `deposit_to_saving_bucket` no la tocan | Pagas 300 de deuda desde "tu reserva" y reserva vale lo mismo. El dinero se mueve en los trackers y no en el presupuesto |

## Lo que sí funciona hoy: mover dinero entre raíces

`set_budget_for_category` **ya es la transferencia**, con reserva de contraparte. Bajar
`variables` de 900 a 600 hace que `_set_root_budget` recalcule y reserva suba a 900; subir
`fijos` la devuelve a 600. Neto: 300 movidos, en dos llamadas normales. `InternalTransfer` no
hace falta para esto.

Donde no funciona es desde dentro de un techo: `_set_child_budget` no toca reserva, así que
bajar una hija libera espacio solo dentro de su padre (burbuja sellada).

## Estrategia

La idea central es separar dos cosas que hoy son el mismo número:

- **el residuo** — `ingresos − Σ raíces`, un cálculo. Es "lo que no has asignado".
- **la reserva de verdad** — una raíz normal cuyo importe decide el usuario, de la que se
  descuenta cuando el dinero sale.

Pasos, de más barato a más caro:

1. **Proteger reserva** de `remove_category` y de recibir gastos. Es el bug de la tabla y son
   dos validaciones.
2. **Sacar la capacidad de deuda de reserva.** `validate_debt_doesnt_exceed_capacity` pasa a
   comparar la cuota contra el ingreso disponible del miembro (ingreso − su parte de las
   categorías compartidas). Deja de moverse cada vez que se toca una categoría.
3. **Reserva deja de autocalcularse.** Quitar el `raise` de `budget_distribution_service.py:13`
   y el recálculo de `_set_root_budget` (`:47-51`); pasa a validar solo `Σ raíces ≤ ingresos`.
   A partir de aquí el usuario le pone importe como a cualquier raíz.
4. **El residuo se vuelve `missing_money` de verdad**, y `finish_planning` exige que sea 0.
   Aquí es donde el descuadre deja de ser invisible.
5. **Las salidas descuentan.** Pagar deuda, depositar en un bucket o crear una categoría nueva
   restan de reserva. Esta es la operación que pensaste en su día — pero solo hace falta para
   las salidas: las entradas ya las cubre `set_budget_for_category`.
6. **Reserva sale de las contribuciones**, o al menos de `owed`. Requiere que
   `get_reserve_contribution_by_member` calcule la parte del miembro aplicando los porcentajes
   del método al importe de reserva, en vez de leerla del dict de contribuciones.
7. **El ingreso extra deja de caer en reserva automáticamente**: sube el residuo de quien lo
   metió, y él decide. Cierra el bug documentado en `DECISIONS.md:487`.

Los pasos 1 y 2 son independientes del resto y se pueden hacer sueltos. Del 3 en adelante van
en cadena: cada uno deja el sistema en un estado que el siguiente necesita.
