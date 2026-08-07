# WorkflowManager — Referencia de API

El usuario interactúa **únicamente** con `WorkflowManager`. Las clases internas (`Household`, `SavingBucketTracker`, `DebtBucketTracker`, etc.) son detalles de implementación. Los servicios de `src/workflow/` (`BudgetDistributionService`, `SettlementCalculator`, `SummaryService`, `IncomeEntryService`) tampoco se usan directamente — `WorkflowManager` delega en ellos.

---

## Invariantes y convenciones

### Unidades monetarias

| Sentido | Unidad |
| --- | --- |
| Entradas (parámetros `amount_*`, `goal_*`) | Euros `€` |
| Salidas (`→ int`) | Céntimos `¢` — 1€ = 100¢ |

Todos los métodos que reciben dinero esperan **euros** como `float`. Todos los métodos que devuelven dinero retornan **céntimos** como `int`.

```python
wm.set_budget_for_category("fijos", 1500.0)  # entrada: 1500€
wm.get_category_budget("fijos")              # salida:  150000¢
```

### Porcentajes (basis points)

Los porcentajes de reparto se expresan en **basis points** donde `10000 = 100%`.

```python
5000  # 50%
3333  # 33.33%
```

### Reserva autocalculada

`reserva` no se puede asignar directamente. Siempre es el complemento del total de ingresos:

```
reserva = total_ingresos - sum(resto_de_categorías)
```

Intentar asignar presupuesto a `"reserva"` directamente lanza `ValueError`.

### El techo de una categoría raíz

Una raíz con hijas es un **techo**, no la suma de sus hijas. Las hijas reparten dentro de ese
importe y no se suman aparte al total del hogar.

De ahí salen dos reglas que se validan en los dos sentidos:

- `Σ hijas ≤ techo` — asignar a una hija por encima de lo que queda lanza `ValueError`.
- `techo ≥ Σ hijas` — bajar el techo por debajo de lo ya repartido lanza
  `CeilingBelowChildrenError`.

El techo **no crece solo**: mientras `reserva` absorba el remanente, subirlo automáticamente
sería bajarle la reserva al usuario sin decírselo.

### Errores del dominio

Los errores viven en `src/models/exceptions.py` y **heredan de `ValueError`**, así que quien ya
capturaba `ValueError` los sigue capturando. Lo que añaden es tipo y datos, para que el borde
pueda formatear el importe en euros sin leer el texto del mensaje.

- `DomainError` — raíz de la jerarquía. Nada la lanza directamente; sirve para capturar todos.
- `CeilingBelowChildrenError` — lleva `category` y `children_total_cents`, el mínimo al que
  puede bajar ese techo.

```python
try:
    wm.set_budget_for_category("fijos", 500.0)
except CeilingBelowChildrenError as e:
    print(f"{e.category} no puede bajar de {to_euros(e.children_total_cents)}")
```

### Persistencia (opcional)

`WorkflowManager` acepta repositorios inyectados en el constructor (`household_repo`, `member_repo`, `period_repo`, `expense_repo`, `debt_repo`, `saving_repo`, `income_entry_repo`, `bucket_entry_repo`, `saving_buckets_repo`, `budget_categories_repository`). Todos son opcionales — sin ellos, todo corre en memoria pura. Con ellos, cada operación relevante también persiste en PostgreSQL. Ver [README](../README.md#diseño) para qué cubre cada repositorio.

---

## Fases del ciclo mensual

```
REGISTRATION → PLANNING → MONTH → CLOSING
```

Cada método indica en qué fase(s) está permitido:

- `REGISTRATION` — solo en registro
- `PLANNING` — solo en planificación
- `MONTH` — solo durante el mes
- `PLANNING+` — planificación y cualquier fase posterior
- `MONTH+` — mes y cualquier fase posterior

`validate_phase(required_phase)` exige que la fase actual sea exactamente esa (usado internamente por los métodos que mutan estado). `validate_phase_accessible(required_phase)` es más permisivo: pasa si la fase actual es esa o si ya se completó antes (usado por las consultas).

---

## Fase REGISTRATION

### `register_member(name: str)`

Registra un miembro en el hogar. El nombre se normaliza automáticamente a minúsculas.

```python
wm.register_member("Amanda")
wm.register_member("Heri")
```

### `set_member_incomes(name: str, amount_eur: float)`

Establece el ingreso mensual de un miembro en euros.

```python
wm.set_member_incomes("Amanda", 2000.0)
wm.set_member_incomes("Heri", 1000.0)
```

> **`finish_registration()` ya no existe.** El período se abre con `start_new_month()`, que es
> el único punto de apertura y deja el hogar directamente en PLANNING. Ahí se crean las
> categorías estándar y los buckets de ahorro personal de cada miembro. Registrar miembros e
> ingresos se hace ya dentro de PLANNING. Ver "Fase CLOSING — Nuevo mes".

---

## Fase PLANNING — Categorías

Las categorías estándar (`fijos`, `variables`, `reserva`) **ya existen** tras `start_new_month()`. Solo usa estos métodos si necesitas categorías extra o modificar las existentes.

### `add_category(name: str, parent: str | None = None)`

Crea una categoría personalizada adicional. Si se pasa `parent`, la categoría cuelga como hija de una raíz existente: el presupuesto de las hijas se reparte dentro del techo de la categoría padre, no se suma aparte al total.

Una hija hereda el `is_shared` de su padre. El árbol tiene dos niveles: pasar como `parent` una categoría que ya es hija lanza `ValueError`.

**Nace con presupuesto 0**, y a una hija no se le puede asignar importe hasta que su raíz tenga techo — si no, no cabe dentro de 0. Para presupuestar de abajo arriba (recoger los gastos concretos y deducir el techo), quien llama recoge los importes primero, fija el techo de la raíz y después crea las hijas.

```python
wm.add_category("ocio")                       # categoría raíz
wm.add_category("alquiler", parent="fijos")   # hija de "fijos"
```

### `set_standard_categories()`

Asegura que existen las tres estándar (`fijos`, `variables`, `reserva`). Las que ya estén se dejan como están; solo crea las que falten. **No borra nada** ni resetea importes, así que llamarlo dos veces es inofensivo.

```python
wm.set_standard_categories()
```

### `remove_category(name: str)`

Elimina una categoría y resuelve qué pasa con sus gastos.

- **Con hijas:** lanza. Promoverlas a raíz metería su importe a competir contra el ingreso y cambiaría el presupuesto sin que nadie lo pida. Hay que borrarlas o moverlas antes.
- **Hija con gastos:** los gastos suben a su padre. Es neutro para los totales, porque ya contaban dentro de su techo.
- **Raíz con gastos:** lanza. No hay a quién subirlos.

```python
wm.remove_category("ocio")
```

### `get_root_categories() → list[str]` *(PLANNING+)*

Las categorías raíz, las únicas que cuentan contra el ingreso.

### `get_category_children(category_name: str) → list[str]` *(PLANNING+)*

Los nombres de las categorías que cuelgan de una raíz.

### `get_category_billable(category_name: str) → int (¢)` *(PLANNING+)*

Lo que una categoría reparte entre los miembros: su presupuesto menos lo que ya ha delegado en sus hijas. En una hoja es su presupuesto entero.

Es el número que evita el doble cobro: la suma de los facturables de todas las categorías es exactamente la suma de las raíces. En una raíz con hijas equivale a "lo que aún no está desglosado".

```python
wm.get_category_budget("fijos")     # 159000¢ — el techo
wm.get_category_billable("fijos")   #  65000¢ — lo no desglosado, si las hijas suman 94000¢
```

### Comportamiento de una categoría (`is_shared`)

Cada categoría es un objeto `Category` con un atributo booleano `is_shared`: `fijos` es `True`; `variables` y `reserva` son `False`. No hay un método público para consultarlo directamente. Tampoco decide quién participa en un gasto: `register_expense` exige la lista siempre, y `is_shared` de la categoría solo sirve para que el borde (CLI, API) sugiera un valor al usuario.

---

## Fase PLANNING — Presupuestos

### `set_budget_for_category(category: str, amount_euros: float)`

Asigna presupuesto a una categoría en euros. `reserva` se recalcula automáticamente.

```python
wm.set_budget_for_category("fijos", 1500.0)
wm.set_budget_for_category("variables", 900.0)
# reserva = 3000 - 1500 - 900 = 600€ (automático)
```

### `set_budget_by_percentages(percentages_floats: dict[str, float]) → None`

Asigna presupuesto a múltiples categorías como porcentaje de los ingresos totales. `reserva` se autocalcula. Los porcentajes son floats 0–100 y su suma no puede superar 100 (lanza `ValueError` si lo hace).

```python
wm.set_budget_by_percentages({"fijos": 50.0, "variables": 30.0})
# reserva = 20% automático
```

### `get_budget_as_percentage(category: str) → int (basis points)` *(PLANNING+)*

Retorna qué porcentaje del ingreso total representa el presupuesto de la categoría, en basis points.

```python
pct = wm.get_budget_as_percentage("fijos")  # 5000 = 50%
```

### `get_category_budget(category_name: str) → int (¢)` *(PLANNING+)*

Presupuesto asignado a una categoría.

```python
budget = wm.get_category_budget("fijos")  # 150000¢ = 1500€
```

### `get_total_budgeted() → int (¢)` *(PLANNING+)*

Suma de los presupuestos de las categorías raíz (las hijas viven dentro del techo de su padre, no se cuentan aparte).

```python
total = wm.get_total_budgeted()  # igual a total_ingresos si está todo presupuestado
```

### Dinero no presupuestado (`missing_money`)

No hay un método `get_missing_money()` independiente. El dato vive dentro de `get_planning_summary()` / `get_month_summary()` como `["missing_money"]` (`{"total": ..., "by_member": {...}}`), y por miembro individual vía `get_reserve_contribution_by_member(member)`.

---

## Fase PLANNING — Método de reparto

### `assign_distribution_method(method: MetodoReparto)`

Configura cómo se reparten los gastos entre miembros.

```python
from src.models.constants import MetodoReparto
wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)  # proporcional a ingresos
wm.assign_distribution_method(MetodoReparto.EQUAL)          # a partes iguales
wm.assign_distribution_method(MetodoReparto.CUSTOM)         # porcentajes manuales
```

### `set_custom_splits(splits: dict[str, float])`

Define porcentajes personalizados para el método CUSTOM. Los porcentajes son floats 0–100 y deben cubrir todos los miembros.

```python
wm.set_custom_splits({"Amanda": 60.0, "Heri": 40.0})
```

### `preview_budget_contribution_summary(method: MetodoReparto) → dict` *(PLANNING+)*

Calcula cómo quedarían las contribuciones con un método **hipotético**, sin modificar la configuración actual. Útil para comparar métodos antes de decidir.

```python
preview = wm.preview_budget_contribution_summary(MetodoReparto.EQUAL)
# {
#   "fijos": {
#     "planned": 150000,                              # ¢
#     "contributions": {"amanda": 75000, "heri": 75000},  # ¢
#     "total_assigned": 150000                        # ¢
#   }
# }
```

### `get_current_contributions() → dict` *(PLANNING+)*

Contribuciones calculadas con el método **ya configurado** (equivale a `preview` con el método activo). Úsalo cuando ya tienes el método fijado y solo quieres ver los números.

```python
contribs = wm.get_current_contributions()
```

### `get_total_contributions_by_member() → dict[str, int] (¢)`

Contribución total por miembro (suma de todas las categorías) según el método de reparto activo.

```python
totals = wm.get_total_contributions_by_member()
# {"amanda": 200000, "heri": 100000}
```

---

## Fase PLANNING — Deuda

La deuda representa el compromiso mensual de pago de deuda personal de cada miembro (hipoteca, préstamo, etc.). Se descuenta de la cuota de `reserva` de ese miembro.

### `add_debt_bucket(name, principal_euros, owner, installment_euros, start_date=None, description="") → UUID`

Declara una deuda personal: cuánto se debe en total, de quién es y qué cuota mensual tiene. Devuelve el `UUID` del bucket, que hace falta para registrar los pagos.

Sustituye al antiguo `set_member_debt(member, amount_euros)`, que solo guardaba la cuota del mes y no seguía el saldo pendiente.

```python
coche = wm.add_debt_bucket(
    name="coche", principal_euros=6000, owner="amanda", installment_euros=200.0
)
```

### `get_debt_status(member_name: str) → dict (valores en ¢)` *(PLANNING+)*

Estado de deuda de un miembro: cuánto comprometió, cuánto pagó y cuánto le queda.

```python
status = wm.get_debt_status("Amanda")
# {"committed": 20000, "paid": 0, "remaining": 20000}
```

### `get_all_debts_summary() → dict` *(PLANNING+)*

Resumen de deuda de todos los miembros: sus buckets, la cuota comprometida y lo pagado en el período.

```python
debts = wm.get_all_debts_summary()
```

---

## Fase PLANNING — Ahorro

El ahorro dejó de ser un objetivo suelto por miembro y pasó a vivir en **buckets** con meta y
fecha límite opcionales. Ver "Fase MONTH — Saving Buckets": se crean en PLANNING con
`create_saving_bucket()`.

> **Métodos retirados.** `set_member_saving_goal`, `auto_assign_saving_goals`,
> `get_saving_goal_status` y `get_all_saving_goals` ya no existen. El equivalente de hoy es
> `get_saving_requirement_by_member(member)`, que devuelve cuánto exigirían este mes las metas
> con fecha límite.

### `get_saving_requirement_by_member(member: str) → int (¢)` *(PLANNING+)*

Cuánto pedirían este mes las metas del miembro para llegar a tiempo. **Es informativo**: el
ahorro es una elección, no una obligación, y nada se valida contra él.

```python
wm.get_saving_requirement_by_member("Amanda")
```

### `validate_debt_doesnt_exceed_capacity()`

Valida que la cuota de deuda de cada miembro no supera su parte de `reserva`. Lanza `ValueError`
si alguien se excede. Se llama sola dentro de `finish_planning()`.

Sustituye a `validate_debt_and_saving_dont_exceed_capacity()`: **el ahorro salió de la
validación**, porque comprometerse a ahorrar no es una deuda con nadie.

```python
wm.validate_debt_doesnt_exceed_capacity()
```

---

## Fase PLANNING — Resumen y finalización

### `get_planning_summary() → dict` *(PLANNING+)*

Resumen completo de planificación: miembros, ingresos, método, porcentajes, categorías, presupuestos, deudas, ahorros, `total_budgeted`, `missing_money` (total y por miembro) y preview de contribuciones. Todos los valores monetarios en `¢`.

```python
summary = wm.get_planning_summary()
```

### `finish_planning()`

Valida que hay presupuesto asignado y que los compromisos de deuda/ahorro no superan la reserva. Congela el acuerdo y avanza a MONTH. Si hay `period_repo`, persiste el estado (`PLANNING → MONTH`) y las contribuciones acordadas; si hay `budget_categories_repository`, persiste las categorías de presupuesto del período.

```python
wm.finish_planning()
```

---

## Fase MONTH — Gastos

### `register_expense(member, category, amount_euros, participants, desc="", method=None, weights=None)`

Registra un gasto en euros.

**Cómo se reparte se decide gasto a gasto.** `weights` fija los porcentajes exactos (uno por participante, sumando 10000). `method` los deriva de un método concreto para esos participantes. Sin ninguno de los dos, se aplica el método acordado del hogar — que es un valor por defecto, no una imposición: cualquier gasto puede repartirse distinto sin tocar la configuración del hogar.

`participants`: quiénes cargan con el gasto. **Obligatorio y nunca vacío** — un gasto sin participantes no tiene reparto posible, así que declararlo así es un error de quien llama. La categoría no lo decide: quien pregunta es el borde (CLI, API).

Los tres casos que caben en esa lista:

| Lista | Qué significa |
|---|---|
| solo el pagador | gasto personal, no entra en el settlement |
| solo otro miembro | lo pagó uno y es de otro — el otro le debe el total |
| varios miembros | compartido, se reparte según el método del hogar |

`is_shared` de un gasto ya registrado no es un flag que se pase — se deriva de `len(participants) > 1` (ver `Expense.is_shared`).

```python
wm.register_expense("Amanda", "fijos", 500.0, ["Amanda", "Heri"], "alquiler")
wm.register_expense("Heri", "variables", 80.0, ["Heri"], "supermercado")
wm.register_expense("Amanda", "salud", 9.99, ["Heri"], "otoscopio")  # lo paga Amanda, es de Heri
```

---

## Fase MONTH — Deuda

### `register_debt_payment(member, amount_euros, description="", payment_date=None)`

Registra un pago de deuda en euros. Lanza `ValueError` si el pago acumulado superaría el compromiso declarado en planificación.

```python
wm.register_debt_payment("Amanda", 200.0, "hipoteca")
```

### `get_debt_history(member: str) → list[DebtEntry]` *(MONTH+)*

Historial completo de pagos de deuda de un miembro.

```python
history = wm.get_debt_history("Amanda")
```

---

## Fase MONTH — Ahorro

> **La "cuenta de ahorro" con `scope` PERSONAL/SHARED ya no existe.** Todo el ahorro vive en
> buckets: se depositan y se retiran con `deposit_to_saving_bucket()` y
> `withdraw_from_saving_bucket()`, y que un bucket sea personal o compartido se deriva de sus
> `owners`. Retirados: `register_savings_deposit`, `register_savings_withdrawal` y
> `get_member_savings_summary`. El resumen por miembro es hoy `get_saving_status(member)`.

### `get_savings_total_shared() → int (¢)` *(MONTH+)*

Total acumulado en el fondo de ahorro compartido por todos los miembros.

```python
total = wm.get_savings_total_shared()
```

### `get_savings_shared_by_period(start_date: date, end_date: date) → dict` *(PLANNING+)*

Movimientos de ahorro compartido filtrados por rango de fechas. Retorna `{member: [SavingEntry]}`.

```python
from datetime import date
movs = wm.get_savings_shared_by_period(date(2026, 4, 1), date(2026, 4, 30))
# {"amanda": [SavingEntry(...)], "heri": []}
```

---

## Fase MONTH — Saving Buckets

Los buckets son objetivos de ahorro concretos con una meta en euros y opcionalmente una fecha límite. Pueden ser personales (un solo dueño) o compartidos (varios dueños).

### `create_saving_bucket(bucket_name, goal_euros, scope, owners, deadline=None, description="") → UUID` *(PLANNING+)*

Crea un bucket y retorna su UUID, que se usa para todas las operaciones posteriores.

```python
from datetime import datetime
from src.models.constants import SavingScope

bucket_id = wm.create_saving_bucket(
    bucket_name="Vacaciones",
    goal_euros=1500.0,
    scope=SavingScope.SHARED,
    owners=["Amanda", "Heri"],
    deadline=datetime(2026, 8, 1),
    description="Viaje de verano",
)
```

### `deposit_to_saving_bucket(bucket_id, member, amount_euros, date=None)` *(MONTH)*

Registra un depósito en un bucket. El miembro debe ser uno de los `owners` del bucket.

```python
wm.deposit_to_saving_bucket(bucket_id, "Amanda", 200.0)
```

### `withdraw_from_saving_bucket(bucket_id, member, amount_euros, date=None)` *(MONTH)*

Registra un retiro de un bucket. No puede superar el saldo disponible del miembro.

```python
wm.withdraw_from_saving_bucket(bucket_id, "Amanda", 50.0)
```

### `get_bucket_by_id(bucket_id: UUID) → SavingBucket` *(PLANNING+)*

Obtiene un bucket por su UUID.

```python
bucket = wm.get_bucket_by_id(bucket_id)
bucket.balance       # saldo total del bucket en ¢
bucket.goal          # meta del bucket en ¢
bucket.bucket_name   # nombre
```

### `get_all_buckets() → dict[UUID, SavingBucket]` *(PLANNING+)*

Todos los buckets del hogar.

```python
buckets = wm.get_all_buckets()
```

### `get_buckets_by_member(member: str) → dict[UUID, SavingBucket]` *(PLANNING+)*

Buckets en los que participa un miembro (aparece en `owners`).

```python
buckets = wm.get_buckets_by_member("Amanda")
```

---

## Fase MONTH — Balances y consultas

### `get_member_owed_total(member_name: str) → int (¢)` *(MONTH+)*

Cuánto debe pagar el miembro según el acuerdo congelado en planificación.

```python
owed = wm.get_member_owed_total("Amanda")
```

### `get_member_paid_total(member_name: str) → int (¢)` *(MONTH+)*

Total de gastos registrados por el miembro en el mes.

```python
paid = wm.get_member_paid_total("Amanda")
```

### `get_member_balance(member_name: str) → int (¢)` *(MONTH+)*

Balance: `pagado - acordado`. Negativo = aún debe, positivo = pagó de más.

```python
balance = wm.get_member_balance("Amanda")  # -50000¢ → debe 500€ más
```

### `get_member_status(member_name: str) → dict (valores en ¢)` *(MONTH+)*

Estado completo del miembro: ingreso, acordado, pagado, balance, deuda, objetivo de ahorro y desglose por categoría.

```python
status = wm.get_member_status("Amanda")
# {
#   "income":       200000,   # ¢
#   "owed":         200000,   # ¢ — acordado en planificación
#   "paid":         150000,   # ¢ — gastado hasta ahora
#   "balance":      -50000,   # ¢ — debe 500€ más
#   "debt":          20000,   # ¢ — compromiso de deuda
#   "saving_goal":   30000,   # ¢ — objetivo de ahorro
#   "by_category": {
#     "fijos": {"contribution": 100000, "paid": 100000, "remaining": 0}
#   }
# }
```

### `get_category_spent(category_name: str) → int (¢)` *(MONTH+)*

Total gastado en una categoría **y en las que cuelgan de ella**. En una hoja no hay hijas, así que es su propio gasto.

```python
wm.get_category_spent("alquiler")  #  80000¢ — lo suyo
wm.get_category_spent("fijos")     #  93050¢ — lo suyo más el de sus hijas
```

### `get_total_spent() → int (¢)` *(MONTH+)*

Total de gastos registrados en el mes.

```python
total = wm.get_total_spent()
```

### `get_category_remaining(category_name: str) → int (¢)` *(MONTH+)*

Presupuesto restante en una categoría: `presupuestado - gastado`, contando el gasto de todo su subárbol.

**Puede salir negativo.** Gastar por encima del techo no se limita, se reporta: es información, no un error.

```python
remaining = wm.get_category_remaining("variables")
```

### `get_total_remaining() → int (¢)` *(MONTH+)*

Presupuesto restante total en el mes.

```python
remaining = wm.get_total_remaining()
```

### `get_settlement() → list[dict]` *(MONTH+)*

Transferencias mínimas para saldar los gastos compartidos entre miembros. Solo considera gastos con más de un participant (`is_shared` derivado).

```python
transfers = wm.get_settlement()
# [{"from": "heri", "to": "amanda", "amount": 15000}]  # amount en ¢
```

### `get_month_summary() → dict (valores en ¢)` *(MONTH+)*

Resumen financiero completo del mes: totales globales, desglose por categoría, estado de cada miembro (incluye su propio `by_category`) y `missing_money` (total y por miembro).

En `by_category` **solo aparecen las raíces**; sus hijas van dentro, en `children`. Así, sumar el primer nivel cuadra siempre con `totals` — con las hijas al mismo nivel se contaría dos veces el mismo dinero. `children` está siempre presente, vacío si la raíz no tiene hijas.

```python
summary = wm.get_month_summary()
# "by_category": {
#   "fijos": {
#     "ceiling":     159000,   # ¢ — techo de la raíz
#     "spent":        93050,   # ¢ — gasto de todo su subárbol
#     "remaining":    65950,   # ¢ — techo menos gasto; puede ser negativo
#     "billable":     65000,   # ¢ — lo que reparte por sí misma: techo − Σ hijas
#     "children": {
#       "alquiler": {"ceiling": 80000, "spent": 80000, "remaining": 0}
#     }
#   }
# }
```

### `finish_month(end_date: date | None = None)`

Avanza de MONTH a CLOSING y fija la fecha de fin del período (por defecto, hoy). Si hay `period_repo`, persiste el cambio de estado y la fecha.

La ventana del período es **semiabierta `[inicio, fin)`**: el día de cierre es exclusivo, para que el día de corte pertenezca solo al mes que empieza y no se cuente en los dos. Consecuencia práctica: cerrar con la fecha de hoy deja fuera los movimientos de hoy, y las consultas por período (deuda pagada, ahorro depositado) no los verán.

```python
wm.finish_month()                      # cierra hoy: lo de hoy queda fuera
wm.finish_month(end_date=date(2026, 6, 6))
```

---

## Fase CLOSING — Nuevo mes

### `start_new_month()`

Reinicia el household para empezar un nuevo ciclo (vuelve a REGISTRATION). Requiere haber llamado `finish_month()` antes (fase CLOSING accesible). Resetea el ahorro del mes y limpia `period_id` local — no borra nada de lo ya persistido.

```python
wm.start_new_month()
```

---

## Fase MONTH — Ingresos extra

Un ingreso extra es dinero que entra fuera del ingreso mensual base (bonus, reembolso, venta puntual). Aumenta la reserva del miembro que lo recibe.

### `add_income_entry(member_name, amount_euros, description="")`

Registra un ingreso extra y recalcula la reserva. Lanza `ValueError` si el miembro no está registrado.

```python
wm.add_income_entry("Amanda", 150.0, "reembolso seguro")
```

### `get_extra_income_entries() → list[IncomeEntry]` *(MONTH+)*

Ingresos extra registrados en el mes.

```python
entries = wm.get_extra_income_entries()
```

---

## Consultas generales (cualquier fase)

### `get_reserve_contribution_by_member(member: str) → int (¢)` *(PLANNING+)*

La parte de `reserva` que le toca a un miembro según el método de reparto. Es el número que
`validate_debt_doesnt_exceed_capacity()` usa como techo de su deuda, y el que aparece como
`missing_money` en los resúmenes.

### `get_saving_status(member: str) → dict` *(PLANNING+)*

Estado de ahorro de un miembro en el período: sus buckets y los totales (depositado, exigido por
las metas). Informativo — nada aquí es una obligación.

### `get_shared_buckets() → dict` *(PLANNING+)*

Los buckets con más de un propietario.

### `set_debt_bucket_installment(bucket_id: UUID, amount_euros: float)` *(PLANNING+)*

Cambia la cuota mensual de un bucket de deuda ya declarado.

### `get_registered_members() → list[str]`

Lista de nombres de miembros (normalizados a minúsculas).

```python
members = wm.get_registered_members()  # ["amanda", "heri"]
```

### `get_member_income(name: str) → int (¢)`

Ingreso mensual de un miembro.

```python
income = wm.get_member_income("Amanda")  # 200000¢ = 2000€
```

### `get_total_incomes() → int (¢)`

Ingreso total del hogar.

```python
total = wm.get_total_incomes()  # 300000¢ = 3000€
```

### `get_active_categories() → list[str]`

Categorías activas del presupuesto.

```python
cats = wm.get_active_categories()  # ["fijos", "variables", "reserva"]
```

---

## Consultas de datos congelados

Datos que se capturan al cerrar cada fase y no cambian después.

### `get_registration_summary() → dict` *(REGISTRATION+)*

Resumen del registro: miembros, ingresos por miembro y total. Valores monetarios en `¢`.

```python
summary = wm.get_registration_summary()
# {"members": [...], "member_incomes": {"amanda": 200000}, "total_household_income": 300000}
```

### `get_incomes() → dict[str, int] (¢)` *(PLANNING+)*

Ingreso mensual de cada miembro. Mientras el período sigue abierto manda el ingreso vivo: ya no se congela al abrir, solo el acuerdo del mes se congela en `finish_planning()`.

```python
incomes = wm.get_incomes()  # {"amanda": 200000, "heri": 100000}
```

### `get_agreed_percentages() → dict[str, int] (basis points)` *(MONTH+)*

Porcentajes de reparto tal como quedaron congelados al cerrar la planificación.

```python
pcts = wm.get_agreed_percentages()  # {"amanda": 6667, "heri": 3333}
```

### `get_agreed_contributions() → dict (valores en ¢)` *(MONTH+)*

Contribuciones por categoría y miembro tal como quedaron congeladas al cerrar la planificación.

```python
contribs = wm.get_agreed_contributions()
```

---

## Flujo completo de ejemplo

Ciclo completo en memoria. Ejecutable tal cual: no necesita base de datos.

```python
from datetime import date, timedelta

from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.workflow.workflow_manager import WorkflowManager

# Inicializar en memoria: sin repositorios, nada toca la base de datos
household = Household(
    budget=Budget(),
    expense_tracker=ExpenseTracker(),
    saving_bucket_tracker=SavingBucketTracker(),
    debt_bucket_tracker=DebtBucketTracker(),
    method=MetodoReparto.PROPORTIONAL,
)
wm = WorkflowManager(household=household)

# El período nace aquí, y con él las categorías estándar
wm.start_new_month(start_date=date(2026, 5, 6))

wm.register_member("Amanda")
wm.set_member_incomes("Amanda", 2000.0)
wm.register_member("Heri")
wm.set_member_incomes("Heri", 1000.0)

# PLANNING — presupuesto por porcentaje; reserva se autocalcula
wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
wm.set_budget_by_percentages({"fijos": 50.0, "variables": 30.0, "reserva": 20.0})

# Desglosar el techo de fijos: las hijas reparten dentro, no se suman aparte
wm.add_category("alquiler", parent="fijos")
wm.set_budget_for_category("alquiler", 1200.0)
print("techo fijos     ", wm.get_category_budget("fijos"))
print("sin desglosar   ", wm.get_category_billable("fijos"))

# Compromisos personales
coche = wm.add_debt_bucket(
    name="coche", principal_euros=6000, owner="amanda", installment_euros=200.0
)
vacaciones = wm.create_saving_bucket(
    bucket_name="vacaciones", owners=["amanda", "heri"], goal_euros=1200.0
)

wm.finish_planning()

# MONTH
wm.register_expense("Amanda", "alquiler", 1200.0, ["Amanda", "Heri"], "alquiler de mayo")
wm.register_expense("Heri", "variables", 300.0, ["Heri"], "supermercado")
wm.register_debt_payment("Amanda", coche, 200.0)
wm.deposit_to_saving_bucket(vacaciones, "Heri", 150.0)

print("gasto en fijos  ", wm.get_category_spent("fijos"))
print("settlement      ", wm.get_settlement())

# CLOSING — el fin es exclusivo, así que va después del último movimiento
wm.finish_month(end_date=date.today() + timedelta(days=1))
print("total gastado   ", wm.get_month_summary()["totals"]["total_spent"])
```

```
techo fijos      150000
sin desglosar    30000
gasto en fijos   120000
settlement       [{'from': 'heri', 'to': 'amanda', 'amount': 40000}]
total gastado    150000
```
