## Qué son los buckets

Un bucket es una etiqueta con nombre sobre dinero que ya existe en `SavingAccount`. No tiene dinero propio — tiene asignaciones. La metáfora exacta es la libreta que describiste: el dinero real está en `SavingAccount`, los buckets son columnas que dicen "de ese dinero, este trozo tiene un propósito".

---

## Arquitectura

```
WorkflowManager
    → Household
        → SavingTracker          ← fuente de verdad del dinero
            → SavingAccount      ← dinero real por miembro
            → BucketTracker      ← etiquetas sobre ese dinero
                → SavingBucket   ← un destino con nombre y objetivo
                    → BucketEntry ← registro de cada asignación
```

Nadie fuera de `SavingTracker` conoce `BucketTracker`. `WorkflowManager` solo habla con `Household`, que delega en `SavingTracker`.

---

## Flujo de una operación

**Crear bucket:**

```
WorkflowManager.create_saving_bucket(primitivos)
→ construye SavingBucket
→ Household.add_saving_bucket(bucket)
→ SavingTracker.add_saving_bucket(bucket)
→ BucketTracker.add_bucket(bucket)
→ devuelve UUID hacia arriba
```

**Depositar en bucket:**

```
WorkflowManager.deposit_to_bucket(member, bucket_id, amount)
→ Household.deposit_to_bucket(...)
→ SavingTracker.deposit_to_bucket(...)
    → valida: sum(asignado en buckets del miembro) + amount <= balance en SavingAccount
    → BucketTracker.deposit(bucket_id, amount, member)
```

**Retirar de bucket:**

```
WorkflowManager.withdraw_from_bucket(member, bucket_id, amount)
→ Household.withdraw_from_bucket(...)
→ SavingTracker.withdraw_from_bucket(...)
    → valida: amount <= balance del miembro en ese bucket
    → BucketTracker.withdraw(bucket_id, amount, member)
```

---

## Posibles bugs y cómo evitarlos

**Bug 1 — Sobreasignación**
El usuario asigna a buckets más de lo que tiene en `SavingAccount`. La validación en `SavingTracker.deposit_to_bucket` lo previene sumando todo lo asignado en todos los buckets del miembro antes de permitir el depósito.

**Bug 2 — Miembro que no es owner del bucket**
Un miembro intenta depositar en un bucket del que no forma parte. `SavingBucket._validate_member_in_bucket` ya lo lanza — no hay que duplicar esa validación.

**Bug 3 — Bucket sin cuenta asociada**
Se intenta depositar en un bucket para un miembro que no tiene `SavingAccount`. `SavingTracker` debe validar que el miembro tiene cuenta antes de delegar.

**Bug 4 — `get_total_assigned` incorrecto**
Si `BucketTracker.get_total_assigned(member_name)` suma mal los balances por miembro, la validación de sobreasignación falla silenciosamente. Este método necesita tests específicos.

---

## Por qué estas decisiones

**¿Por qué la validación en `SavingTracker` y no en `BucketTracker`?**
Porque `BucketTracker` no tiene acceso a `SavingAccount`. Mover la validación allí requeriría una referencia circular o pasar el balance como parámetro en cada operación — más complejidad sin beneficio.

**¿Por qué `BucketTracker` dentro de `SavingTracker` y no en `Household`?**
Porque los buckets son una forma de organizar el ahorro, no una entidad de primer nivel del hogar. `Household` no necesita saber que existen buckets — solo habla con `SavingTracker`.

**¿Por qué `SavingBucket` mantiene sus propias `BucketEntry`?**
Para poder responder "¿cuánto hay asignado a este bucket y por quién?" sin tener que reconstruirlo desde `SavingAccount`. Es un registro de asignaciones, no de dinero real.
