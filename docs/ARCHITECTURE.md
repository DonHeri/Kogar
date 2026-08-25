# ARQUITECTURA DEL PROYECTO KOGAR

## 📋 Visión General

**Kogar** es un sistema de gestión financiera compartida que permite a hogares con múltiples miembros:

1. Registrar miembros e ingresos
2. Planificar presupuestos por categorías
3. Distribuir gastos de forma justa según ingresos
4. Registrar y hacer seguimiento de gastos reales

**Filosofía:** Arquitectura orientada a fases con estado congelado y cálculos con precisión financiera (céntimos como enteros).

---

## 🔄 Sistema de Fases

El flujo del sistema está organizado en 4 fases secuenciales:

```
REGISTRATION → PLANNING → MONTH → CLOSING
    ✅            ✅        🚧       📋
```

### **Gestión de Estado por Fases**

- **REGISTRATION:** Datos mutables. Se pueden agregar/modificar miembros e ingresos.
- **PLANNING:** Datos de registro se congelan (`_registered_incomes`). Se configura presupuesto.
- **MONTH:** Datos de planificación se congelan (`_agreed_percentages`, `_agreed_contributions`). Se registran gastos.
- **CLOSING:** No implementado aún.

**Regla clave:** Al pasar de fase, los datos acordados se congelan para mantener consistencia durante las fases posteriores.

---

## 🏗️ Arquitectura de Módulos

```
src/
├── models/           # Entidades del dominio
│   ├── constants.py
│   ├── member.py
│   ├── household.py
│   ├── budget.py
│   ├── budget_category.py
│   ├── expense.py
│   ├── expense_tracker.py
│   ├── finance_calculator.py
│   ├── category_library.py
│   └── subcategory_library.py
├── utils/            # Utilidades de conversión
│   ├── currency.py
│   └── printer.py
├── workflow/         # Orquestación de fases
│   └── workflow_manager.py
├── cli/              # Interfaz de usuario (vacío - futuro)
├── storage/          # Persistencia (vacío - futuro)
└── exceptions/       # Excepciones custom (vacío - futuro)
```

---

## 📦 Clases y Relaciones

### **1️⃣ FASE REGISTRATION**

#### `Member` - Participante del hogar

**Responsabilidad:** Representa a una persona con su ingreso mensual.

**Atributos:**

- `name: str` - Nombre del miembro
- `monthly_income: int` - Ingreso mensual en céntimos

**Métodos:**

- `__init__(name: str)` - Valida nombre no vacío
- `add_incomes(income_cents: int)` - Acumula ingresos (céntimos)
- `_validate_name(name)` - Valida nombre no vacío
- `_validate_income(income_cents)` - Valida ingreso >= 0

**Relaciones:**

- Creado por `WorkflowManager.register_member()`
- Almacenado en `Household.members: Dict[str, Member]`

---

### **2️⃣ FASE PLANNING**

#### `Budget` - Orquestador de categorías

**Responsabilidad:** Gestiona colección de categorías de presupuesto.

**Atributos:**

- `categories: Dict[str, BudgetCategory]` - Diccionario de categorías activas

**Métodos de Inicialización:**

- `set_standard_categories()` - Crea categorías estándar: fijos, variables, deuda, ahorro

**Métodos de Gestión de Categorías:**

- `add_category(name: str)` - Agrega categoría normalizada
- `delete_budget_category(category: str)` - Elimina categoría sin gastos
- `get_categories_list() -> list[str]` - Lista categorías activas
- `get_category_budget(name: str) -> int` - Presupuesto de categoría (céntimos)

**Métodos de Presupuesto:**

- `set_budget(category: str, amount: float)` - Asigna presupuesto a categoría
- `get_total_budgeted() -> int` - Total presupuestado (céntimos)

**Métodos de Gastos:**

- `register_payment(category: str, member: str, amount: int)` - Registra pago
- `get_category_spent(name: str) -> int` - Total gastado en categoría
- `get_total_spent() -> int` - Total gastado global
- `get_category_remaining(name: str) -> int` - Presupuesto restante

**Validadores:**

- `_validate_active_category(name)` - Categoría no existe (para crear)
- `_validate_category_exists(name)` - Categoría existe (para modificar)
- `_validate_amount(amount)` - Monto >= 0
- `_validate_category_is_deletable(category)` - Sin gastos registrados

**Relaciones:**

- Inyectado en `Household.__init__(budget: Budget)`
- Usa `CategoryLibrary` para normalización
- Contiene múltiples `BudgetCategory`

---

#### `BudgetCategory` - Categoría individual

**Responsabilidad:** Gestiona presupuesto y pagos de una categoría específica.

**Atributos:**

- `name: str` - Nombre de la categoría
- `planned_amount: int` - Presupuesto planificado (céntimos)
- `spent: int` - Total gastado (céntimos)
- `member_contributions: Dict[str, int]` - Pagos por miembro (céntimos)

**Métodos:**

- `__init__(name: str, planned_amount: float)` - Crea categoría con presupuesto
- `register_payment(member_name: str, amount_cents: int)` - Registra pago
- `remaining() -> int` - Calcula presupuesto restante
- `member_pending(member_name: str, owed_amount: int) -> int` - Deuda pendiente de miembro
- `get_report() -> str` - Formato usuario-friendly

**Validadores:**

- `_validate_amount(amount)` - Presupuesto >= 0
- `_validate_payment(amount_cents)` - Pago > 0

**Relaciones:**

- Contenida en `Budget.categories`
- Recibe pagos desde `Expense`

---

#### `CategoryLibrary` - Biblioteca de categorías

**Responsabilidad:** Gestiona catálogo de categorías estándar y extendidas con normalización.

**Atributos de Clase:**

- `STANDARD_CATEGORIES: Dict[str, str]` - 4 categorías base: fijos, variables, deuda, ahorro
- `EXTENDED_CATEGORIES: Dict[str, str]` - 8 categorías adicionales: salud, transporte, ocio, etc.

**Métodos de Mutación:**

- `add_category(name: str)` - Agrega categoría a extendidas

**Métodos de Consulta:**

- `get_standards_categories() -> Dict[str, str]` - Solo estándar
- `get_all_suggestions() -> Dict[str, str]` - Estándar + extendidas
- `is_standard(name: str) -> bool` - Es categoría estándar
- `is_suggest(name: str) -> bool` - Está en extendidas
- `is_known(name: str) -> bool` - Existe (estándar o extendida)

**Normalización:**

- `normalize(text: str) -> str` - Convierte a minúsculas, quita espacios
- `find_similar(user_input: str) -> list[str]` - TODO: sugerencias por similitud

**Relaciones:**

- Usado por `Budget` para validación y normalización
- Stateless (solo métodos de clase)

---

#### `SubcategoryLibrary` - Subcategorías sugeridas

**Responsabilidad:** Proporciona subcategorías granulares por categoría.

**Atributos de Clase:**

- `SUGGESTIONS: Dict[str, list[str]]` - Mapeo categoría → lista de subcategorías

**Métodos:**

- `get_suggestions_for(category: str) -> list[str]` - Subcategorías de una categoría

**Relaciones:**

- Datos de referencia, no usado activamente en v0.1
- Futuro: desglose detallado de gastos

---

#### `FinanceCalculator` - Motor de cálculos financieros

**Responsabilidad:** Realiza cálculos matemáticos sin estado (stateless).

**Métodos de Agregación:**

- `sum_values(values: list[int]) -> int` - Suma valores

**Métodos de Porcentajes:**

- `calculate_percentage_based_on_weight_of_income(income_map: Dict[str, int]) -> Dict[str, int]`
  - Calcula % proporcional a ingresos
  - Retorna basis points (5357 = 53.57%)
  - Garantiza suma exacta 10000
  - Descuadre al miembro con mayor ingreso

- `calculate_equal_percentage(members: Dict[str, int]) -> Dict[str, int]`
  - Calcula % equitativo (50/50, 33/33/33)
  - Descuadre al miembro con mayor ingreso

**Métodos de Contribuciones:**

- `calculate_contribution(percentages: Dict[str, int], budget_amount: int) -> Dict[str, int]`
  - Aplica % sobre presupuesto
  - Retorna contribución en céntimos
  - Garantiza suma exacta sin pérdida
  - Descuadre al miembro con mayor porcentaje

**Relaciones:**

- Usado por `Household` para cálculos de distribución
- Todos los métodos estáticos

---

### **3️⃣ FASE MONTH**

#### `Expense` - Gasto individual

**Responsabilidad:** Representa un pago realizado por un miembro.

**Atributos:**

- `member: str` - Quién pagó
- `category: str` - Categoría del gasto
- `description: str` - Descripción opcional
- `_amount_cents: int` - Monto en céntimos (privado)
- `_date: datetime` - Fecha del gasto (privado)

**Properties (read-only):**

- `amount -> int` - Monto del gasto
- `date -> datetime` - Fecha del gasto

**Métodos:**

- `__init__(member, category, amount_cents, description="")` - Constructor con validaciones
- `is_same_month(other_date: datetime) -> bool` - Compara mes/año
- `is_same_year(other_date: datetime) -> bool` - Compara año

**Validadores:**

- `_validate_non_empty_string(value, field_name)` - String no vacío
- `_validate_positive_amount(value, field_name)` - Monto > 0

**Relaciones:**

- Creado por `WorkflowManager.register_expense()`
- Almacenado en `ExpenseTracker.expenses`
- Usado por `Household` para actualizar `BudgetCategory`

---

#### `ExpenseTracker` - Gestor de colección de gastos

**Responsabilidad:** Almacena y filtra gastos. NO valida (validación en Household).

**Atributos:**

- `expenses: list[Expense]` - Lista de gastos

**Métodos de Almacenamiento:**

- `add_expense(expense: Expense)` - Agrega gasto
- `get_all_expenses() -> list[Expense]` - Todos los gastos

**Métodos de Filtrado:**

- `get_expenses_by_category(category: str) -> list[Expense]` - Por categoría
- `get_expenses_by_member(member: str) -> list[Expense]` - Por miembro

**Métodos de Agregación:**

- `get_total_spent() -> int` - Total gastado (céntimos)
- `get_total_spent_by_category(category: str) -> int` - Total por categoría
- `get_total_spent_by_member(member: str) -> int` - Total por miembro
- `get_category_breakdown() -> Dict[str, int]` - Desglose por categoría
- `get_member_breakdown() -> Dict[str, int]` - Desglose por miembro

**Diseño:**

- Un tracker = un mes
- Siguiente mes = nuevo tracker
- Histórico multi-mes para v0.4

**Relaciones:**

- Inyectado en `Household.__init__(expense_tracker: ExpenseTracker)`
- Recibe gastos desde `Household.register_expense()`

---

### **4️⃣ ORQUESTADOR CENTRAL**

#### `Household` - Coordinador del hogar

**Responsabilidad:** Orquesta miembros, presupuesto, distribución y gastos. Hub central del dominio.

**Atributos:**

- `members: Dict[str, Member]` - Miembros del hogar
- `budget: Budget` - Presupuesto compartido
- `expense_tracker: ExpenseTracker` - Tracking de gastos
- `method: MetodoReparto` - Método de distribución global
- `_custom_splits: Dict[str, int]` - % personalizados (si método CUSTOM)
- `_registered_incomes: Dict[str, int]` - Ingresos congelados (≥ PLANNING)
- `_agreed_percentages: Dict[str, int]` - % congelados (≥ MONTH)
- `_agreed_contributions: Dict` - Contribuciones congeladas (≥ MONTH)

**Constructor:**

- `__init__(budget: Budget, expense_tracker: ExpenseTracker, method: MetodoReparto)`

#### **Métodos REGISTRATION:**

**Gestión de Miembros:**

- `register_member(member: Member)` - Registra miembro
- `set_member_income(name: str, amount_cents: int)` - Establece ingreso

#### **Métodos PLANNING:**

**Gestión de Categorías:**

- `add_category(name: str)` - Agrega categoría
- `remove_category(name: str)` - Elimina categoría
- `set_standard_categories()` - Crea 4 categorías base
- `get_active_categories() -> list[str]` - Lista categorías
- `get_category_budget(name: str) -> int` - Presupuesto de categoría

**Asignación de Presupuesto:**

- `set_budget_for_category(category: str, amount: float)` - Asigna presupuesto

**Configuración de Distribución:**

- `assign_distribution_method(method: MetodoReparto)` - Establece método
- `set_custom_splits(splits: Dict[str, float])` - Define % personalizados (0-100)

#### **Métodos de Congelación de Estado:**

- `freeze_registration_state()` - Congela ingresos al pasar a PLANNING
- `freeze_planning_state()` - Congela % y contribuciones al pasar a MONTH

#### **Métodos MONTH:**

**Registro de Gastos:**

- `register_expense(expense: Expense)` - Registra gasto (valida miembro y categoría)

#### **Queries - Estado Congelado:**

- `get_registered_incomes() -> Dict[str, int]` - Ingresos congelados (≥ PLANNING)
- `get_agreed_percentages() -> Dict[str, int]` - % congelados (≥ MONTH)
- `get_agreed_contributions() -> Dict` - Contribuciones congeladas (≥ MONTH)

#### **Queries - REGISTRATION:**

- `get_registration_summary() -> dict`
  - Retorna: members, member_incomes, total_household_income

#### **Queries - PLANNING:**

- `get_loose_money() -> int` - Ingresos - total presupuestado
- `preview_budget_contribution_summary(method: MetodoReparto) -> dict`
  - Simula contribuciones con método inyectado
  - Por categoría: planned, contributions, total_assigned
- `get_current_contributions() -> dict` - Usa método configurado (self.method)
- `get_total_budgeted() -> int` - Total presupuestado
- `get_planning_summary() -> dict`
  - Retorna todo: members, incomes, method, percentages, categories, budget, loose_money, contributions_preview

#### **Queries - MONTH:**

- `get_total_spent() -> int` - Total gastado
- `get_month_summary() -> dict`
  - Retorna: total (budgeted, spent, remaining), by_category (budget, spent, remaining), loose_money

#### **Helpers Internos:**

- `get_total_incomes() -> int` - Usa datos congelados si disponibles, sino calcula
- `get_percentages_by_method(method: MetodoReparto) -> Dict[str, int]`
  - PROPORTIONAL: llama a `FinanceCalculator.calculate_percentage_based_on_weight_of_income()`
  - EQUAL: llama a `FinanceCalculator.calculate_equal_percentage()`
  - CUSTOM: retorna `self._custom_splits`
- `calculate_member_contribution_for_category(percentages, budget_amount)`
  - Delega a `FinanceCalculator.calculate_contribution()`

**Validadores:**

- `_validate_has_members()` - Hay al menos 1 miembro
- `_validate_total_incomes_positive()` - Ingresos totales > 0
- `_validate_all_members_have_split(splits)` - Todos tienen % asignado
- `_validate_category_exist(category)` - Categoría existe
- `_validate_member_exist(member)` - Miembro existe

**Relaciones:**

- Depende de: `Member`, `Budget`, `ExpenseTracker`, `Expense`, `FinanceCalculator`
- Usado por: `WorkflowManager`

---

### **5️⃣ WORKFLOW - Orquestación de Fases**

#### `WorkflowManager` - Gestor de fases y conversiones

**Responsabilidad:**

1. Orquesta transiciones entre fases
2. Capa de conversión euros ↔ céntimos (única interfaz con usuario)
3. Valida operaciones permitidas por fase

**Atributos:**

- `household: Household` - Instancia del hogar
- `current_phase: Phase` - Fase actual
- `_completed_phases: set[Phase]` - Fases ya completadas

**Constructor:**

- `__init__(household: Household)` - Inicializa en REGISTRATION

#### **Métodos REGISTRATION:**

- `register_member(name: str)` - Crea Member y registra
- `set_incomes(name: str, amount_eur: float)` - Convierte a céntimos y establece
- `finish_registration()` - Valida, congela ingresos, → PLANNING
  - Valida: al menos 1 miembro, ingresos > 0
  - Llama a `household.freeze_registration_state()`

#### **Métodos PLANNING:**

**Configuración de Distribución:**

- `assign_distribution_method(method: MetodoReparto)` - Establece método
- `set_custom_splits(splits: Dict[str, float])` - Define % personalizados

**Gestión de Categorías:**

- `add_category(name: str)` - Agrega categoría
- `set_standard_categories()` - Crea categorías base
- `remove_category(name: str)` - Elimina categoría

**Asignación de Presupuesto:**

- `set_budget_for_category(category: str, amount: float)` - Asigna presupuesto

**Queries de Contribuciones:**

- `preview_budget_contribution_summary(method: MetodoReparto)` - Preview con método inyectado
- `get_current_contributions()` - Contribuciones con método actual

**Finalización:**

- `finish_planning()` - Valida, congela acuerdos, → MONTH
  - Valida: al menos 1 categoría, presupuesto > 0
  - Llama a `household.freeze_planning_state()`

#### **Métodos MONTH:**

- `register_expense(member: str, category: str, amount_euros: float, desc="")`
  - Convierte a céntimos, crea Expense, registra

#### **Queries Generales (independientes de fase):**

- `get_registered_members() -> list[str]` - Lista miembros
- `get_member_income(name: str) -> int` - Ingreso de miembro (céntimos)
- `get_total_incomes() -> int` - Ingresos totales (céntimos)
- `get_active_categories() -> list[str]` - Categorías activas

#### **Queries por Fase (accesibles desde fase actual o posteriores):**

- `get_registration_summary()` - ≥ REGISTRATION
- `get_planning_summary()` - ≥ PLANNING
- `get_month_summary()` - ≥ MONTH
- `get_registered_incomes()` - ≥ PLANNING
- `get_agreed_percentages()` - ≥ MONTH
- `get_agreed_contributions()` - ≥ MONTH

#### **Validadores:**

- `validate_phase(required_phase: Phase)` - Fase actual == requerida (estricto)
- `validate_phase_accessible(required_phase: Phase)` - Fase actual o ya completada (permisivo)

**Diseño:**

- Modificaciones: validación estricta (`validate_phase`)
- Consultas/summaries: validación permisiva (`validate_phase_accessible`)

**Relaciones:**

- Único punto de entrada desde CLI/UI
- Orquesta `Household` completo
- Crea instancias de `Member`, `Expense`

---

### **6️⃣ CONSTANTES Y ENUMERACIONES**

#### `constants.py`

**Phase - Fases del workflow:**

```python
class Phase(Enum):
    REGISTRATION = "registro"
    PLANNING = "planificación"
    MONTH = "transcurso_mes"
    CLOSING = "cierre"
```

**MetodoReparto - Métodos de distribución:**

```python
class MetodoReparto(Enum):
    PROPORTIONAL = "proporcional"  # Según % ingresos
    EQUAL = "igual"                # Equitativo (50/50)
    CUSTOM = "custom"              # % definidos por usuario
```

---

### **7️⃣ UTILIDADES**

#### `utils/currency.py` - Conversiones financieras

**Conversiones de Moneda:**

- `to_cents(euros: float) -> int` - Usuario → interno (3.14 → 314)
- `to_euros(cents: int) -> str` - Interno → usuario (314 → "3.14€")

**Conversiones de Porcentaje:**

- `to_percentage_basis(decimal_percentage: float) -> int` - (53.57 → 5357)
- `format_percentage(basis_points: int) -> str` - (5357 → "53.57%")

**Filosofía:**

- Almacenamiento interno: enteros (céntimos, basis points)
- Evita errores de redondeo de floats
- Conversiones solo en fronteras (entrada/salida)

---

## 🔄 Flujo de Datos por Fase

### **REGISTRATION → PLANNING**

```
Usuario → WorkflowManager
├─ register_member("Amanda")
│  └─ Crea Member → Household.register_member()
│     └─ Almacena en Household.members
├─ set_incomes("Amanda", 6000.00)
│  └─ Convierte a céntimos (600000)
│     └─ Household.set_member_income()
│        └─ Member.add_incomes()
└─ finish_registration()
   ├─ Valida: miembros y ingresos
   ├─ Household.freeze_registration_state()
   │  └─ _registered_incomes = {miembro: income}
   └─ current_phase = Phase.PLANNING
```

### **PLANNING → MONTH**

```
Usuario → WorkflowManager
├─ set_standard_categories()
│  └─ Budget.set_standard_categories()
│     └─ Crea 4 BudgetCategory (fijos, variables, deuda, ahorro)
├─ set_budget_for_category("fijos", 5000.00)
│  └─ Budget.set_budget()
│     └─ BudgetCategory.planned_amount = 500000 (céntimos)
├─ assign_distribution_method(MetodoReparto.PROPORTIONAL)
│  └─ Household.method = PROPORTIONAL
├─ get_planning_summary()
│  └─ Household.get_planning_summary()
│     ├─ get_percentages_by_method() → FinanceCalculator
│     │  └─ calculate_percentage_based_on_weight_of_income()
│     └─ get_current_contributions()
│        └─ FinanceCalculator.calculate_contribution()
└─ finish_planning()
   ├─ Valida: categorías y presupuestos
   ├─ Household.freeze_planning_state()
   │  ├─ _agreed_percentages = get_percentages_by_method()
   │  └─ _agreed_contributions = get_current_contributions()
   └─ current_phase = Phase.MONTH
```

### **MONTH - Registro de Gastos**

```
Usuario → WorkflowManager
└─ register_expense("Amanda", "fijos", 250.00, "Alquiler")
   ├─ Convierte a céntimos (25000)
   ├─ Crea Expense(member, category, amount_cents, desc)
   └─ Household.register_expense(expense)
      ├─ Valida miembro y categoría existen
      ├─ ExpenseTracker.add_expense(expense)
      │  └─ Almacena en expenses[]
      └─ Budget.register_payment(category, member, amount)
         └─ BudgetCategory.register_payment()
            ├─ member_contributions[member] += amount
            └─ spent += amount
```

---

## 🧩 Diagrama de Dependencias

```
WorkflowManager
    │
    ├──> Household (hub central)
    │       │
    │       ├──> Member (1:N)
    │       │      └── monthly_income: int
    │       │
    │       ├──> Budget (1:1)
    │       │      │
    │       │      ├──> CategoryLibrary (stateless)
    │       │      │
    │       │      └──> BudgetCategory (1:N)
    │       │             ├── planned_amount: int
    │       │             ├── spent: int
    │       │             └── member_contributions: Dict
    │       │
    │       ├──> ExpenseTracker (1:1)
    │       │      │
    │       │      └──> Expense (1:N)
    │       │             ├── member: str
    │       │             ├── category: str
    │       │             ├── amount: int
    │       │             └── date: datetime
    │       │
    │       └──> FinanceCalculator (stateless)
    │              ├── calculate_percentage_based_on_weight_of_income()
    │              ├── calculate_equal_percentage()
    │              └── calculate_contribution()
    │
    └──> utils/currency (stateless)
           ├── to_cents()
           ├── to_euros()
           ├── to_percentage_basis()
           └── format_percentage()

Bibliotecas (stateless):
├─ CategoryLibrary
│    ├── STANDARD_CATEGORIES
│    └── EXTENDED_CATEGORIES
└─ SubcategoryLibrary
     └── SUGGESTIONS
```

---

## 🎯 Patrones de Diseño Aplicados

### **1. Dependency Injection**

- `Household` recibe `Budget` y `ExpenseTracker` en constructor
- Facilita testing con mocks
- Desacopla creación de uso

### **2. State Freezing**

- Datos acordados se congelan al cambiar fase
- Previene modificación inconsistente
- `_registered_incomes`, `_agreed_percentages`, `_agreed_contributions`

### **3. Single Responsibility**

- `WorkflowManager`: orquestación + conversiones
- `Household`: lógica de dominio
- `FinanceCalculator`: cálculos matemáticos
- `ExpenseTracker`: almacenamiento + filtrado

### **4. Stateless Utilities**

- `FinanceCalculator`: métodos estáticos
- `CategoryLibrary`: métodos de clase
- `currency`: funciones puras
- Sin efectos secundarios, fácil testeo

### **5. Value Objects (Immutable Properties)**

- `Expense.amount` y `Expense.date` son read-only
- Previene mutación accidental

### **6. Library Pattern**

- `CategoryLibrary` y `SubcategoryLibrary`
- Datos de referencia centralizados
- Normalización consistente

---

## 🔐 Principios de Precisión Financiera

### **Almacenamiento en Céntimos (Enteros)**

**Problema:** Floats causan errores de redondeo

```python
# ❌ MAL
0.1 + 0.2 = 0.30000000000000004
```

**Solución:** Todo en enteros internamente

```python
# ✅ BIEN
10 + 20 = 30  # (0.10€ + 0.20€ = 0.30€)
```

### **Distribución Sin Pérdida**

Al distribuir presupuesto, la suma debe cuadrar exactamente:

**Ejemplo:** 100€ entre 3 personas (33.33% cada uno)

```python
# División entera primero
100 * 3333 // 10000 = 33  (por 3 = 99)

# Sobra 1 céntimo → al de mayor %
# [33, 33, 34] = 100 ✅
```

**Implementación:** `FinanceCalculator.calculate_contribution()`

- División entera (`//`)
- Resto al de mayor porcentaje
- Validación: `sum(contributions) == budget_amount`

---

## 📊 Estado Actual del Proyecto

### ✅ **Completado (v0.1)**

- Sistema de fases REGISTRATION → PLANNING
- Gestión de miembros e ingresos
- Presupuesto por categorías
- 3 métodos de distribución: PROPORTIONAL, EQUAL, CUSTOM
- Cálculos financieros con precisión de céntimos
- Congelación de estado entre fases
- Testing completo del dominio

### 🚧 **En Desarrollo (v0.2)**

- Fase MONTH (tracking de gastos)
- `Expense` y `ExpenseTracker` implementados
- Integración parcial en `Household`
- Resumen mensual básico

### 📋 **Pendiente**

- Fase CLOSING (cierre de mes, liquidaciones)
- Persistencia (storage)
- CLI/UI pulido
- Histórico multi-mes
- Análisis y reportes

---

## 🧪 Testing

**Cobertura:** ~95% del código del dominio

**Archivos de Test:**

- `test_member.py` - Validación de miembros
- `test_household.py` - Lógica central
- `test_budget.py` - Gestión de presupuestos
- `test_calculator.py` - Precisión matemática
- `test_expense.py` - Validación de gastos
- `test_expense_tracker.py` - Filtros y agregaciones
- `test_workflow_manager.py` - Transiciones de fase
- `test_utils_currency.py` - Conversiones
- `test_category_library.py` - Normalización

**Filosofía:**

- Tests unitarios por clase
- Validación de precisión financiera
- Testing de transiciones de fase
- Validación de restricciones de dominio

---

## 🚀 Flujo de Usuario Completo (v0.1)

```python
# 1. SETUP
from src.workflow.workflow_manager import WorkflowManager
from src.models.household import Household
from src.models.budget import Budget
from src.models.expense_tracker import ExpenseTracker
from src.models.constants import MetodoReparto

budget = Budget()
tracker = ExpenseTracker()
household = Household(budget, tracker)
workflow = WorkflowManager(household)

# 2. REGISTRATION
workflow.register_member("Amanda")
workflow.register_member("Heri")
workflow.set_incomes("Amanda", 6000)  # 6000€
workflow.set_incomes("Heri", 4000)    # 4000€
workflow.finish_registration()        # → PLANNING

# 3. PLANNING
workflow.set_standard_categories()
workflow.set_budget_for_category("fijos", 5000)
workflow.set_budget_for_category("variables", 2000)
workflow.assign_distribution_method(MetodoReparto.PROPORTIONAL)

summary = workflow.get_planning_summary()
# {
#   "total_household_income": 1000000,  # 10000€ en céntimos
#   "total_budgeted": 700000,           # 7000€
#   "loose_money": 300000,              # 3000€
#   "distribution_percentages": {
#     "Amanda": 6000,  # 60.00%
#     "Heri": 4000     # 40.00%
#   },
#   "contributions_preview": {
#     "fijos": {
#       "planned": 500000,
#       "contributions": {"Amanda": 300000, "Heri": 200000}
#     },
#     "variables": {
#       "planned": 200000,
#       "contributions": {"Amanda": 120000, "Heri": 80000}
#     }
#   }
# }

workflow.finish_planning()  # → MONTH

# 4. MONTH (en desarrollo)
workflow.register_expense("Amanda", "fijos", 250.00, "Alquiler")
workflow.register_expense("Heri", "variables", 85.50, "Supermercado")

month_summary = workflow.get_month_summary()
# {
#   "total": {
#     "total_budgeted": 700000,
#     "total_spent": 33550,
#     "total_remaining": 666450
#   },
#   "by_category": {
#     "fijos": {
#       "budget": 500000,
#       "spent": 25000,
#       "remaining": 475000
#     },
#     ...
#   }
# }
```

---

## 📚 Convenciones del Proyecto

### **Naming**

- Clases: `PascalCase`
- Métodos/funciones: `snake_case`
- Constantes: `UPPER_SNAKE_CASE`
- Privados: prefijo `_` (ej: `_validate_member`)

### **Validaciones**

- Métodos de validación prefijo `_validate_`
- Lanzan `ValueError` con mensaje descriptivo
- Validaciones en capa de dominio, no en trackers

### **Conversiones**

- Entrada usuario: euros (float)
- Dominio interno: céntimos (int)
- Salida usuario: string formateado ("3.14€")
- Conversión única en `WorkflowManager`

### **Documentación**

- Docstrings en métodos públicos
- Type hints en firmas
- Comentarios de sección: `# ====== SECTION ======`

---

## 🎓 Decisiones Arquitectónicas Clave

1. **Fases explícitas con validación:** Previene operaciones en fase incorrecta
2. **Estado congelado:** Datos acordados inmutables tras transición
3. **Céntimos como enteros:** Precisión financiera sin floats
4. **Inyección de dependencias:** Testing y desacoplamiento
5. **Separación queries/commands:** Métodos estrictos vs permisivos
6. **Normalización centralizada:** `CategoryLibrary` única fuente de verdad
7. **Calculadora stateless:** Reutilizable, testeable, sin efectos secundarios
8. **Un tracker por mes:** Simplicidad, histórico en v0.4

---

## 🔮 Evolución Futura

### **v0.3 - Distribución Flexible**

- Método de reparto por categoría (no global)
- Ejemplo: fijos PROPORTIONAL, ahorro CUSTOM

### **v0.4 - Persistencia**

- SQLite para datos
- Histórico multi-mes
- Repositorios con Protocol

### **v0.5 - Cierre y Liquidación**

- Fase CLOSING completa
- Cálculo de deudas finales
- Transferencias de ajuste

### **v1.0 - UI Completa**

- CLI estructurado
- Web UI (Streamlit/Flask)
- Exportación de reportes

---

**Documento generado:** 2026-03-06  
**Versión del proyecto:** v0.1 (REGISTRATION + PLANNING completas)  
**Fase actual:** v0.2 en desarrollo (MONTH)
