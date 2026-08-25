Aquí tienes el documento completo para no perder contexto:

---

# 📋 DECISIONES PENDIENTES — Sesión 15/03/26

---

## 🔴 SETTLEMENT

### Problema central
Para calcular quién debe a quién, necesitamos definir qué gastos entran en el cálculo. Si incluimos todos, un miembro que ahorra más obligaría al otro a pagarle, lo cual no tiene sentido.

### Lo que está claro
- Ahorro es individual y **nunca** entra en settlement
- `fijos` siempre entra en settlement — es gasto del hogar por definición
- Settlement necesita filtrar gastos por naturaleza compartida vs personal

### Solución A — `CategoryBehavior` en `BudgetCategory` ✅ Solución buena, decisión pendiente
El behavior (SHARED/EXCLUDED) vive en la categoría. El sistema decide una vez, y todos los gastos de esa categoría heredan ese comportamiento. El usuario configura la categoría una sola vez y el sistema lo recuerda mes a mes.

**Ventajas:**
- El usuario vago no decide nada — los defaults del sistema son correctos
- Consistencia garantizada: no depende de que el usuario marque bien cada gasto
- Escalable: cuando lleguen subcategorías, el behavior se mueve ahí de forma natural
- Una vez configurado, funciona solo para siempre

**Zonas grises sin resolver:**
- `variables` en v0.1 es SHARED, lo que significa que si Heri gasta su presupuesto en cafés personales, Amanda carga con parte. Limitación consciente hasta v0.3 con subcategorías
- `deuda` no puede ser estándar porque puede ser compartida (hipoteca) o personal (préstamo individual). ¿Default EXCLUDED y el usuario cambia si es compartida? ¿O el usuario declara obligatoriamente al crearla?

**Lo que resuelve en v0.3:**
Cuando subcategorías tengan entidad propia, `variables > supermercado` será SHARED y `variables > cafe_personal` será EXCLUDED. El usuario preciso configura una vez y obtiene settlement exacto. El usuario vago no configura nada y sigue funcionando con defaults de categoría.

---

**Solución B — `shared` flag en `Expense` ✅ Solución rápida, peor a largo plazo**
Cada gasto individual lleva un flag `shared: bool`. Settlement suma solo los gastos marcados como compartidos.

**Ventajas:**
- Simple de implementar ahora
- Máxima precisión por gasto

**Problemas:**
- Fricción en cada gasto — el usuario decide en cada registro
- Default `shared=True` genera errores silenciosos frecuentes (el café personal entra en settlement si el usuario no recuerda marcarlo)
- No es configurable una vez — el usuario repite la decisión cada mes
- Inconsistencia garantizada: `fijos` con `shared=False` es semánticamente inválido pero el modelo lo permite

**Conclusión:** Solución B es el camino rápido pero genera deuda técnica y UX mala. Solución A es más trabajo ahora pero es la arquitectura correcta a largo plazo. **Decisión pendiente: confirmar Solución A y cerrar.**

---

### Cómo conectar subcategorías al sistema actual (v0.3)

Hoy subcategorías son un string libre en `Expense`. Cuando tengan entidad propia, la migración es:

```
Hoy:    Expense(member, category="variables", subcategory="cafe", amount)
v0.3:   Expense(member, category=Category, subcategory=Subcategory, amount)
        Subcategory lleva: name, behavior(SHARED/EXCLUDED), parent_category
```

`BudgetCategory` se convierte en contenedor de `Subcategory`. El presupuesto puede vivir en la categoría (como ahora) o bajar a subcategoría cuando el usuario quiere esa precisión. Settlement en v0.3 itera subcategorías en lugar de categorías.

La migración no rompe el modelo actual — es una extensión. `CategoryBehavior` en `BudgetCategory` hoy es exactamente el mismo concepto que en `Subcategory` mañana.

---

## 🟡 CATEGORÍAS — Creación y gestión

### Lo que está claro
- `fijos` y `variables` son las únicas categorías verdaderamente estándar del sistema
- `ahorro` sale del sistema de categorías completamente → vive en `SavingsTracker`
- El patrón de presupuesto por porcentajes debe completarse

### Decisiones pendientes

**¿Pueden los usuarios renombrar fijos/variables?**
Si un usuario quiere llamarles "gastos fijos" y "gastos del día a día", ¿el sistema lo permite? Implicación: el sistema necesita un identificador interno (`slug`) separado del nombre display. O simplemente no se permite renombrar categorías estándar.

**¿`deuda` existe como categoría estándar?**
Un usuario puede tener deuda 0, en cuyo caso la categoría no existiría. Opciones:
- `deuda` es categoría opcional que el usuario activa si la necesita
- `deuda` no existe en el sistema — el usuario crea sus propias categorías de deuda con nombre y behavior explícito
- `deuda` existe pero con presupuesto 0 hasta que el usuario lo asigne

Implicación para el patrón de porcentajes: si `deuda` no es estándar, el flujo de onboarding es:
```
fijos     → usuario asigna % o monto
variables → usuario asigna %
[categorías custom opcionales]
ahorro    → recibe lo que sobre, o el usuario define goal explícito
```

**¿Qué pasa con el loose money?**
El usuario puede:
- A) Destinarlo a ahorro (define savings goal)
- B) Dejarlo como colchón del mes (loose money explícito)
- C) Mix: parte a ahorro, parte libre

El sistema no debe asumir que todo el loose money va a ahorro. El usuario elige. Si no define savings goal, todo queda como loose money. **¿Hay un paso en PLANNING donde el sistema muestra el loose money y pregunta cuánto va a ahorro?** Esto define si `set_savings_goal()` es parte del flujo obligatorio de PLANNING o una acción opcional.

---

## 🟢 AHORRO — Diseño cerrado

### Lo que está claro
- `SavingsAccount` es por miembro, acumulativa (histórico total, no solo mensual)
- Operaciones v0.1: depósito y retiro
- Transferencias internas (ahorro → categoría) son futuro próximo, no v0.1
- Ahorro mensual es elección del usuario — puede ser 0
- Balance puede ser negativo si retiran más de lo depositado
- Histórico es lo que desbloquea planificación futura

### Modelo acordado

```
SavingsEntry     → amount_cents (positivo=depósito, negativo=retiro), date, description
SavingsAccount   → entries acumulativos + monthly_goal opcional
SavingsTracker   → una account por miembro, inyectado en Household
```

### Pendiente de decidir
- ¿Cómo se presenta un balance negativo al usuario? ¿Warning, error, se permite silenciosamente?
- ¿`monthly_goal` se define en PLANNING o puede definirse/modificarse durante MONTH?
- Reconciliación en `finish_month()`: ¿qué genera? ¿Solo reporte planned vs actual, o hay alguna acción automática?

### Integración con fases
```
PLANNING → set_savings_goal(member, amount) — opcional
MONTH    → register_savings_deposit(member, amount)
           register_savings_withdrawal(member, amount)
CLOSING  → reconciliación: planned_goal vs actual_deposited este mes
           histórico: snapshot mensual de savings por miembro
```

### Pregunta clave aún abierta
¿`SavingsAccount` necesita distinguir entre meses internamente, o es una lista plana de entries con fecha y el sistema filtra por fecha cuando necesita datos mensuales? La segunda opción es más simple y más flexible — permite queries históricas arbitrarias sin estructura fija por mes.

**Recomendación:** lista plana con fecha. Cuando necesites "ahorro de marzo", filtras por fecha. Cuando necesites histórico total, sumas todo. No hay que predefinir la estructura temporal.

---

## 📦 ORDEN DE IMPLEMENTACIÓN ACTUALIZADO

```
1. SavingsEntry + SavingsAccount + SavingsTracker          ← siguiente sesión
2. Inyectar SavingsTracker en Household
3. set_savings_goal() en WorkflowManager (PLANNING, opcional)
4. register_savings_deposit() + register_savings_withdrawal() (MONTH)
5. finish_month() con reconciliación básica (CLOSING)
6. start_new_month() → nuevo ExpenseTracker, reset fase

— Decisión pendiente antes de continuar —
7. Cerrar CategoryBehavior (Solución A vs B)
8. get_settlement() usando behavior decidido
9. Cerrar modelo de categorías (deuda, renombrado, loose money → ahorro)
```

---

## 🧊 BACKLOG CONFIRMADO FUERA DE SCOPE ACTUAL

- **Transferencias internas** (`InternalTransfer`, `TransferTracker`) → v0.2
- **Subcategorías con entidad propia y behavior** → v0.3
- **Métodos de reparto por categoría** → v0.3
- **Cuentas bancarias** (cuenta A, cuenta B, cuenta conjunta, domiciliaciones) → v0.4. Requiere entidad `Account`, `Expense` referenciando account, settlement por cuenta
- **SavingsBuckets** (metas de ahorro a largo plazo) → v0.5
- **Histórico multi-mes + analytics** → v0.4/v0.5