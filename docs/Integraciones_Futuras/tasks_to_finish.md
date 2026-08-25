📋 TAREAS GRANDES - v0.2 (Tracking de Gastos)
T1. Crear Entidad Expense
    Representa un gasto: quién pagó, cuánto, categoría, fecha
    Validaciones: monto > 0, categoría existe, miembro existe, fecha válida
    Métodos: getters, validadores, __repr__
    Tests: validaciones, casos extremos, constructores

T2. Crear ExpenseTracker (Gestor de Gastos)
    Contenedor de gastos como lo es Budget con categorías
    Métodos: register_expense(), get_expenses_by_category(), get_expenses_by_member()
    Métodos: get_total_spent_by_member(), get_pending_by_member_and_category()
    Validadores: gasto válido, no duplicados, etc
    Tests: 30-40 tests mínimo

T3. Integrar ExpenseTracker en Household
    Campo: self.expenses_tracker
    Métodos delegados: register_expense(), get_balances()
    Método: get_member_balance(member_name: str) → dict (debe - pagó por categoría)
    Tests: flujo completo de gasto

T4. Crear Fase MONTH en WorkflowManager
    Validar transición PLANNING → MONTH
    Métodos en MONTH: register_expense(), get_balance_summary()
    Validar que no se puede volver atrás a PLANNING una vez en MONTH
    Tests: transiciones, bloqueos, validaciones

T5. Método get_settlement() en Household
    Calcula quién debe pagar a quién al final del mes
    Retorna: {Amanda: 50, Heri: -50} (positivo=acreedor, negativo=deudor)
    Valida que suma total = 0
    Tests: múltiples escenarios de deuda/acreedor

T6. Fase CLOSING en WorkflowManager
    Transición MONTH → CLOSING
    Métodos: get_month_report() (completo con balances, settlement)
    Método: confirm_month_closed() → prepara para siguiente mes o archivo
    Tests: cierre mes, reportes

T7. Método preview_category_with_expenses() en Household
    Muestra una categoría CON gastos ya registrados
    Retorna: presupuesto, gastos, saldo, quién debe qué, porcentaje usado
    Tests: múltiples escenarios

📋 TAREAS GRANDES - v0.3 (Ahorro y Objetivos)
T8. Crear Entidad SavingsBucket
    Representa un objetivo de ahorro (vacaciones, emergencias, etc)
    Campos: nombre, objetivo_amount, current_amount, contributions_por_miembro
    Métodos: add_contribution(), get_progress(), is_complete(), get_member_contribution()
    Validadores: nombre válido, monto > 0, sin duplicados
    Tests: estado, contribuciones, progreso

T9. Crear SavingsManager
    Contenedor de múltiples SavingsBucket
    Métodos: create_bucket(), delete_bucket(), get_bucket(), list_buckets()
    Método: get_total_savings_by_member() (cuánto ha aportado cada uno en total)
    Validadores: bucket existe, nombre válido, no duplicados
    Tests: CRUD de buckets, validaciones

T10. Integrar SavingsManager en Household
    Campo: self.savings_manager
    Métodos: add_savings_bucket(), contribute_to_bucket(), get_savings_summary()
    Método: allocate_budget_to_savings() (si presupuesto "ahorro" es para bucket)
    Tests: flujo completo de ahorro

T11. Lógica de Distribución de Ahorro
    En PLANNING: si presupuesto es categoría "ahorro", pregunta si es SavingsBucket
    Si es bucket: distribuir según método_reparto elegido
    Si es general: simplemente presupuestar
    Tests: distribución, buckets, presupuestos simultáneos

T12. Reportes de Ahorro en WorkflowManager
    Métodos: get_savings_report() (progreso de todos los buckets)
    Método: get_member_savings_contribution() (cuánto ha aportado cada miembro)
    Tests: múltiples buckets, miembros, contribuciones

📋 TAREAS TRANSVERSALES (Necesarias Ahora o Pronto)
T13. Buscador de Similitudes en CategoryLibrary
    Método: find_similar(user_input: str, threshold=75) con difflib
    Retorna: lista de categorías similares
    Usa en add_category() para advertir duplicados
    Tests: casos exactos, typos, similares
T14. Métodos de Reparto POR CATEGORÍA
    Household.set_category_distribution_method(category, method)
    Almacenar dict: {categoria: método}
    Calcular contribuciones respetando método por categoría
    Tests: métodos diferentes por categoría
T15. get_planning_summary() Completo
    Resumen presupuestos + método + contribuciones por categoría
    Validar dinero suelto
    Mostrar warnings
    Tests: completo, con warnings, sin dinero suelto
T16. CLI/Workflow Mejorado para PLANNING
    Agregar categoría → asignar presupuesto → elegir método → ver preview
    Todo conectado con WorkflowManager
    Tests de integración: flujo completo REGISTRATION → PLANNING → MONTH