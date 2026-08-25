# ================================================ ⏳ EN NEVERA (Ideas/Dudas que no urgen) ================================================
- **[Arquitectura]** Normalización: WM hace `.strip()` pero NO lowercase. Nombres propios mantienen capitalización. CategoryLibrary ya normaliza categorías.
- **[General]** Tracker de IVA: registrar IVA por gasto, saber total al final del mes
- **[ExpensesTracker]** Filtrar por: día, rango días, rango precios, nombre
- **[CategoryLibrary]** Verificador similitudes: detectar si usuario quiso decir categoría existente
- **[BudgetCategory]** Gastos usan `MetodoReparto`, ahorros usan `individual_goals` por miembro
- **[Expense]** `Expense` = solo gastos externos. Transferencias internas NO son Expense, se calculan con `get_settlement()`. Futuro: `InternalTransfer` si necesario. Usa strings para member/category.

---

### **MEJORAS SOLID (Futuras)**

- **[Household]** Si >250-300 líneas → extraer `BudgetDistributionService`
- **[MetodoReparto]** Si 5+ métodos → Strategy Pattern con `DistributionStrategy(Protocol)`
- **[BudgetCategory]** Si >150 líneas → dividir en `BudgetCategory` + `CategoryExpenseTracker`
- **[Repositories]** Cuando SQLite → `ExpenseRepository(Protocol)`

---

# ================================================ 🏗️ DEFINIENDO ================================================

- **[Expense]** ¿ID único (UUID) o objeto en memoria suficiente?
- **[Household]** 🟡`preview_method()` y `preview_all_methods()`


# ================================================ 🏁 CERRADAS (Funcionamiento actual) ================================================

### **====== 06-03-26 ======**

- **[Household]** Congelar estado en transiciones: `finish_registration()` cachea `_registered_incomes`. `finish_planning()` cachea `_agreed_percentages` y `_agreed_contributions`. Fases posteriores usan datos oficiales. Helpers comprueban frozen data primero. ✅

- **[WorkflowManager]** Doble validación: `validate_phase()` estricta (solo current), `validate_phase_accessible()` permisiva (current O completada). Modificaciones estrictas, consultas permisivas. ✅

- **[WorkflowManager]** `_completed_phases = set()` registra fases alcanzadas. Inicia con `{Phase.REGISTRATION}`. `finish_X()` añade siguiente fase ANTES de cambiar current_phase. ✅

- **[Household]** `preview_budget_contribution_summary(method)` simula. `get_current_contributions()` usa self.method ya configurado. ✅

- **[Código]** Organización por secciones: comentarios `# ====== REGISTRATION PHASE ======`. Facilita navegación. ✅

### **====== 05-03-26 ======**

- **[WorkflowManager]** Única capa conversión euros↔céntimos. Dominio 100% céntimos (int). Bug corregido: antes x2 conversión (gastos x100). ✅

- **[WorkflowManager]** Recibe primitivos del CLI, crea objetos dominio. CLI no importa Member/Expense. WM hace `.strip()` pero NO normaliza. ✅

### **====== 03-03-26 ======**

- **[Household]** ExpenseTracker inyectado en constructor. Permite mocks in tests. ✅
- **[ExpenseTracker]** NO valida, solo almacena/filtra. Validaciones en Household. WM crea → Household valida → Tracker almacena. ✅
- **[ExpenseTracker]** Un tracker = un mes. Siguiente mes = nuevo tracker. Histórico multi-mes v0.4. ✅
- **[ExpenseTracker vs Calculator]** Tracker usa `sum()` directo. Calculator para distribuciones complejas. ✅

### **====== 02-03-26 ======**

- **[Budget]** 4 categorías rígidas ahora, futuro flexibles. ✅
- **[Household]** Gestiona percentages y contributions. ✅
- **[General]** 100% ingresos con destino. `get_planning_summary()` expone "loose_money". ✅
- **[CLI]** `finish_registration` y `finish_planning` validan antes avanzar fase. ✅

#### **27-02-26**

- **[MetodoReparto]** Método único global v0.2. Todas categorías mismo reparto. v0.3: per-category. ✅
- **[Arquitectura]** `Protocol` mejor que ABC para repos. Duck typing, mypy. ✅

#### **20-02-26**

- **[Phases]** Fases NO en Household. WorkflowManager orquesta. Entidades dominio no conocen fases. ✅
- **[utils]** `change_eur_cent.py` → `currency.py` ✅
- **[Budget]** Si >150 líneas, `BudgetCategory` a archivo propio. ✅
- **[Member]** `participante.py` → `member.py` ✅

#### **19-02-26**

- **[Household]** `set_custom_splits` valida y convierte. PROPORTIONAL/EQUAL dinámicos, CUSTOM cachea. ✅
- **[Calculator]** Céntimos sobrantes al mayor ingreso. Empate → primero. ✅

#### **18-02-26**

- **[Calculator]** División entera `//` en vez de `round()` para céntimos. Sobrante al mayor aporte. ✅

#### **< 18-02-26**

- **[Budget]** Orquestador con dict de `BudgetCategory`. ✅
- **[Member]** Nombre obligatorio, no solo espacios. ✅
- **[BudgetCategory]** Montos > 0. ✅
- **[Calculator]** Todo céntimos (int) evita errores float. ✅
