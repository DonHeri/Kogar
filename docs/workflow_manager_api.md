# WorkflowManager — Referencia de API

El usuario interactúa **únicamente** con `WorkflowManager`. Las clases internas (`Household`, `SavingTracker`, `DebtTracker`, etc.) son detalles de implementación.

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

---

## Fase REGISTRATION

### `register_member(name: str)`

Registra un miembro en el hogar. El nombre se normaliza automáticamente a minúsculas.

```python
wm.register_member("Amanda")
wm.register_member("Heri")
```

### `set_incomes(name: str, amount_eur: float)`

Establece el ingreso mensual de un miembro en euros.

```python
wm.set_incomes("Amanda", 2000.0)
wm.set_incomes("Heri", 1000.0)
```

### `finish_registration()`

Valida que hay al menos un miembro con ingresos, congela los datos y avanza a PLANNING.
Las categorías estándar (`fijos`, `variables`, `reserva`) se crean automáticamente en este paso.

```python
wm.finish_registration()
```

---

## Fase PLANNING — Categorías

Las categorías estándar (`fijos`, `variables`, `reserva`) **ya existen** tras `finish_registration()`. Solo usa estos métodos si necesitas categorías extra o modificar las existentes.

### `add_category(name: str)`

Crea una categoría personalizada adicional.

```python
wm.add_category("ocio")
```

### `set_standard_categories()`

Resetea las categorías a las estándar (`fijos`, `variables`, `reserva`), eliminando cualquier categoría personalizada. Útil si se quiere volver al estado inicial de planificación.

```python
wm.set_standard_categories()
```

### `remove_category(name: str)`

Elimina una categoría. Solo elimina categorías que hayas añadido con `add_category()` — eliminar una estándar puede romper el flujo.

```python
wm.remove_category("ocio")
```

### `get_category_behavior(category: str) → CategoryBehavior` *(PLANNING+)*

Retorna si la categoría es `SHARED` o `PERSONAL`.

- `SHARED` — los gastos de esta categoría se distribuyen entre miembros y se reflejan en el `settlement`
- `PERSONAL` — los gastos no cuentan para el `settlement`

```python
behavior = wm.get_category_behavior("fijos")
# CategoryBehavior.SHARED o CategoryBehavior.PERSONAL
```

---

## Fase PLANNING — Presupuestos

### `set_budget_for_category(category: str, amount_euros: float)`

Asigna presupuesto a una categoría en euros. `reserva` se recalcula automáticamente.

```python
wm.set_budget_for_category("fijos", 1500.0)
wm.set_budget_for_category("variables", 900.0)
# reserva = 3000 - 1500 - 900 = 600€ (automático)
```

### `set_budget_by_percentages(percentages: dict[str, float])`

Asigna presupuesto a múltiples categorías como porcentaje de los ingresos totales. `reserva` se autocalcula. Los porcentajes son floats 0–100.

```python
wm.set_budget_by_percentages({"fijos": 50.0, "variables": 30.0})
# reserva = 20% automático
```

### `apply_percentage_distribution(percentages: dict[str, float])`

Igual que `set_budget_by_percentages` pero con validaciones previas: verifica que todas las categorías existen y que la suma no supera el 100%.

```python
wm.apply_percentage_distribution({"fijos": 50.0, "variables": 30.0})
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

Suma de los presupuestos de todas las categorías.

```python
total = wm.get_total_budgeted()  # igual a total_ingresos si está todo presupuestado
```

### `get_missing_money() → int (¢)` *(PLANNING+)*

Dinero no presupuestado: `total_ingresos - total_presupuestado`. Debería ser 0 cuando el presupuesto está completo, ya que `reserva` absorbe el resto.

```python
missing = wm.get_missing_money()
```

### `get_missing_money_by_member(member_name: str) → int (¢)` *(PLANNING+)*

Parte del dinero no presupuestado que le corresponde a un miembro según el método de reparto activo.

```python
missing = wm.get_missing_money_by_member("Amanda")
```

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

---

## Fase PLANNING — Deuda

La deuda representa el compromiso mensual de pago de deuda personal de cada miembro (hipoteca, préstamo, etc.). Se descuenta de la cuota de `reserva` de ese miembro.

### `set_member_debt(member: str, amount_euros: float)`

Declara cuánto pagará el miembro en concepto de deuda durante el mes.

```python
wm.set_member_debt("Amanda", 200.0)  # Amanda pagará 200€ de deuda este mes
```

### `get_debt_status(member_name: str) → dict (valores en ¢)` *(PLANNING+)*

Estado de deuda de un miembro: cuánto comprometió, cuánto pagó y cuánto le queda.

```python
status = wm.get_debt_status("Amanda")
# {"committed": 20000, "paid": 0, "remaining": 20000}
```

### `get_all_debts() → dict[str, int] (¢)` *(PLANNING+)*

Deuda comprometida de todos los miembros.

```python
debts = wm.get_all_debts()
# {"amanda": 20000, "heri": 10000}
```

---

## Fase PLANNING — Ahorro

El ahorro representa el objetivo mensual de ahorro de cada miembro. Se descuenta de la cuota de `reserva` junto con la deuda.

### `set_member_saving_goal(member: str, amount_euros: float)`

Declara manualmente el objetivo de ahorro mensual de un miembro.

```python
wm.set_member_saving_goal("Amanda", 300.0)
```

### `auto_assign_saving_goals()`

Calcula y asigna automáticamente el objetivo de ahorro de cada miembro según:

```text
saving_goal[m] = cuota_reserva[m] - deuda[m]
```

Llámalo después de `set_member_debt()` y antes de `finish_planning()`.

```python
wm.set_member_debt("Amanda", 200.0)
wm.auto_assign_saving_goals()
```

### `get_saving_goal_status(member_name: str) → dict (valores en ¢)` *(PLANNING+)*

Estado del objetivo de ahorro: comprometido, depositado y pendiente.

```python
status = wm.get_saving_goal_status("Amanda")
# {"committed": 30000, "paid": 15000, "remaining": 15000}
```

### `get_all_saving_goals() → dict[str, int] (¢)` *(PLANNING+)*

Objetivo de ahorro comprometido de todos los miembros.

```python
goals = wm.get_all_saving_goals()
# {"amanda": 30000, "heri": 15000}
```

### `validate_debt_and_saving_dont_exceed_capacity()`

Valida que `deuda + ahorro` de cada miembro no supera su cuota de `reserva`. Lanza `ValueError` si algún miembro se excede. Se llama automáticamente dentro de `finish_planning()`, pero puede invocarse manualmente durante la planificación para detectar problemas antes.

```python
wm.validate_debt_and_saving_dont_exceed_capacity()
```

---

## Fase PLANNING — Resumen y finalización

### `get_planning_summary() → dict` *(PLANNING+)*

Resumen completo de planificación: miembros, ingresos, método, presupuestos por categoría, deudas, ahorros, dinero no presupuestado y preview de contribuciones. Todos los valores monetarios en `¢`.

```python
summary = wm.get_planning_summary()
```

### `finish_planning()`

Valida que hay presupuesto asignado y que los compromisos de deuda/ahorro no superan la reserva. Congela el acuerdo y avanza a MONTH.

```python
wm.finish_planning()
```

---

## Fase MONTH — Gastos

### `register_expense(member, category, amount_euros, desc="", is_shared=None)`

Registra un gasto en euros. Si `is_shared=None`, el comportamiento se deriva del `CategoryBehavior` de la categoría (`SHARED` → compartido, `PERSONAL` → individual). Se puede sobreescribir explícitamente.

```python
wm.register_expense("Amanda", "fijos", 500.0, "alquiler")
wm.register_expense("Heri", "variables", 80.0, "supermercado", is_shared=True)
```

---

## Fase MONTH — Deuda

### `register_debt_payment(member, amount_euros, description="", date=None)`

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

## Fase MONTH — Ahorro en cuenta

### `register_savings_deposit(member, amount_euros, destination, description="", date=None)`

Registra un depósito en la cuenta de ahorro. `destination` indica si es `PERSONAL` o `SHARED`.

```python
from src.models.constants import SavingScope
wm.register_savings_deposit("Amanda", 300.0, SavingScope.PERSONAL, "ahorro mensual")
wm.register_savings_deposit("Heri", 150.0, SavingScope.SHARED, "fondo común")
```

### `register_savings_withdrawal(member, amount_euros, destination, description="", date=None)`

Registra un retiro de la cuenta de ahorro. No puede superar el saldo disponible.

```python
wm.register_savings_withdrawal("Amanda", 100.0, SavingScope.PERSONAL)
```

### `get_member_savings_summary(member: str) → dict (valores en ¢)` *(PLANNING+)*

Resumen de ahorro de un miembro: balances total/personal/shared, historial completo y movimientos del mes actual.

```python
summary = wm.get_member_savings_summary("Amanda")
# {
#   "balance_total":    30000,   # ¢
#   "balance_personal": 20000,   # ¢
#   "balance_shared":   10000,   # ¢
#   "history": [...],
#   "actual_month": {"personal": 20000, "shared": 10000}  # ¢
# }
```

### `get_savings_total_shared() → int (¢)` *(MONTH+)*

Total acumulado en el fondo de ahorro compartido por todos los miembros.

```python
total = wm.get_savings_total_shared()
```

### `get_savings_shared_by_month(month: int, year: int) → dict` *(PLANNING+)*

Movimientos de ahorro compartido filtrados por mes y año. Retorna `{member: [SavingEntry]}`.

```python
movs = wm.get_savings_shared_by_month(month=4, year=2026)
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

### `deposit_to_bucket(bucket_id, member, amount_euros, date=None)` *(MONTH)*

Registra un depósito en un bucket. El miembro debe ser uno de los `owners` del bucket.

```python
wm.deposit_to_bucket(bucket_id, "Amanda", 200.0)
```

### `withdraw_from_bucket(bucket_id, member, amount_euros, date=None)` *(MONTH)*

Registra un retiro de un bucket. No puede superar el saldo disponible del miembro.

```python
wm.withdraw_from_bucket(bucket_id, "Amanda", 50.0)
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

Total de gastos registrados en una categoría.

```python
spent = wm.get_category_spent("variables")
```

### `get_total_spent() → int (¢)` *(MONTH+)*

Total de gastos registrados en el mes.

```python
total = wm.get_total_spent()
```

### `get_category_remaining(category_name: str) → int (¢)` *(MONTH+)*

Presupuesto restante en una categoría: `presupuestado - gastado`.

```python
remaining = wm.get_category_remaining("variables")
```

### `get_total_remaining() → int (¢)` *(MONTH+)*

Presupuesto restante total en el mes.

```python
remaining = wm.get_total_remaining()
```

### `get_settlement() → list[dict]` *(MONTH+)*

Transferencias mínimas para saldar los gastos compartidos entre miembros. Solo considera gastos con `is_shared=True`.

```python
transfers = wm.get_settlement()
# [{"from": "heri", "to": "amanda", "amount": 15000}]  # amount en ¢
```

### `get_month_summary() → dict (valores en ¢)` *(MONTH+)*

Resumen financiero completo del mes: totales globales, desglose por categoría, estado de cada miembro y dinero no presupuestado.

```python
summary = wm.get_month_summary()
```

### `finish_month()`

Avanza de MONTH a CLOSING.

```python
wm.finish_month()
```

---

## Consultas generales (cualquier fase)

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

### `get_registered_incomes() → dict[str, int] (¢)` *(PLANNING+)*

Ingresos tal como quedaron congelados al cerrar el registro.

```python
incomes = wm.get_registered_incomes()  # {"amanda": 200000, "heri": 100000}
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

```python
from src.models.budget import Budget
from src.models.constants import MetodoReparto, SavingScope
from src.models.debt_tracker import DebtTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.saving_tracker import SavingTracker
from src.workflow.workflow_manager import WorkflowManager

# Inicializar
household = Household(Budget(), ExpenseTracker(), SavingTracker(), DebtTracker())
wm = WorkflowManager(household)

# REGISTRATION
wm.register_member("Amanda")
wm.register_member("Heri")
wm.set_incomes("Amanda", 2000.0)   # 2000€
wm.set_incomes("Heri", 1000.0)    # 1000€
wm.finish_registration()
# → categorías fijos/variables/reserva creadas automáticamente

# PLANNING
wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
wm.set_budget_for_category("fijos", 1500.0)      # 1500€
wm.set_budget_for_category("variables", 900.0)   # 900€
# reserva = 3000 - 1500 - 900 = 600€ (automático)

wm.set_member_debt("Amanda", 200.0)   # Amanda pagará 200€ de deuda
wm.auto_assign_saving_goals()
# Amanda: saving_goal = cuota_reserva_amanda - 20000¢
# Heri:   saving_goal = cuota_reserva_heri   - 0¢

wm.finish_planning()

# MONTH
wm.register_expense("Amanda", "fijos", 1500.0, "alquiler")
wm.register_expense("Heri", "variables", 300.0, "supermercado", is_shared=True)
wm.register_debt_payment("Amanda", 200.0, "hipoteca")
wm.register_savings_deposit("Heri", 150.0, SavingScope.PERSONAL, "ahorro mensual")

print(wm.get_settlement())
# [{"from": "heri", "to": "amanda", "amount": 10000}]  # Heri debe 100€ a Amanda

wm.finish_month()
```
