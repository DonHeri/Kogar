Select text to add comments on the plan
Plan: CategoryBehavior + is_shared + Settlement
Context
Se quiere diferenciar gastos/categorías entre compartidos y personales, prerequisito para implementar get_settlement(). La decisión de diseño es: CategoryBehavior define el default por categoría, pero el usuario puede hacer override por gasto concreto.

El ahorro ya tiene SavingDestination.PERSONAL/SHARED, no requiere cambios.

Cabos sueltos identificados (previo a la tarea principal)
Test function names desactualizados — test_household.py y test_workflow_manager.py tienen funciones llamadas test_get_loose_money_* y similares. Renombrar a missing_money. Archivos: tests/test_household.py, tests/test_workflow_manager.py

FIXME cosmético — workflow_manager.py:118 tiene comentario # FIXME O crear standard_categories??? pero el comportamiento actual (raise ValueError) es correcto. Eliminar el FIXME.

Implementación principal
Paso 1 — CategoryBehavior en BudgetCategory
Archivo: src/models/budget_category.py

Añadir enum CategoryBehavior(Enum): SHARED, EXCLUDED
Añadir parámetro behavior: CategoryBehavior = CategoryBehavior.SHARED al constructor
Exponer como @property behavior
Paso 2 — Defaults al crear categorías
Archivo: src/models/household.py

En set_standard_categories() y add_category(): pasar behavior=CategoryBehavior.EXCLUDED cuando la categoría sea reserva. Resto: SHARED (default).
Añadir helper get_category_behavior(category_name) -> CategoryBehavior
Paso 3 — is_shared en Expense
Archivo: src/models/expense.py

Añadir campo is_shared: bool = True al constructor
Validar que sea bool
Exponer como @property
Paso 4 — WorkflowManager.register_expense()
Archivo: src/workflow/workflow_manager.py

Añadir parámetro opcional is_shared: bool | None = None a register_expense()
Si is_shared is None: derivar de household.get_category_behavior(category):
SHARED → is_shared=True
EXCLUDED → is_shared=False
Si el usuario pasa is_shared explícitamente: usar ese valor (override)
Pasar is_shared al crear Expense
Paso 5 — Implementar get_settlement()
Archivo: src/models/household.py

Descomentar y implementar get_settlement()
Lógica:
Obtener todos los gastos con is_shared=True del expense_tracker
Por cada miembro: balance = paid_shared - agreed_contribution_shared
Resolver transferencias mínimas (algoritmo deudor/acreedor)
Retornar list[dict]: [{"from": str, "to": str, "amount": int}]
Exponer en WorkflowManager con validate_phase_accessible(Phase.MONTH)
Paso 6 — Tests
tests/test_budget_category.py: CategoryBehavior en constructor, default SHARED, EXCLUDED
tests/test_expense.py: campo is_shared, default True, override
tests/test_household.py: get_category_behavior(), get_settlement() con casos:
gastos solo shared → settlement correcto
gastos reserva excluidos del settlement
is_shared override en gasto individual
tests/test_workflow_manager.py: register_expense con is_shared derivado y con override
Archivos a modificar
Archivo	Cambio
src/models/budget_category.py	+ CategoryBehavior enum + campo behavior
src/models/expense.py	+ campo is_shared
src/models/household.py	+ get_category_behavior() + get_settlement()
src/workflow/workflow_manager.py	+ is_shared en register_expense(), + get_settlement(), - FIXME
tests/test_budget_category.py	+ tests CategoryBehavior
tests/test_expense.py	+ tests is_shared
tests/test_household.py	+ tests settlement, renombrar funciones loose_money
tests/test_workflow_manager.py	+ tests settlement, renombrar funciones loose_money
Verificación
pytest tests/test_budget_category.py
pytest tests/test_expense.py
pytest tests/test_household.py
pytest tests/test_workflow_manager.py
pytest --cov=src