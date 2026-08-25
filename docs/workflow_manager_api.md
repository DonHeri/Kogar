# WorkflowManager — Referencia de API

El usuario interactúa **únicamente** con `WorkflowManager`. Las clases internas (`Household`, `SavingTracker`, `DebtTracker`, etc.) son detalles de implementación.

---

## Fases del ciclo mensual

```
REGISTRATION → PLANNING → MONTH → CLOSING
```

Cada método indica en qué fase(s) está permitido:

- `REGISTRATION` — sólo en registro
- `PLANNING` — sólo en planificación
- `MONTH` — sólo durante el mes
- `PLANNING+` — en planificación y cualquier fase posterior
- `MONTH+` — en mes y cualquier fase posterior

---

## Fase REGISTRATION

### `register_member(name: str)`

Registra un miembro en el hogar.

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

Valida que hay miembros con ingresos, congela los datos y avanza a PLANNING.

```python
wm.finish_registration()
```

---

## Fase PLANNING — Categorías

### `add_category(name: str)`

Crea una categoría personalizada.

```python
wm.add_category("ocio")
```

### `set_standard_categories()`

Actualmente **se establecen de forma automática** en `household.freeze_registration_state()`
Establece las categorías estándar: `fijos`, `variables`, `reserva`.

```python
wm.set_standard_categories()
```

### `remove_category(name: str)`

Actualmente no hay flexibilidad en creación de categorías. Por lo que eliminar una categoría puede romper el flujo del programa.
Elimina una categoría existente.

```python
wm.remove_category("ocio")
```

### `get_category_behavior(category: str) → CategoryBehavior` _(PLANNING+)_

Retorna si la categoría es `SHARED` (gastos compartidos) o `PERSONAL`.
`SHARED` - Se refleja en el `settlement`
`PERSONAL` - No cuenta para el `settlement`

```python
behavior = wm.get_category_behavior("fijos")
# CategoryBehavior.SHARED o CategoryBehavior.PERSONAL
```

---

## Fase PLANNING — Presupuestos

### `set_budget_for_category(category: str, amount_euros: float)`

Asigna presupuesto a una categoría en euros. `reserva` se autocalcula.

```python
wm.set_budget_for_category("fijos", 1500.0)
wm.set_budget_for_category("variables", 900.0)
# reserva = total_ingresos - fijos - variables (automático)
```

### `set_budget_by_percentages(percentages: dict[str, float])`

Asigna presupuesto a múltiples categorías como porcentaje de los ingresos totales. `reserva` se autocalcula.

```python
wm.set_budget_by_percentages({"fijos": 50.0, "variables": 30.0})
# reserva = 20% automático
```

### `apply_percentage_distribution(percentages: dict[str, float])`

Igual que `set_budget_by_percentages` pero valida que las categorías existen y que la suma no supera el 100%.

```python
wm.apply_percentage_distribution({"fijos": 50.0, "variables": 30.0})
```

### `get_budget_as_percentage(category: str) → int` _(PLANNING+)_

Retorna qué porcentaje del ingreso total representa el presupuesto de la categoría, en basis points (5000 = 50%).

```python
pct = wm.get_budget_as_percentage("fijos")  # 5000 = 50%
```

### `get_category_budget(category_name: str) → int` _(PLANNING+)_

Presupuesto asignado a una categoría en céntimos.

```python
budget = wm.get_category_budget("fijos")  # 150000 = 1500€
```

### `get_total_budgeted() → int` _(PLANNING+)_

Total presupuestado en céntimos.

```python
total = wm.get_total_budgeted()
```

### `get_missing_money() → int` _(PLANNING+)_

Dinero no presupuestado: `total_ingresos - total_presupuestado`.

```python
missing = wm.get_missing_money()
```

### `get_missing_money_by_member(member_name: str) → int` _(PLANNING+)_

Parte del dinero no presupuestado que corresponde a un miembro según el método de reparto.

```python
missing = wm.get_missing_money_by_member("Amanda")
```

---

## Fase PLANNING — Método de reparto

### `assign_distribution_method(method: MetodoReparto)`

Configura cómo se reparten los gastos entre miembros.

```python
from src.models.constants import MetodoReparto
wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)  # por ingresos
wm.assign_distribution_method(MetodoReparto.EQUAL)          # a partes iguales
wm.assign_distribution_method(MetodoReparto.CUSTOM)         # personalizado
```

### `set_custom_splits(splits: dict[str, float])`

Define porcentajes personalizados para el método CUSTOM (0–100).

```python
wm.set_custom_splits({"Amanda": 60.0, "Heri": 40.0})
```

### `preview_budget_contribution_summary(method: MetodoReparto) → dict` _(PLANNING+)_

Vista previa de contribuciones por categoría con un método específico (sin modificar la configuración).

```python
preview = wm.preview_budget_contribution_summary(MetodoReparto.EQUAL)
# {"fijos": {"planned": 150000, "contributions": {"amanda": 75000, "heri": 75000}, ...}}
```

### `get_current_contributions() → dict` _(PLANNING+)_

Contribuciones con el método ya configurado.

```python
contribs = wm.get_current_contributions()
```

---

## Fase PLANNING — Deuda

### `set_member_debt(member: str, amount_euros: float)`

Declara la deuda mensual comprometida de un miembro (lo que pagará de deuda ese mes).

```python
wm.set_member_debt("Amanda", 200.0)
```

### `get_debt_status(member_name: str) → dict` _(PLANNING+)_

Estado de deuda de un miembro: comprometido, pagado y pendiente.

```python
status = wm.get_debt_status("Amanda")
# {"committed": 20000, "paid": 0, "remaining": 20000}
```

### `get_all_debts() → dict[str, int]` _(PLANNING+)_

Mapa `{member: deuda_comprometida_céntimos}` de todos los miembros.

```python
debts = wm.get_all_debts()
# {"amanda": 20000, "heri": 10000}
```

---

## Fase PLANNING — Ahorro

### `set_member_saving_goal(member: str, amount_euros: float)`

Declara el ahorro mensual comprometido de un miembro.

```python
wm.set_member_saving_goal("Amanda", 300.0)
```

### `auto_assign_saving_goals()`

Asigna automáticamente el ahorro de cada miembro como:
`saving_goal = cuota_reserva - deuda_declarada`.

```python
wm.set_member_debt("Amanda", 200.0)
wm.auto_assign_saving_goals()
# Amanda: saving_goal = cuota_reserva_amanda - 20000
```

### `get_saving_goal_status(member_name: str) → dict` _(PLANNING+)_

Estado del objetivo de ahorro: comprometido, pagado y pendiente.

```python
status = wm.get_saving_goal_status("Amanda")
# {"committed": 30000, "paid": 0, "remaining": 30000}
```

### `get_all_saving_goals() → dict[str, int]` _(PLANNING+)_

Mapa `{member: ahorro_comprometido_céntimos}` de todos los miembros.

```python
goals = wm.get_all_saving_goals()
# {"amanda": 30000, "heri": 15000}
```

### `validate_debt_and_saving_dont_exceed_capacity()`

Valida que `deuda + ahorro` de cada miembro no supera su cuota de reserva. Se llama automáticamente en `finish_planning()`.

```python
wm.validate_debt_and_saving_dont_exceed_capacity()
```

---

## Fase PLANNING — Resumen y finalización

### `get_planning_summary() → dict` _(PLANNING+)_

Resumen completo de planificación: miembros, ingresos, método, presupuestos, deudas, ahorros y contribuciones.

```python
summary = wm.get_planning_summary()
```

### `finish_planning()`

Valida presupuestos y compromisos, congela el acuerdo y avanza a MONTH.

```python
wm.finish_planning()
```

---

## Fase MONTH — Gastos

### `register_expense(member, category, amount_euros, desc="", is_shared=None)`

Registra un gasto. Si `is_shared=None`, el comportamiento se deriva del tipo de categoría.

```python
wm.register_expense("Amanda", "fijos", 500.0, "alquiler")
wm.register_expense("Heri", "variables", 80.0, "supermercado", is_shared=True)
```

---

## Fase MONTH — Deuda

### `register_debt_payment(member, amount_euros, description="", date=None)`

Registra un pago de deuda. No puede superar el compromiso declarado.

```python
wm.register_debt_payment("Amanda", 200.0, "hipoteca")
```

### `get_debt_history(member: str) → list` _(MONTH+)_

Historial completo de pagos de deuda de un miembro.

```python
history = wm.get_debt_history("Amanda")
# [DebtEntry(...), ...]
```

---

## Fase MONTH — Ahorro en cuenta

### `register_savings_deposit(member, amount_euros, destination, description="", date=None)`

Registra un depósito en la cuenta de ahorro (PERSONAL o SHARED).

```python
from src.models.constants import SavingScope
wm.register_savings_deposit("Amanda", 300.0, SavingScope.PERSONAL)
wm.register_savings_deposit("Heri", 150.0, SavingScope.SHARED)
```

### `register_savings_withdrawal(member, amount_euros, destination, description="", date=None)`

Registra un retiro de la cuenta de ahorro.

```python
wm.register_savings_withdrawal("Amanda", 100.0, SavingScope.PERSONAL)
```

### `get_member_savings_summary(member: str) → dict` _(PLANNING+)_

Resumen de ahorro de un miembro: balances total/personal/shared, historial y mes actual.

```python
summary = wm.get_member_savings_summary("Amanda")
# {
#   "balance_total": 30000,
#   "balance_personal": 20000,
#   "balance_shared": 10000,
#   "history": [...],
#   "actual_month": {"personal": 20000, "shared": 10000}
# }
```

### `get_savings_total_shared() → int` _(MONTH+)_

Total ahorrado en el fondo compartido por todos los miembros.

```python
total = wm.get_savings_total_shared()
```

### `get_savings_shared_by_month(month: int, year: int) → dict` _(PLANNING+)_

Movimientos de ahorro compartido filtrados por mes y año.

```python
movs = wm.get_savings_shared_by_month(month=4, year=2026)
# {"amanda": [SavingEntry(...)], "heri": []}
```

---

## Fase MONTH — Saving Buckets

Los buckets son objetivos de ahorro concretos (ej. "Vacaciones", "Coche nuevo") con una meta y opcionalmente una fecha límite.

### `create_saving_bucket(bucket_name, goal_euros, scope, owners, deadline=None, description="") → UUID` _(PLANNING+)_

Crea un bucket y retorna su UUID.

```python
from src.models.constants import SavingScope

bucket_id = wm.create_saving_bucket(
    bucket_name="Vacaciones",
    goal_euros=1500.0,
    scope=SavingScope.SHARED,
    owners=["Amanda", "Heri"],
    deadline=datetime(2026, 8, 1),
)
```

### `deposit_to_bucket(bucket_id, member, amount_euros, date=None)`

Registra un depósito en un bucket existente.

```python
wm.deposit_to_bucket(bucket_id, "Amanda", 200.0)
```

### `withdraw_from_bucket(bucket_id, member, amount_euros, date=None)`

Registra un retiro de un bucket.

```python
wm.withdraw_from_bucket(bucket_id, "Amanda", 50.0)
```

### `get_bucket_by_id(bucket_id: UUID) → SavingBucket` _(PLANNING+)_

Obtiene un bucket por su UUID.

```python
bucket = wm.get_bucket_by_id(bucket_id)
print(bucket.balance)  # saldo actual en céntimos
```

### `get_all_buckets() → dict[UUID, SavingBucket]` _(PLANNING+)_

Todos los buckets del hogar.

```python
buckets = wm.get_all_buckets()
```

### `get_buckets_by_member(member: str) → dict[UUID, SavingBucket]` _(PLANNING+)_

Buckets en los que participa un miembro.

```python
buckets = wm.get_buckets_by_member("Amanda")
```

---

## Fase MONTH — Balances y consultas

### `get_member_owed_total(member_name: str) → int` _(MONTH+)_

Cuánto debe pagar el miembro según el acuerdo (en céntimos).

```python
owed = wm.get_member_owed_total("Amanda")
```

### `get_member_paid_total(member_name: str) → int` _(MONTH+)_

Total gastado por un miembro en el mes (en céntimos).

```python
paid = wm.get_member_paid_total("Amanda")
```

### `get_member_balance(member_name: str) → int` _(MONTH+)_

Balance del miembro: `pagado - acordado`. Negativo = debe más, positivo = pagó de más.

```python
balance = wm.get_member_balance("Amanda")
```

### `get_member_status(member_name: str) → dict` _(MONTH+)_

Estado completo del miembro: ingresos, acordado, pagado, balance, deuda, ahorro y desglose por categoría.

```python
status = wm.get_member_status("Amanda")
# {
#   "income": 200000, "owed": 200000, "paid": 150000, "balance": -50000,
#   "debt": 20000, "saving_goal": 30000,
#   "by_category": {"fijos": {"contribution": 100000, "paid": 100000, "remaining": 0}}
# }
```

### `get_category_spent(category_name: str) → int` _(MONTH+)_

Total gastado en una categoría.

```python
spent = wm.get_category_spent("variables")
```

### `get_total_spent() → int` _(MONTH+)_

Total gastado en el mes.

```python
total = wm.get_total_spent()
```

### `get_category_remaining(category_name: str) → int` _(MONTH+)_

Presupuesto restante en una categoría: `presupuesto - gastado`.

```python
remaining = wm.get_category_remaining("variables")
```

### `get_total_remaining() → int` _(MONTH+)_

Total restante por gastar en el mes.

```python
remaining = wm.get_total_remaining()
```

### `get_settlement() → list[dict]` _(MONTH+)_

Transferencias mínimas para saldar gastos compartidos.

```python
transfers = wm.get_settlement()
# [{"from": "heri", "to": "amanda", "amount": 15000}]
```

### `get_month_summary() → dict` _(MONTH+)_

Resumen financiero completo del mes: totales, por categoría, por miembro y dinero no presupuestado.

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

Lista de miembros registrados.

```python
members = wm.get_registered_members()  # ["amanda", "heri"]
```

### `get_member_income(name: str) → int`

Ingreso mensual de un miembro en céntimos.

```python
income = wm.get_member_income("Amanda")
```

### `get_total_incomes() → int`

Ingreso total del hogar en céntimos.

```python
total = wm.get_total_incomes()
```

### `get_active_categories() → list[str]`

Categorías activas del presupuesto.

```python
cats = wm.get_active_categories()  # ["fijos", "variables", "reserva"]
```

---

## Consultas de datos congelados

### `get_registration_summary() → dict` _(REGISTRATION+)_

Resumen de la fase de registro: miembros, ingresos individuales y total.

```python
summary = wm.get_registration_summary()
```

### `get_registered_incomes() → dict[str, int]` _(PLANNING+)_

Ingresos congelados al cerrar el registro.

```python
incomes = wm.get_registered_incomes()  # {"amanda": 200000, "heri": 100000}
```

### `get_agreed_percentages() → dict[str, int]` _(MONTH+)_

Porcentajes de reparto acordados y congelados al cerrar la planificación.

```python
pcts = wm.get_agreed_percentages()  # {"amanda": 6667, "heri": 3333}
```

### `get_agreed_contributions() → dict` _(MONTH+)_

Contribuciones por categoría acordadas y congeladas al cerrar la planificación.

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
wm.set_incomes("Amanda", 2000.0)
wm.set_incomes("Heri", 1000.0)
wm.finish_registration()

# PLANNING
wm.assign_distribution_method(MetodoReparto.PROPORTIONAL)
wm.set_budget_for_category("fijos", 1500.0)
wm.set_budget_for_category("variables", 900.0)
# reserva = 3000 - 1500 - 900 = 600€ (automático)

wm.set_member_debt("Amanda", 200.0)
wm.auto_assign_saving_goals()
wm.finish_planning()

# MONTH
wm.register_expense("Amanda", "fijos", 1500.0, "alquiler")
wm.register_expense("Heri", "variables", 300.0, "supermercado", is_shared=True)
wm.register_debt_payment("Amanda", 200.0, "hipoteca")
wm.register_savings_deposit("Heri", 150.0, SavingScope.PERSONAL)

print(wm.get_settlement())
wm.finish_month()
```
