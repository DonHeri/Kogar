# Mapa de persistencia — Fases 1-3

Orden de ejecución para completar la persistencia del proyecto.
Cada bloque es autónomo: terminas, commiteas, y arrancas el siguiente.

---

## Estado actual

| Entidad                       | Migración | Repositorio | Integrado en WM |
| ----------------------------- | --------- | ----------- | --------------- |
| `households`                  | ✅        | ✅          | ✅              |
| `members`                     | ✅        | ✅          | ✅              |
| `household_periods`           | ✅        | ✅          | ✅              |
| `period_agreed_contributions` | ✅        | ✅          | ✅              |
| `expenses`                    | ✅        | ✅          | ✅              |
| `expense_participants`        | ✅        | ✅          | ✅              |
| `categories`                  | ✅        | ✅          | ✅              |
| `debt_entries`                | ✅        | ✅          | ✅              |
| `saving_entries`              | ✅        | ✅          | ✅              |
| `saving_buckets`              | ✅        | ✅          | ✅              |
| `bucket_entries`              | ✅        | ✅          | ✅              |
| `month_settlements`           | ❌        | ❌          | ❌              |
| `income_entries`              | ✅        | ✅          | ✅              |

---

## Bloque 1 — Acabar refactor `participants` (en curso)

**1.1** `WorkflowManager.register_expense()` — cambia `is_shared: bool | None` por `participants: list[str] | None`.
Si no se pasa: `category.is_shared == True` → `list(self.household.members.keys())`; `False` → solo el pagador.

**1.2** `Household.get_settlement()` — filtra por `len(expense.participants) > 1` en lugar de `expense.is_shared`.
Construye el `income_map` solo con los participantes de cada gasto.

**1.3** Tests de settlement en `test_household.py` — reemplaza `is_shared=True/False` por `participants=[...]`.

**1.4** Tests de WM — actualiza los dos tests que usan `is_shared=` en `register_expense`.

**1.5** `pytest -q --no-cov` en verde → commit `refactor: replace is_shared with participants in Expense`.

---

## Bloque 2 — Migración `expenses` + `expense_participants`

**2.1** Migración `expenses`:

```sql
CREATE TABLE expenses (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES household_periods(id),
    payer_id INTEGER NOT NULL REFERENCES members(id),
    category_name VARCHAR(100) NOT NULL,
    amount_cents INTEGER NOT NULL,
    description VARCHAR(255) DEFAULT '',
    expense_date TIMESTAMP NOT NULL
);
```

**2.2** Migración `expense_participants`:

```sql
CREATE TABLE expense_participants (
    expense_id INTEGER NOT NULL REFERENCES expenses(id),
    member_id INTEGER NOT NULL REFERENCES members(id),
    weight SMALLINT,
    PRIMARY KEY (expense_id, member_id)
);
```

**2.3** `alembic upgrade head` → verificar.

---

## Bloque 3 — `ExpenseRepository` ✅ COMPLETADO

Archivo: `src/storage/expense_repository.py` (creado, incompleto)

**Estado:** `__init__` ✅ · `save_expense` ❌ (INSERT sin VALUES) · `find_by_period` ❌ · `find_with_participants` ❌

**Nota de firma:** la firma real de `save` es `save(expense, period_id, member_ids: dict[str, int]) -> int`.
No recibe `household_id` — recibe el dict `{name: id}` que WM tiene en `self.member_ids`.
El WM llama: `self.expense_repo.save(expense, self.period_id, self.member_ids)`.

**3.1** `save(expense: Expense, period_id: int, member_ids: dict[str, int]) -> int`

- `payer_id = member_ids[expense.member]`
- Inserta en `expenses`, obtiene el `id`
- Para cada nombre en `expense.participants`: `member_id = member_ids[name]` e inserta en `expense_participants`
- Devuelve el `expense_id`

**3.2** `find_by_period(period_id: int) -> list[dict]`

- SELECT de `expenses` filtrado por `period_id`

**3.3** `find_with_participants(period_id: int) -> list[dict]`

- JOIN entre `expenses`, `expense_participants` y `members`
- Cada elemento incluye `participants: list[str]`

**3.4** Inyectar en `WorkflowManager`: añade `expense_repo` opcional al constructor.
En `register_expense()`, si existe, llama a `save` tras registrar en el tracker.

**3.5** Tests en `tests/test_expense_repository.py` — misma estructura que los de `PeriodRepository`.

**3.6** `pytest -q --no-cov` → commit `feat: add ExpenseRepository with participants`.

---

## Bloque 4 — Migración `categories` + `CategoryRepository`

**4.1** Migración:

```sql
CREATE TABLE categories (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_shared BOOLEAN NOT NULL DEFAULT TRUE,
    type VARCHAR(20) NOT NULL CHECK (type IN ('normal', 'auto_calculated')),
    is_standard BOOLEAN NOT NULL DEFAULT FALSE,
    household_id INTEGER REFERENCES households(id)
);
CREATE UNIQUE INDEX uq_standard_categories ON categories (name) WHERE household_id IS NULL;
```

**4.2** `CategoryRepository` en `src/storage/category_repository.py`:

- `create(category: Category, household_id: int) -> int`
- `get_by_name(name: str, household_id: int) -> Category | None`
- `list_by_household(household_id: int) -> list[Category]`

**4.3** Inyectar en `WorkflowManager`. En `finish_registration()`, persistir las categorías estándar creadas.

**4.4** Tests + commit `feat: add CategoryRepository`.

---

## Bloque 5 — Migración `debt_entries` + `DebtRepository`

**5.1** Migración:

```sql
CREATE TABLE debt_entries (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES household_periods(id),
    member_id INTEGER NOT NULL REFERENCES members(id),
    amount_cents INTEGER NOT NULL,
    description VARCHAR(255) DEFAULT '',
    entry_date TIMESTAMP NOT NULL
);
```

**5.2** `DebtRepository` en `src/storage/debt_repository.py`:

- `save_payment(member_name: str, household_id: int, period_id: int, amount_cents: int, description: str, date) -> None`
- `find_by_period(period_id: int) -> list[dict]`

**5.3** Inyectar en `WorkflowManager.register_debt_payment()`.

**5.4** Tests + commit `feat: add DebtRepository`.

---

## Bloque 6 — Migraciones ahorro + `SavingRepository`

**6.1** Migraciones:

```sql
CREATE TABLE saving_entries (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES household_periods(id),
    member_id INTEGER NOT NULL REFERENCES members(id),
    amount_cents INTEGER NOT NULL,
    scope VARCHAR(10) NOT NULL CHECK (scope IN ('personal', 'shared')),
    entry_date TIMESTAMP NOT NULL
);

CREATE TABLE saving_buckets (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES households(id),
    name VARCHAR(100) NOT NULL,
    goal_cents INTEGER,
    scope VARCHAR(10) NOT NULL CHECK (scope IN ('personal', 'shared'))
);

CREATE TABLE bucket_entries (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bucket_id INTEGER NOT NULL REFERENCES saving_buckets(id),
    member_id INTEGER NOT NULL REFERENCES members(id),
    amount_cents INTEGER NOT NULL,
    entry_date TIMESTAMP NOT NULL
);
```

**6.2** `SavingRepository` en `src/storage/saving_repository.py`:

- `save_deposit(...)`, `save_withdrawal(...)`, `find_entries_by_period(...)`
- `create_bucket(...)`, `find_buckets_by_household(...)`, `save_bucket_entry(...)`

**6.3** Inyectar en WM en `register_savings_deposit()` y métodos de bucket.

**6.4** Tests + commit `feat: add SavingRepository`.

---

## Bloque 7 — `month_settlements` + `SettlementRepository`

**7.1** Migración:

```sql
CREATE TABLE month_settlements (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES household_periods(id),
    from_member_id INTEGER NOT NULL REFERENCES members(id),
    to_member_id INTEGER NOT NULL REFERENCES members(id),
    amount_cents INTEGER NOT NULL
);
```

**7.2** `SettlementRepository` en `src/storage/settlement_repository.py`:

- `save_snapshot(period_id: int, transfers: list[dict], household_id: int) -> None`
- `get_by_period(period_id: int) -> list[dict]`

**7.3** Inyectar en `WorkflowManager.finish_month()` — calcular settlement y persistirlo al cerrar.

**7.4** Tests + commit `feat: add SettlementRepository`.

---

## Bloque 8 — `income_entries` (dominio + persistencia)

**8.1** Nuevo modelo `src/models/income_entry.py`:

```python
@dataclass
class IncomeEntry:
    member: str
    amount_cents: int
    affects_distribution: bool
    period_id: int | None = None
```

**8.2** En `Household`:

- Añade `_income_entries: list[IncomeEntry] = []`
- Método `add_income_entry(member, amount_cents, affects_distribution)`
- Actualiza `get_total_incomes()`: suma `monthly_income` base + entradas con `affects_distribution=True`

**8.3** En `WorkflowManager`: añade `register_income_entry(member, amount_eur, affects_distribution)`.

**8.4** Migración:

```sql
CREATE TABLE income_entries (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES household_periods(id),
    member_id INTEGER NOT NULL REFERENCES members(id),
    amount_cents INTEGER NOT NULL,
    affects_distribution BOOLEAN NOT NULL DEFAULT TRUE,
    entry_date TIMESTAMP NOT NULL
);
```

**8.5** `IncomeEntryRepository` en `src/storage/income_entry_repository.py`:

- `save(member_name: str, household_id: int, period_id: int, amount_cents: int, affects_distribution: bool, date) -> None`
- `find_by_period(period_id: int) -> list[dict]`

**8.6** Tests de dominio + repositorio + commit `feat: add income_entries with affects_distribution`.

---

## Orden de ejecución

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
              ↑___↑___↑  (4, 5 y 6 son independientes entre sí)
```

El bloque 7 (settlement) depende de que el 3 (expenses) esté hecho.
Los bloques 4, 5 y 6 pueden hacerse en cualquier orden una vez terminado el 3.
El bloque 8 (income_entries) es independiente de todos — puedes hacerlo en cualquier momento.
