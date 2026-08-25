# Informe técnico: Problema de descuadre en la distribución de contribuciones

## 1. Descripción del problema

El sistema de reparto de contribuciones por categorías en el hogar presenta un **problema de descuadre** debido a la acumulación de redondeos cuando se trabaja con cantidades enteras (céntimos). El error se manifiesta en escenarios con múltiples categorías y miembros con ingresos desiguales, donde los redondeos sistemáticamente favorecen al miembro con mayor porcentaje, pudiendo llegar a exceder su ingreso real o el presupuesto de la categoría.

### Naturaleza matemática del problema

- Al repartir un presupuesto entre miembros usando porcentajes, cada contribución se calcula con división entera: `(budget * porcentaje) // 10000`.
- El sobrante de cada categoría (por los céntimos que no se pueden repartir) se acumula y, en el algoritmo original, se asigna al miembro mayoritario.
- Cuando hay muchas categorías, estos céntimos se suman y pueden provocar que un miembro supere su ingreso o que la suma de contribuciones supere el presupuesto de la categoría.

## 2. Función culpable

La función responsable del bug es:

```
FinanceCalculator.calculate_contributions_all_categories(categories, percentages, incomes)
```

Ubicación: `src/models/finance_calculator.py`

Esta función:

- Calcula la contribución base de cada miembro a cada categoría usando división entera.
- Acumula el sobrante global de todos los redondeos.
- Intenta redistribuir el sobrante, pero puede asignar más de lo permitido si no controla correctamente los límites de ingreso y presupuesto.

## 3. Tests que no pasan

Los siguientes tests de `tests/test_contribution_edge_cases.py` fallan sistemáticamente:

- `test_edge_case_proportional_2_to_1_full_budget`: Amanda excede su ingreso por acumulación de céntimos.
- `test_edge_case_prime_numbers_maximize_remainders`: Amanda excede su ingreso por varios céntimos.
- `test_edge_case_percentage_based_budget_33_percent`: Amanda excede su ingreso.
- `test_edge_case_ten_categories_accumulate_remainders`: Amanda excede su ingreso por acumulación extrema.
- `test_edge_case_custom_split_awkward_percentages`: La suma de contribuciones supera el presupuesto de la categoría.
- `test_edge_case_budget_exceeds_income`: Amanda excede su ingreso cuando el presupuesto total es mayor que la suma de ingresos.

**Ejemplo de error reportado:**

```
ValueError: amanda excede su ingreso: 200010 > 200000
ValueError: La suma de fijos es 150015, esperado 150000
```

## 4. Conclusión

El sistema actual no garantiza simultáneamente:

- Que ningún miembro supere su ingreso.
- Que la suma de contribuciones por categoría no supere el presupuesto.
- Que no se pierdan céntimos (invariante de contabilidad).

Esto es consecuencia directa de la aritmética entera y la acumulación de redondeos en múltiples categorías. Se requiere un algoritmo que, antes de asignar cualquier céntimo sobrante, verifique el margen disponible tanto por miembro como por categoría, y deje sin asignar el sobrante si no es posible repartirlo sin violar restricciones.
