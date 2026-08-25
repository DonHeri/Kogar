# 🎓 Mejoras SOLID Futuras - Explicación Detallada

> **Fecha:** 03-03-2026  
> **Contexto:** Análisis de mejoras arquitecturales identificadas para v0.3+  
> **Filosofía:** Pragmatismo sobre perfeccionismo - refactoriza cuando sea necesario, no "por si acaso"

---

## 📐 Filosofía General: "Rule of Three"

**No refactorices hasta que veas el mismo problema 3 veces:**
1. Primera vez: Escribe directo
2. Segunda vez: "Hmm, se parece..."
3. Tercera vez: **Ahora sí, refactoriza**

### ⚖️ Balance pragmático

| Acción | Cuándo |
|--------|--------|
| ✅ **Hazlo ahora** | Inyección de dependencias (ya implementado) |
| ⚠️ **Prepárate** | Mantén clases <250 líneas, documenta decisiones |
| ❌ **No lo hagas** | Abstracciones "por si acaso" sin caso de uso real |

---

## 1️⃣ Household - Refactorizar si crece (v0.3+)

### 📊 Situación actual

Household gestiona múltiples responsabilidades:

```python
class Household:
    # 1. Gestión de miembros
    def register_member(self, member: Member)
    def set_member_income(self, name: str, amount: float)
    
    # 2. Delegación a Budget
    def add_category(self, name: str)
    def set_budget_for_category(self, category: str, amount: float)
    
    # 3. CÁLCULOS DE DISTRIBUCIÓN (lo pesado)
    def get_percentages_by_method(self, method: MetodoReparto)  # 20+ líneas
    def calculate_member_contribution_for_category(...)
    def get_budget_contribution_summary(...)
    
    # 4. Generación de reportes
    def get_planning_summary(self)
```
### 🔧 Refactorización propuesta: Extraer BudgetDistributionService

```python
# src/models/budget_distribution_service.py
class BudgetDistributionService:
    """Servicio que calcula cómo distribuir presupuestos entre miembros"""
    
    def __init__(self, members: dict[str, Member], method: MetodoReparto):
        self.members = members
        self.method = method
        self._custom_splits = {}
    
    def get_percentages(self) -> dict[str, int]:
        """Calcula porcentajes según método configurado"""
        income_map = {name: m.monthly_income for name, m in self.members.items()}
        
        match self.method:
            case MetodoReparto.PROPORTIONAL:
                return FinanceCalculator.calculate_percentage_based_on_weight_of_income(income_map)
            case MetodoReparto.EQUAL:
                return FinanceCalculator.calculate_equal_percentage(income_map)
            case MetodoReparto.CUSTOM:
                return self._custom_splits
    
    def calculate_contributions_for_budget(self, budget: Budget) -> dict:
        """Calcula contribuciones de todos para todas las categorías"""
        percentages = self.get_percentages()
        summary = {}
        
        for cat_name, category in budget.categories.items():
            contributions = FinanceCalculator.calculate_contribution(
                percentages, category.planned_amount
            )
            summary[cat_name] = {
                "planned": category.planned_amount,
                "contributions": contributions,
                "total_assigned": sum(contributions.values()),
            }
        
        return summary
```

**Household simplificado:**

```python
class Household:
    def __init__(self, budget: Budget, expense_tracker: ExpenseTracker, method: MetodoReparto):
        self.members: Dict[str, Member] = {}
        self.budget = budget
        self.expense_tracker = expense_tracker
        self.distribution_service = BudgetDistributionService(self.members, method)
    
    def get_planning_summary(self) -> dict:
        # Solo coordinación, no cálculos pesados
        contributions = self.distribution_service.calculate_contributions_for_budget(self.budget)
        return {
            "members": list(self.members.keys()),
            "contributions_preview": contributions,
            # ...
        }
```

### ✅ Ventajas

1. **Single Responsibility:** Household coordina, DistributionService calcula
2. **Testeable:** Cálculos de distribución se testean independientemente
3. **Extensible:** Añadir métodos no hincha Household
4. **Reutilizable:** Usar DistributionService en reportes, simulaciones

### ❌ Por qué NO ahora

- Household ~200 líneas (manejable)
- Solo 3 métodos simples de distribución
- Código actual legible
- Añadir capa adicional = overengineering en v0.2

### 📚 Principio SOLID aplicado

**Single Responsibility Principle (SRP):**
- Una clase debe tener una única razón para cambiar
- Household cambiaría por: miembros, presupuestos, O cálculos de distribución
- Separar distribución reduce razones de cambio

---

## 2️⃣ MetodoReparto - Strategy Pattern (v0.3+)

### 📊 Situación actual

```python
def get_percentages_by_method(self, method: MetodoReparto):
    income_map = {name: m.monthly_income for name, m in self.members.items()}
    
    match method:
        case MetodoReparto.PROPORTIONAL:
            return FinanceCalculator.calculate_percentage_based_on_weight_of_income(income_map)
        case MetodoReparto.EQUAL:
            return FinanceCalculator.calculate_equal_percentage(income_map)
        case MetodoReparto.CUSTOM:
            return self._custom_splits
```

**Funciona bien para 3 métodos simples**, pero limitado si crece.

### 🎯 Triggers para Strategy Pattern

| Indicador | Umbral | Estado actual |
|-----------|--------|---------------|
| Número de métodos | >5 | 3 ✅ |
| Líneas por método | >20 | 2-5 ✅ |
| Configuración por método | Requerida | No ✅ |
| Métodos custom por usuario | Habilitado | No ✅ |

**Escenarios futuros que justificarían el patrón:**
- `WEIGHTED`: Ponderado por horas trabajadas
- `TIERED`: Por tramos (primeros 1000€ igual, resto proporcional)
- `CAP_PROPORTIONAL`: Proporcional con tope máximo de X%
- `BY_CATEGORY`: Método diferente por categoría

### 🔧 Implementación con Strategy Pattern

```python
# src/models/distribution_strategies.py
from typing import Protocol

class DistributionStrategy(Protocol):
    """Contrato para estrategias de distribución"""
    def calculate(self, income_map: dict[str, int]) -> dict[str, int]:
        """Calcula porcentajes de distribución"""
        ...

# ===== IMPLEMENTACIONES =====

class ProportionalDistribution:
    """Reparto proporcional a ingresos"""
    
    def calculate(self, income_map: dict[str, int]) -> dict[str, int]:
        return FinanceCalculator.calculate_percentage_based_on_weight_of_income(income_map)


class EqualDistribution:
    """Reparto equitativo 50/50"""
    
    def calculate(self, income_map: dict[str, int]) -> dict[str, int]:
        return FinanceCalculator.calculate_equal_percentage(income_map)


class CustomDistribution:
    """Reparto personalizado por usuario"""
    
    def __init__(self, custom_splits: dict[str, int]):
        self.custom_splits = custom_splits
    
    def calculate(self, income_map: dict[str, int]) -> dict[str, int]:
        return self.custom_splits


class CappedProportionalDistribution:
    """Proporcional con tope máximo (ejemplo futuro)"""
    
    def __init__(self, max_percentage: float = 60.0):
        self.max_cap = to_percentage_basis(max_percentage)
    
    def calculate(self, income_map: dict[str, int]) -> dict[str, int]:
        base = FinanceCalculator.calculate_percentage_based_on_weight_of_income(income_map)
        
        # Aplicar cap: nadie paga más de 60%
        for member, pct in base.items():
            if pct > self.max_cap:
                base[member] = self.max_cap
        
        # Rebalancear diferencia entre otros miembros...
        return base
```

**Uso polimórfico:**

```python
class Household:
    def __init__(self, budget, expense_tracker, distribution_strategy: DistributionStrategy):
        self.strategy = distribution_strategy
    
    def get_percentages(self) -> dict[str, int]:
        income_map = {name: m.monthly_income for name, m in self.members.items()}
        return self.strategy.calculate(income_map)


# Uso:
strategy = ProportionalDistribution()
household = Household(budget, tracker, strategy)

# Cambiar dinámicamente:
household.strategy = CappedProportionalDistribution(max_percentage=65)
```

### ✅ Ventajas

1. **Open/Closed Principle:** Añades estrategias SIN modificar Household
2. **Testeable:** Cada estrategia se testea independientemente
3. **Flexible:** Cambio de estrategia en runtime
4. **Extensible:** Usuarios pueden crear estrategias custom

### ❌ Por qué NO ahora

- Solo 3 métodos con 2-5 líneas cada uno
- `match/case` es pythónico y claro para casos simples
- Strategy requiere 5+ archivos para 15 líneas de código
- **YAGNI (You Aren't Gonna Need It):** No compliques antes de tiempo

---

## 3️⃣ BudgetCategory - Separar tracking (v0.4+)

### 📊 Situación actual

```python
class BudgetCategory:
    def __init__(self, name: str, planned_amount: float):
        # RESPONSABILIDAD 1: Presupuesto planificado
        self.name = name
        self.planned_amount = to_cents(planned_amount)
        
        # RESPONSABILIDAD 2: Tracking de gastos reales
        self.spent = 0
        self.member_contributions = {}
    
    def register_payment(self, member_name: str, amount: float):
        """Actualiza spent y contributions"""
        cents = to_cents(amount)
        if member_name not in self.member_contributions:
            self.member_contributions[member_name] = 0
        self.member_contributions[member_name] += cents
        self.spent += cents
    
    def remaining(self) -> int:
        return self.planned_amount - self.spent
```

### 🔧 Separación propuesta

```python
# src/models/budget_category.py
class BudgetCategory:
    """Representa el presupuesto PLANIFICADO de una categoría"""
    
    def __init__(self, name: str, planned_amount: float):
        self.name = name
        self.planned_amount = to_cents(planned_amount)
    
    def update_planned_amount(self, new_amount: float):
        """Actualiza presupuesto planificado"""
        self.planned_amount = to_cents(new_amount)


# src/models/category_expense_tracker.py
class CategoryExpenseTracker:
    """Trackea gastos REALES de una categoría específica"""
    
    def __init__(self, category_name: str):
        self.category_name = category_name
        self.spent = 0
        self.member_contributions = {}
        self.payment_history = []  # Nuevo: historial detallado
    
    def register_payment(self, member_name: str, amount: float, date: datetime):
        """Registra un pago"""
        cents = to_cents(amount)
        
        # Actualizar totales
        if member_name not in self.member_contributions:
            self.member_contributions[member_name] = 0
        self.member_contributions[member_name] += cents
        self.spent += cents
        
        # Guardar historial
        self.payment_history.append({
            "member": member_name,
            "amount": cents,
            "date": date
        })
    
    def remaining(self, planned_amount: int) -> int:
        """Calcula restante contra presupuesto"""
        return planned_amount - self.spent
    
    def get_daily_average(self) -> float:
        """Calcula gasto promedio diario"""
        if not self.payment_history:
            return 0.0
        
        days = (datetime.now() - self.payment_history[0]["date"]).days
        return self.spent / max(days, 1)
    
    def get_spending_trend(self) -> str:
        """Analiza tendencia: 'aumentando' | 'estable' | 'disminuyendo'"""
        # Comparar primera y segunda mitad del mes...
        pass
    
    def is_over_budget(self, planned_amount: int, threshold: float = 0.8) -> bool:
        """Verifica si se superó X% del presupuesto"""
        return self.spent >= (planned_amount * threshold)
```

**Budget coordina ambos:**

```python
class Budget:
    def __init__(self):
        self.categories: dict[str, BudgetCategory] = {}
        self.expense_trackers: dict[str, CategoryExpenseTracker] = {}


# Household genera reportes combinados:
def get_category_summary(self, category: str):
    planned = self.budget.categories[category]
    tracker = self.budget.expense_trackers[category]
    
    return {
        "name": category,
        "planned": planned.planned_amount,
        "spent": tracker.spent,
        "remaining": tracker.remaining(planned.planned_amount),
        "daily_avg": tracker.get_daily_average(),
        "trend": tracker.get_spending_trend(),
        "contributions": tracker.member_contributions,
        "alert": tracker.is_over_budget(planned.planned_amount)
    }
```

### ✅ Ventajas

1. **Interface Segregation:** Clientes que solo consultan presupuesto no necesitan tracking
2. **Single Responsibility:** Una clase planning, otra ejecución
3. **Extensible:** Añadir estadísticas no afecta presupuesto planificado
4. **Testeable:** Planning y tracking se testean por separado

### ❌ Por qué NO ahora

- BudgetCategory solo ~60 líneas
- Tracking básico (spent + contributions)
- Sin historial ni estadísticas complejas
- Separar ahora = complejidad sin beneficio en v0.2

### 📚 Principio SOLID aplicado

**Interface Segregation Principle (ISP):**
- Clientes no deberían depender de interfaces que no usan
- Si solo necesitas consultar presupuesto, no necesitas métodos de tracking

---

## 4️⃣ Repositories - Protocol para persistencia (v0.4)

### 📊 Situación actual (v0.2)

```python
class ExpenseTracker:
    def __init__(self):
        self.expenses: list[Expense] = []  # ← Todo en memoria
    
    def add_expense(self, expense: Expense):
        self.expenses.append(expense)
    
    def get_all(self) -> list[Expense]:
        return self.expenses.copy()
```

**Problema:** Al cerrar programa, pierdes todos los datos.

### 🎯 Trigger para Protocol

**En v0.4 cuando implementes:**
- ✅ Persistencia en SQLite (base de datos local)
- ✅ Exportación a CSV/JSON
- 🔮 Sincronización cloud (futuro lejano)

### 🔧 Implementación con Protocol (Dependency Inversion)

```python
# src/storage/expense_repository.py
from typing import Protocol

class ExpenseRepository(Protocol):
    """Contrato para almacenar gastos (abstracción)"""
    
    def save(self, expense: Expense) -> None:
        """Guarda un gasto"""
        ...
    
    def get_all(self) -> list[Expense]:
        """Recupera todos los gastos"""
        ...
    
    def get_by_category(self, category: str) -> list[Expense]:
        """Filtra por categoría"""
        ...
    
    def get_by_member(self, member: str) -> list[Expense]:
        """Filtra por miembro"""
        ...
    
    def delete(self, expense_id: str) -> bool:
        """Elimina un gasto"""
        ...


# ===== IMPLEMENTACIÓN 1: En memoria (v0.2) =====
class InMemoryExpenseRepository:
    """Almacena gastos en memoria (desaparece al cerrar)"""
    
    def __init__(self):
        self._expenses: list[Expense] = []
    
    def save(self, expense: Expense) -> None:
        self._expenses.append(expense)
    
    def get_all(self) -> list[Expense]:
        return self._expenses.copy()
    
    def get_by_category(self, category: str) -> list[Expense]:
        return [e for e in self._expenses if e.category == category]
    
    def get_by_member(self, member: str) -> list[Expense]:
        return [e for e in self._expenses if e.member == member]


# ===== IMPLEMENTACIÓN 2: SQLite (v0.4) =====
class SQLiteExpenseRepository:
    """Almacena gastos en SQLite (persiste entre sesiones)"""
    
    def __init__(self, db_path: str):
        import sqlite3
        self.conn = sqlite3.connect(db_path)
        self._create_table()
    
    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member TEXT NOT NULL,
                category TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT,
                date TEXT NOT NULL
            )
        """)
        self.conn.commit()
    
    def save(self, expense: Expense) -> None:
        self.conn.execute(
            "INSERT INTO expenses (member, category, amount, description, date) VALUES (?, ?, ?, ?, ?)",
            (expense.member, expense.category, expense.amount, 
             expense.description, expense.date.isoformat())
        )
        self.conn.commit()
    
    def get_all(self) -> list[Expense]:
        cursor = self.conn.execute("SELECT member, category, amount, description, date FROM expenses")
        rows = cursor.fetchall()
        
        expenses = []
        for row in rows:
            # Reconstruir Expense desde DB
            expense = Expense(
                member=row[0],
                category=row[1],
                amount=row[2] / 100,  # Cents to euros
                description=row[3]
            )
            # Restaurar fecha...
            expenses.append(expense)
        
        return expenses
    
    def get_by_category(self, category: str) -> list[Expense]:
        cursor = self.conn.execute(
            "SELECT * FROM expenses WHERE category = ?", 
            (category,)
        )
        # Convertir rows a Expense objects...
        pass


# ===== IMPLEMENTACIÓN 3: JSON (v0.4) =====
class JSONExpenseRepository:
    """Almacena gastos en archivo JSON"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        import json
        from pathlib import Path
        
        if not Path(self.file_path).exists():
            with open(self.file_path, 'w') as f:
                json.dump([], f)
    
    def save(self, expense: Expense) -> None:
        import json
        
        # Leer JSON actual
        with open(self.file_path, 'r') as f:
            expenses = json.load(f)
        
        # Añadir nuevo gasto
        expenses.append({
            "member": expense.member,
            "category": expense.category,
            "amount": expense.amount,
            "description": expense.description,
            "date": expense.date.isoformat()
        })
        
        # Guardar
        with open(self.file_path, 'w') as f:
            json.dump(expenses, f, indent=2)
    
    def get_all(self) -> list[Expense]:
        import json
        
        with open(self.file_path, 'r') as f:
            data = json.load(f)
        
        # Convertir JSON a Expense objects
        expenses = []
        for item in data:
            expense = Expense(
                member=item["member"],
                category=item["category"],
                amount=item["amount"] / 100,
                description=item["description"]
            )
            expenses.append(expense)
        
        return expenses
```

**ExpenseTracker depende de la abstracción:**

```python
class ExpenseTracker:
    def __init__(self, repository: ExpenseRepository):  # ← Protocol, no clase concreta
        self.repository = repository
    
    def add_expense(self, expense: Expense):
        self.repository.save(expense)
    
    def get_all(self) -> list[Expense]:
        return self.repository.get_all()
    
    def get_by_category(self, category: str) -> list[Expense]:
        return self.repository.get_by_category(category)
```

**Uso intercambiable en diferentes versiones:**

```python
# v0.2: En memoria
repo = InMemoryExpenseRepository()
tracker = ExpenseTracker(repo)

# v0.4: SQLite
repo = SQLiteExpenseRepository("finanzas.db")
tracker = ExpenseTracker(repo)

# v0.5: JSON
repo = JSONExpenseRepository("expenses.json")
tracker = ExpenseTracker(repo)

# ExpenseTracker NO CAMBIA ✅
```

### ✅ Ventajas (Dependency Inversion + Liskov Substitution)

1. **Testeable:** Inyectar `MockExpenseRepository` en tests sin dependencias externas
2. **Flexible:** Cambiar de memoria → SQLite sin modificar ExpenseTracker
3. **Open/Closed:** Añadir PostgreSQL sin tocar código existente
4. **Mantenible:** Lógica de negocio NO conoce detalles de DB

**Ejemplo de test con mock:**

```python
class MockExpenseRepository:
    """Mock para tests - sin DB real"""
    
    def __init__(self):
        self.saved_expenses = []
        self.save_called = False
    
    def save(self, expense):
        self.saved_expenses.append(expense)
        self.save_called = True
    
    def get_all(self):
        return self.saved_expenses


def test_expense_tracker_add_expense():
    # Arrange
    mock_repo = MockExpenseRepository()
    tracker = ExpenseTracker(mock_repo)
    expense = Expense("Amanda", "fijos", 100)
    
    # Act
    tracker.add_expense(expense)
    
    # Assert
    assert mock_repo.save_called
    assert len(mock_repo.saved_expenses) == 1
    assert mock_repo.saved_expenses[0] == expense
```

### ❌ Por qué NO ahora

- En v0.2 no hay persistencia real (solo memoria)
- Crear 3 capas (Protocol + InMemory + Interfaces) para guardar en lista = overengineering
- Añade complejidad sin beneficio tangible hasta v0.4
- **YAGNI:** Implementa cuando realmente necesites SQLite

### 📚 Principios SOLID aplicados

**Dependency Inversion Principle (DIP):**
- Depende de abstracciones (ExpenseRepository Protocol), no de implementaciones concretas
- Los módulos de alto nivel (ExpenseTracker) no dependen de los de bajo nivel (SQLiteExpenseRepository)

**Liskov Substitution Principle (LSP):**
- Puedes sustituir InMemoryExpenseRepository por SQLiteExpenseRepository sin romper ExpenseTracker
- Todas las implementaciones cumplen el contrato del Protocol

---

## 📊 Resumen: Cuándo aplicar cada mejora

| Mejora | Trigger concreto | Versión sugerida | ¿Urgente? |
|--------|------------------|------------------|-----------|
| **Extraer DistributionService** | Household >250 líneas O 5+ métodos distribución | v0.3+ | ❌ No |
| **Strategy Pattern** | 5+ métodos complejos O configuración por método | v0.3+ | ❌ No |
| **Separar BudgetCategory** | >150 líneas O historial/estadísticas complejas | v0.4+ | ❌ No |
| **Protocol repositories** | Implementar persistencia SQLite | v0.4 | ✅ Sí |

---

## 🎯 Principios clave para el futuro

### 1. **YAGNI (You Aren't Gonna Need It)**
No implementes funcionalidad hasta que la necesites realmente.

### 2. **KISS (Keep It Simple, Stupid)**
La solución más simple que funciona es la mejor.

### 3. **Rule of Three**
Refactoriza después de ver el patrón 3 veces, no antes.

### 4. **Código pragmático > Código perfecto**
Un proyecto funcional y mantenible es mejor que uno perfectamente arquitecturado pero incompleto.

---

## ✅ Estado actual del proyecto vs SOLID

| Principio | Estado | Evaluación |
|-----------|--------|------------|
| **S** (Single Responsibility) | ✅ Muy bien | Household es "gordo" pero OK por ahora |
| **O** (Open/Closed) | ✅ Bien | Enum + match/case es extensible |
| **L** (Liskov Substitution) | N/A | Sin herencia (composición > herencia) |
| **I** (Interface Segregation) | ✅ Excelente | Clases pequeñas y enfocadas |
| **D** (Dependency Inversion) | ✅ Excelente | Inyección de dependencias consistente |

**Conclusión:** Tu proyecto respeta SOLID lo suficiente para v0.2. No refactorices por perfeccionismo.

---

## 🔮 Roadmap de mejoras arquitecturales

```
v0.2 (Actual)
├── ✅ Inyección de dependencias
├── ✅ Separación de responsabilidades básica
└── ✅ Clases pequeñas y cohesivas

v0.3
├── ⚠️ Evaluar si Household necesita DistributionService
└── ⚠️ Considerar Strategy si añades muchos métodos de reparto

v0.4
├── ✅ IMPLEMENTAR Protocol para repositories (crítico para persistencia)
└── ⚠️ Evaluar si BudgetCategory necesita separación

v0.5+
└── 🔮 Evaluar patrones adicionales según necesidades reales
```

---

**Última actualización:** 03-03-2026  
**Próxima revisión:** Al completar v0.3 o cuando Household supere 250 líneas
