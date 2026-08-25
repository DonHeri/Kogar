Como ejemplo, vamos a utilizar la refactorización de quitar la flag de `is_shared`, está se encuentra en category, category_library y de ahí en adelante aparece más veces.

Mi duda es, como avanzas con los cambios sin perderte en el camino:

## Paso 1: Ver el alcance del cambio -- donde aparece?

`cd "P:/Heri/20_Proyectos/proyectos-programacion/Publicos/Kogar" && echo "=== is_shared: dónde vive ==="; grep -rn "is_shared" src/ migrations/ --include=*.py | sed -E 's/:.*//' | sort | uniq -c | sort -rn`

Salida:

```bash
=== is_shared: dónde vive ===
    4 src/models/saving_bucket.py
    4 src/models/budget.py
    3 src/models/saving_bucket_tracker.py
    2 src/storage/budget_categories_repository.py
    2 src/models/category_library.py
    2 src/models/category.py
    2 migrations/versions/dc926eef2735_budget_categories_table.py
    1 src/models/expense.py
    1 src/models/budget_category.py
```

## Paso 2: Rompe a propósito y deja que el sistema te dicte la lista

Esto es lo que más te va a cambiar el día. No busques a mano dónde tocar. Cambia la firma, lanza la suite, y agrupa los errores por mensaje:

`pytest tests/ -q --no-cov 2>&1 | grep -oE "TypeError: .{0,60}" | sort | uniq -c | sort -rn`

Es lo que corrí varias veces esta sesión. Salía así:

```bash
312 TypeError: Budget.add_category() missing 'participants'
23 TypeError: BudgetCategory.**init**() missing 'participants'
```

Dos números, dos tareas. No 335 problemas: dos. Y cuando arreglas el primero, el reparto cambia y te dice qué queda. Esa lista es tu backlog, y se regenera sola cada vez que corres los tests.
En un lenguaje con tipos fuertes te la da el compilador; en Python te la da la suite, y por eso la suite es innegociable antes de un refactor transversal.

El corolario incómodo: si tu suite no cubre una zona, ese refactor lo haces a ciegas. El coste de no tener tests no se paga escribiendo tests, se paga aquí.

## Paso 3 : Aditivo primero, borrado al final

Nunca cambies una firma de golpe. Se hace en tres tiempos:

Tiempo|Qué haces|Estado|
Expandir|añades el parámetro nuevo, opcional, con default|Verde|
Migrar|mueves los llamadores, de la hoja a la raíz|Verde|
Contraer|quitas lo viejo|Verde|

El nombre técnico es **parallel change o expand/contract**. Búscalo con ese nombre, porque es la técnica central de refactorizar sin parar el mundo.

Dónde se nota la diferencia: en el tiempo 1 tú decides cuántos sitios rompes. Con default, cero. Sin default, todos a la vez — que es exactamente lo que pasó con participants y por eso salieron 335 rojos de golpe.

## Paso 4 · De la hoja a la raíz, nunca al revés

El orden no es libre: lo dicta quién depende de quién.

BudgetCategory → Budget → Household → servicios → WorkflowManager → tests
Empiezas por BudgetCategory porque no depende de nadie. Si empiezas por WorkflowManager, cada línea que escribes se apoya en algo que aún no existe, y acabas manteniendo cinco capas a medias en la cabeza. Esa sensación de "me estoy perdiendo" casi siempre es haber empezado por el sitio equivocado.

## Paso 5 · Un cambio en vuelo, y commits que compilan

Dos cosas que ya viviste hoy, las dos por lo mismo.

Cuando quité to_cents de BudgetCategory no pude verificarlo, porque tu participants a medias tapaba la suite entera con otro error. Dos cambios en vuelo y ninguno medible.

Y el commit 38971 no pasaba sus propios tests. Un commit así es un punto de retorno falso: crees que puedes volver ahí y no puedes. Por eso lo fundimos.

La regla: cada commit compila y pasa la suite. Es lo que te deja hacer git bisect dentro de tres meses cuando aparezca un número raro.


---
`git status --short | wc -l && git diff --stat | tail -1` comando util para hacer un status si sospechas que hay archivos sin cambios reales. 