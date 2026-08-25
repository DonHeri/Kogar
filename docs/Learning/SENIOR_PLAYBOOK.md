# Guía Rápida: Cómo Enfrentar Cualquier Tarea

---

## Antes de empezar

**Pregunta única:** ¿Qué es lo MÍNIMO que necesito para que esto funcione?

No implementes 10 cosas. Implementa 1 cosa que aporte valor.

---

## Cuando estés bloqueado (>30 min)

**¿Estoy haciendo demasiado a la vez?**  
→ Reduce: implementa solo 1 parte, no todo

**¿Me falta información?**  
→ Escribe un test que muestre qué necesitas

**¿Estoy buscando la solución perfecta?**  
→ Acepta la fea ahora, mejórala después

**¿Ya existe algo similar?**  
→ Búscalo en el código y adáptalo

**Llevo más de 2 horas igual:**  
→ Pide ayuda o cambia de tarea

---

## Forma de trabajar

### Ciclo básico (20-30 min):

1. Test simple que falla
2. Código mínimo que lo pasa
3. Commit
4. Repetir

### Ejemplo:

```python
# Commit 1: return {"total": 0}
# Commit 2: return {"total": calculado}
# Commit 3: return {"total": calculado, "items": []}
```

No intentes hacerlo perfecto desde el inicio.

---

## Tests

**Orden recomendado:**

1. Test tonto: ¿devuelve algo?
2. Test simple: 1 caso básico
3. Test vacío: ¿funciona con datos vacíos?
4. Test real: flujo completo

No empieces por el test complejo.

---

## Commits

**Cada 20-30 minutos:**

```bash
git commit -m "feat: agregar campo X"
```

No esperes a terminar todo. Commitea progreso.

---

## Preguntas útiles

**Antes de codear:**

- ¿Qué es lo mínimo?
- ¿Cómo sé que funciona?

**Mientras codeas:**

- ¿Esto se entiende?
- ¿Estoy repitiendo código?

**Antes de commit:**

- ¿Pasan los tests?
- ¿El mensaje es claro?

---

## Reglas simples

1. Implementa primero lo que da más valor al usuario
2. Copia código similar sin culpa
3. Test temprano (no al final)
4. Commits frecuentes (cada 20-30 min)
5. Si >2h bloqueado → cambia enfoque
6. Breaks cada hora
7. Solución fea > nada funcionando
8. Itera, no busques perfección

---

## Cuando todo falle

1. Para de codear
2. Explica el problema en voz alta
3. Dibuja el flujo en papel
4. Busca ejemplos similares en el repo
5. Implementa la versión más simple posible

---

**Recuerda:** Progreso imperfecto > perfección sin progreso
