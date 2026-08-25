# 🎯 PRIORIDAD 1 - MVP Usable

### 1. Sistema de Porcentajes (2-3h)

- [ ] `WorkflowManager.set_budget_by_percentage(category, pct)`
- [ ] `WorkflowManager.get_budget_as_percentage(category)`
- [ ] `WorkflowManager.apply_percentage_distribution(dict)`
- [ ] Tests

### 2. Settlement (1-2h)

- [ ] `Household.get_settlement()` → [{from, to, amount}]
- [ ] Algoritmo para 2 personas
- [ ] Tests

### 3. CLOSING (2-3h)

- [ ] `WorkflowManager.finish_month()` → generar settlement + reporte
- [ ] `WorkflowManager.start_new_month()` → reset tracker
- [ ] Tests

---

# 🔧 PRIORIDAD 2 - Mejoras UX

### 4. Transacciones internas (3-4h)

- [ ] Clase `InternalTransfer`
- [ ] Clase `TransferTracker`
- [ ] Integrar con balances
- [ ] Tests

### 5. Ingresos extras (3-4h)

- [ ] Diseño: ¿individual o compartido?
- [ ] Implementación
- [ ] Tests

---

# 🧊 BACKLOG

### Refactors
- [ ] Validaciones centralizadas
- [ ] BudgetCategory con @property
- [ ] Excepciones custom
- [ ] Summary builders

### v0.3
- [ ] Subcategorías en gastos
- [ ] Buscar similitudes CategoryLibrary
- [ ] Método reparto por categoría

### v0.4+
- [ ] Persistencia SQLite + histórico
- [ ] Analytics + reportes (CSV, PDF)
- [ ] SavingsBuckets con metas

---

# ✅ COMPLETADO

Ver archivo COMPLETADO.md para historial detallado
