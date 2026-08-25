# Proyecto: KOGAR

## Qué es
App de gestión financiera para hogares compartidos. Backend Python puro,
sin persistencia todavía. Gestiona miembros, presupuestos por categoría,
gastos y settlements entre miembros.

## Estado actual

- Fase: savings completos implementados, preparando settlement y cierre de mes
- Funciona: registro de miembros, presupuestos, gastos, savings completos
  (depósitos, retiros, resumen por miembro, saving_goal y deuda por miembro,
  validación deuda+ahorro vs reserva)

- Próximo hito: settlement con CategoryBehavior → cierre de mes → persistencia SQLite

## Stack
- Python puro, sin frameworks
- pytest para tests
- Estructura: src/ con módulos por entidad, tests/ espejo de src/

## Arquitectura (decisiones clave)
- WorkflowManager: única capa de conversión euros↔céntimos, crea objetos dominio
- Household: coordina, valida contexto de negocio
- ExpenseTracker: almacena y filtra, NO valida
- Budget: solo planning, nunca execution
- Fases: REGISTRATION → PLANNING → MONTH → CLOSING
- Dominio 100% en céntimos (int), sin floats en cálculos de dinero

## Comandos
- `pytest` — correr todos los tests
- `pytest tests/test_X.py` — tests de un módulo
- `pytest --cov=src` — con cobertura
- `python sandbox_main.py` — entorno de prueba manual

## Próximas tareas (orden de prioridad)

1. Settlement con CategoryBehavior (reserva excluida, solo categorías SHARED)
2. get_planning_summary y get_month_summary con savings y deuda en el output
3. finish_month() / CLOSING phase
