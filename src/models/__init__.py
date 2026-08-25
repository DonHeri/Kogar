from src.models.saving_bucket_entry import SavingBucketEntry
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.models.budget import Budget
from src.models.budget_category import BudgetCategory
from src.models.category import AutoCalculatedCategory, Category
from src.models.category_library import CategoryLibrary
from src.models.constants import MetodoReparto, Phase, SavingScope
from src.models.exceptions import CeilingBelowChildrenError, DomainError
from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.models.finance_calculator import FinanceCalculator
from src.models.household import Household
from src.models.member import Member

from src.models.saving_bucket import SavingBucket
from src.models.subcategory_library import SubcategoryLibrary

""" 
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 2           

┌──────────────────────────────────────────────────┐
│         SETTLEMENT — GASTOS COMPARTIDOS          │
└──────────────────────────────────────────────────┘
  Heri debe 186.37€ a Amanda

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 3

┌──────────────────────────────────────────────────┐
│                GASTOS DEL PERÍODO                │
└──────────────────────────────────────────────────┘
  'Compartido' = tiene más de un participante, y solo esos entran
  en el settlement. Un gasto de un solo participante es personal.

  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ Día    │ Pagó    │ Categoría  │ Importe  │ Concepto            │ Reparto       │
  ├────────────────────────────────────────────────────────────────────────────────────────┤
  │ 06/08  │ Amanda  │ Alquiler   │ 500.00€  │ Alquiler            │ Amanda, Heri  │
  │ 06/08  │ Heri    │ Alquiler   │ 11.00€   │ alquiler            │ Amanda, Heri  │
  │ 06/08  │ Heri    │ Variables  │ 26.55€   │ Gym                 │ personal      │
  │ 06/08  │ Heri    │ Internet   │ 22.00€   │ internet            │ Amanda, Heri  │
  │ 06/08  │ Heri    │ Luz        │ 94.25€   │ luz                 │ Amanda, Heri  │
  │ 06/08  │ Heri    │ Variables  │ 3.50€    │ chiringuito el och  │ personal      │
  │ 06/08  │ Amanda  │ Variables  │ 32.90€   │ gym                 │ personal      │
  └────────────────────────────────────────────────────────────────────────────────────────┘

  TOTAL GASTADO                    690.20€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 4

  ¿De quién?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

┌──────────────────────────────────────────────────┐
│                 ESTADO DE AMANDA                 │
└──────────────────────────────────────────────────┘

  ┌─ AMANDA ───────────────────────────┐
  │  Ingreso            1413.85€  │
  │  Le toca poner      1269.18€  │
  │  Ha pagado           532.90€  │
  │  Cuota de deuda      118.90€  │
  │  Metas de ahorro       0.00€  │
  └─────────────────────────────────────┘

  Balance (pagado − debido)       -736.28€
      En negativo, debe dinero al hogar.

  ┌────────────────────────────────────────────────────┐
  │ Categoría  │ Acordó   │ Pagó     │ Le falta  │
  ├────────────────────────────────────────────────────┤
  │ Fijos      │ 18.67€   │ 0.00€    │ 18.67€    │
  │ Variables  │ 200.00€  │ 32.90€   │ 167.10€   │
  │ Reserva    │ 396.51€  │ 0.00€    │ 396.51€   │
  │ Alquiler   │ 255.50€  │ 500.00€  │ -244.50€  │
  │ Agua       │ 17.50€   │ 0.00€    │ 17.50€    │
  │ Luz        │ 45.00€   │ 0.00€    │ 45.00€    │
  │ Comida     │ 325.00€  │ 0.00€    │ 325.00€   │
  │ Internet   │ 11.00€   │ 0.00€    │ 11.00€    │
  └────────────────────────────────────────────────────┘


  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 12

┌──────────────────────────────────────────────────┐
│               RESERVA SIN DESTINO                │
└──────────────────────────────────────────────────┘
  Dinero libre: de aquí sale deuda, ahorro, o lo que decidas.
  Amanda                           396.51€
  Heri                             396.51€
──────────────────────────────────────────────────────
  TOTAL                            793.02€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 1 

  ┌─ BALANCE DEL MES ────────────────┐
  │  Presupuestado    2538.35€  │
  │  Gastado           690.20€  │
  │  Restante         1848.15€  │
  └───────────────────────────────────┘


  ┌────────────────────────────────────────────────────────┐
  │ Categoría     │ Presup.   │ Gastado  │ Restante  │
  ├────────────────────────────────────────────────────────┤
  │ Fijos         │ 1345.33€  │ 627.25€  │ 718.08€   │
  │   · Alquiler  │ 511.00€   │ 511.00€  │ 0.00€     │
  │   · Agua      │ 35.00€    │ 0.00€    │ 35.00€    │
  │   · Luz       │ 90.00€    │ 94.25€   │ -4.25€    │
  │   · Comida    │ 650.00€   │ 0.00€    │ 650.00€   │
  │   · Internet  │ 22.00€    │ 22.00€   │ 0.00€     │
  │ Variables     │ 400.00€   │ 62.95€   │ 337.05€   │
  │ Reserva       │ 793.02€   │ 0.00€    │ 793.02€   │
  └────────────────────────────────────────────────────────┘


Por miembro — lo acordado frente a lo pagado
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda (pagado − acordado)      -736.28€
      acordó 1269.18€  ·  pagó 532.90€
  Heri (pagado − acordado)       -1111.87€
      acordó 1269.17€  ·  pagó 157.30€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 12           

┌──────────────────────────────────────────────────┐
│               RESERVA SIN DESTINO                │
└──────────────────────────────────────────────────┘
  Dinero libre: de aquí sale deuda, ahorro, o lo que decidas.
  Amanda                           396.51€
  Heri                             396.51€
──────────────────────────────────────────────────────
  TOTAL                            793.02€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 0

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 337.05€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2
  › Importe (€): 9.99
  › Concepto [variables]: apple

  ¿Quién comparte este gasto?  (por defecto: solo Amanda)
     1  Lo que diga la categoría — solo Amanda
     2  Entre todos los miembros del hogar
     3  Solo Amanda (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 1
✓ 9.99 € en variables — pagó Amanda, reparto: según la categoría

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 327.06€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2
  › Importe (€): 14.99
  › Concepto [variables]: amazon

  ¿Quién comparte este gasto?  (por defecto: solo Amanda)
     1  Lo que diga la categoría — solo Amanda
     2  Entre todos los miembros del hogar
     3  Solo Amanda (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 1
✓ 14.99 € en variables — pagó Amanda, reparto: según la categoría

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 312.07€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2
  › Importe (€): 24.95
  › Concepto [variables]: amazon prime 

  ¿Quién comparte este gasto?  (por defecto: solo Amanda)
     1  Lo que diga la categoría — solo Amanda
     2  Entre todos los miembros del hogar
     3  Solo Amanda (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 1
✓ 24.95 € en variables — pagó Amanda, reparto: según la categoría

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 287.12€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2 
  › Importe (€): 27
  › Concepto [variables]: Copas

  ¿Quién comparte este gasto?  (por defecto: solo Amanda)
     1  Lo que diga la categoría — solo Amanda
     2  Entre todos los miembros del hogar
     3  Solo Amanda (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 2
✓ 27.00 € en variables — pagó Amanda, reparto: Amanda, Heri

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 2

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 260.12€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2
  › Importe (€): 41.60
  › Concepto [variables]: Black turtle

  ¿Quién comparte este gasto?  (por defecto: solo Heri)
     1  Lo que diga la categoría — solo Heri
     2  Entre todos los miembros del hogar
     3  Solo Heri (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 2
✓ 41.60 € en variables — pagó Heri, reparto: Amanda, Heri

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 218.52€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2
  › Importe (€): 12
  › Concepto [variables]: Bizum luis copas

  ¿Quién comparte este gasto?  (por defecto: solo Amanda)
     1  Lo que diga la categoría — solo Amanda
     2  Entre todos los miembros del hogar
     3  Solo Amanda (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 2
✓ 12.00 € en variables — pagó Amanda, reparto: Amanda, Heri

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 206.52€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2
  › Importe (€): 10
  › Concepto [variables]: parking ruta

  ¿Quién comparte este gasto?  (por defecto: solo Amanda)
     1  Lo que diga la categoría — solo Amanda
     2  Entre todos los miembros del hogar
     3  Solo Amanda (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 2
✓ 10.00 € en variables — pagó Amanda, reparto: Amanda, Heri

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 196.52€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2
  › Importe (€): 7.50
  › Concepto [variables]: bebidas ruta

  ¿Quién comparte este gasto?  (por defecto: solo Amanda)
     1  Lo que diga la categoría — solo Amanda
     2  Entre todos los miembros del hogar
     3  Solo Amanda (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 2
✓ 7.50 € en variables — pagó Amanda, reparto: Amanda, Heri

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 189.02€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2
  › Importe (€): 7.39
  › Concepto [variables]: consum amanda

  ¿Quién comparte este gasto?  (por defecto: solo Amanda)
     1  Lo que diga la categoría — solo Amanda
     2  Entre todos los miembros del hogar
     3  Solo Amanda (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 1
✓ 7.39 € en variables — pagó Amanda, reparto: según la categoría

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 1

  ¿Quién ha pagado?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

  ¿En qué categoría?
     1  Fijos  queda 718.08€  ·  compartida
     2  Variables  queda 181.63€  ·  personal
     3  Reserva  queda 793.02€  ·  personal
     4  Alquiler  queda 0.00€  ·  compartida
     5  Agua  queda 35.00€  ·  compartida
     6  Luz  queda -4.25€  ·  compartida
     7  Comida  queda 650.00€  ·  compartida
     8  Internet  queda 0.00€  ·  compartida
     0  volver
  › Opción: 2
  › Importe (€): 9.99
  › Concepto [variables]: otoscopio

  ¿Quién comparte este gasto?  (por defecto: solo Amanda)
     1  Lo que diga la categoría — solo Amanda
     2  Entre todos los miembros del hogar
     3  Solo Amanda (personal, fuera del settlement)
     4  Elegir quién participa
     0  volver
  › Opción: 4
  › ¿Participa Amanda? (S/n): n
  › ¿Participa Heri? (S/n): s
✓ 9.99 € en variables — pagó Amanda, reparto: Heri

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 5

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 1

  ┌─ BALANCE DEL MES ────────────────┐
  │  Presupuestado    2538.35€  │
  │  Gastado           855.61€  │
  │  Restante         1682.74€  │
  └───────────────────────────────────┘


  ┌────────────────────────────────────────────────────────┐
  │ Categoría     │ Presup.   │ Gastado  │ Restante  │
  ├────────────────────────────────────────────────────────┤
  │ Fijos         │ 1345.33€  │ 627.25€  │ 718.08€   │
  │   · Alquiler  │ 511.00€   │ 511.00€  │ 0.00€     │
  │   · Agua      │ 35.00€    │ 0.00€    │ 35.00€    │
  │   · Luz       │ 90.00€    │ 94.25€   │ -4.25€    │
  │   · Comida    │ 650.00€   │ 0.00€    │ 650.00€   │
  │   · Internet  │ 22.00€    │ 22.00€   │ 0.00€     │
  │ Variables     │ 400.00€   │ 228.36€  │ 171.64€   │
  │ Reserva       │ 793.02€   │ 0.00€    │ 793.02€   │
  └────────────────────────────────────────────────────────┘


Por miembro — lo acordado frente a lo pagado
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda (pagado − acordado)      -612.47€
      acordó 1269.18€  ·  pagó 656.71€
  Heri (pagado − acordado)       -1070.27€
      acordó 1269.17€  ·  pagó 198.90€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 2

┌──────────────────────────────────────────────────┐
│         SETTLEMENT — GASTOS COMPARTIDOS          │
└──────────────────────────────────────────────────┘
  Heri debe 193.82€ a Amanda

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 3

┌──────────────────────────────────────────────────┐
│                GASTOS DEL PERÍODO                │
└──────────────────────────────────────────────────┘
  'Compartido' = tiene más de un participante, y solo esos entran
  en el settlement. Un gasto de un solo participante es personal.

  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ Día    │ Pagó    │ Categoría  │ Importe  │ Concepto            │ Reparto       │
  ├────────────────────────────────────────────────────────────────────────────────────────┤
  │ 06/08  │ Amanda  │ Alquiler   │ 500.00€  │ Alquiler            │ Amanda, Heri  │
  │ 06/08  │ Heri    │ Alquiler   │ 11.00€   │ alquiler            │ Amanda, Heri  │
  │ 06/08  │ Heri    │ Variables  │ 26.55€   │ Gym                 │ personal      │
  │ 06/08  │ Heri    │ Internet   │ 22.00€   │ internet            │ Amanda, Heri  │
  │ 06/08  │ Heri    │ Luz        │ 94.25€   │ luz                 │ Amanda, Heri  │
  │ 06/08  │ Heri    │ Variables  │ 3.50€    │ chiringuito el och  │ personal      │
  │ 06/08  │ Amanda  │ Variables  │ 32.90€   │ gym                 │ personal      │
  │ 06/08  │ Amanda  │ Variables  │ 9.99€    │ apple               │ personal      │
  │ 06/08  │ Amanda  │ Variables  │ 14.99€   │ amazon              │ personal      │
  │ 06/08  │ Amanda  │ Variables  │ 24.95€   │ amazon prime        │ personal      │
  │ 06/08  │ Amanda  │ Variables  │ 27.00€   │ Copas               │ Amanda, Heri  │
  │ 06/08  │ Heri    │ Variables  │ 41.60€   │ Black turtle        │ Amanda, Heri  │
  │ 06/08  │ Amanda  │ Variables  │ 12.00€   │ Bizum luis copas    │ Amanda, Heri  │
  │ 06/08  │ Amanda  │ Variables  │ 10.00€   │ parking ruta        │ Amanda, Heri  │
  │ 06/08  │ Amanda  │ Variables  │ 7.50€    │ bebidas ruta        │ Amanda, Heri  │
  │ 06/08  │ Amanda  │ Variables  │ 7.39€    │ consum amanda       │ personal      │
  │ 06/08  │ Amanda  │ Variables  │ 9.99€    │ otoscopio           │ personal      │
  └────────────────────────────────────────────────────────────────────────────────────────┘

  TOTAL GASTADO                    855.61€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 6

┌──────────────────────────────────────────────────┐
│                  QUIÉN PONE QUÉ                  │
└──────────────────────────────────────────────────┘
  Cada categoría reparte solo lo suyo — una raíz con hijas reparte
  lo que no les ha delegado, así nadie aporta dos veces.

Fijos — reparte 37.33€
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda                            18.67€
  Heri                              18.66€

Variables — reparte 400.00€
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda                           200.00€
  Heri                             200.00€

Reserva — reparte 793.02€
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda                           396.51€
  Heri                             396.51€

Alquiler — reparte 511.00€
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda                           255.50€
  Heri                             255.50€

Agua — reparte 35.00€
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda                            17.50€
  Heri                              17.50€

Luz — reparte 90.00€
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda                            45.00€
  Heri                              45.00€

Comida — reparte 650.00€
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda                           325.00€
  Heri                             325.00€

Internet — reparte 22.00€
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda                            11.00€
  Heri                              11.00€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 7

┌──────────────────────────────────────────────────┐
│                 DEUDA DECLARADA                  │
└──────────────────────────────────────────────────┘

Amanda
▸▸▸▸▸▸▸▸
    Oposición                    118.90€/mes  ·  quedan 3881.10€ en 33 cuotas  ·  abierta
    Este período: pagado 118.90€ de 118.90€ (faltan 0.00€)

Heri
▸▸▸▸▸▸
    Financiación moto            132.00€/mes  ·  quedan 264.00€ en 2 cuotas  ·  abierta
    Entierro                       8.00€/mes  ·  quedan 10000.00€ en 1250 cuotas  ·  abierta
    Este período: pagado 132.00€ de 140.00€ (faltan 8.00€)

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 12

┌──────────────────────────────────────────────────┐
│               RESERVA SIN DESTINO                │
└──────────────────────────────────────────────────┘
  Dinero libre: de aquí sale deuda, ahorro, o lo que decidas.
  Amanda                           396.51€
  Heri                             396.51€
──────────────────────────────────────────────────────
  TOTAL                            793.02€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 0

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 7

  Ahorro
     1  Crear un bucket de ahorro
     2  Ver los buckets
     3  Ver el ahorro de un miembro
     4  Ver el ahorro compartido
     0  volver
  › Opción: 0

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 3

  ¿Qué bucket?
     1  amanda's personal saving  0.00€ (sin meta)  ·  Amanda
     2  heri's personal saving  0.00€ (sin meta)  ·  Heri
     3  Colchón emergencia  0.00€ / 6000.00€  ·  Amanda, Heri
     0  volver
  › Opción: 3

  ¿Quién deposita?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1
  › Importe a depositar (€): 396.51
✓ 396.51 € depositados

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 5

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 1

  ┌─ BALANCE DEL MES ────────────────┐
  │  Presupuestado    2538.35€  │
  │  Gastado           855.61€  │
  │  Restante         1682.74€  │
  └───────────────────────────────────┘


  ┌────────────────────────────────────────────────────────┐
  │ Categoría     │ Presup.   │ Gastado  │ Restante  │
  ├────────────────────────────────────────────────────────┤
  │ Fijos         │ 1345.33€  │ 627.25€  │ 718.08€   │
  │   · Alquiler  │ 511.00€   │ 511.00€  │ 0.00€     │
  │   · Agua      │ 35.00€    │ 0.00€    │ 35.00€    │
  │   · Luz       │ 90.00€    │ 94.25€   │ -4.25€    │
  │   · Comida    │ 650.00€   │ 0.00€    │ 650.00€   │
  │   · Internet  │ 22.00€    │ 22.00€   │ 0.00€     │
  │ Variables     │ 400.00€   │ 228.36€  │ 171.64€   │
  │ Reserva       │ 793.02€   │ 0.00€    │ 793.02€   │
  └────────────────────────────────────────────────────────┘


Por miembro — lo acordado frente a lo pagado
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda (pagado − acordado)      -612.47€
      acordó 1269.18€  ·  pagó 656.71€
  Heri (pagado − acordado)       -1070.27€
      acordó 1269.17€  ·  pagó 198.90€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  ›Opción:   
"""

# El ahorro no reduce lo que debe el usuario 
""" 
┌──────────────────────────────────────────────────┐
│                 DEUDA DECLARADA                  │
└──────────────────────────────────────────────────┘

Amanda
▸▸▸▸▸▸▸▸
    Oposición                    118.90€/mes  ·  quedan 3881.10€ en 33 cuotas  ·  abierta
    Este período: pagado 118.90€ de 118.90€ (faltan 0.00€)

Heri
▸▸▸▸▸▸
    Financiación moto            132.00€/mes  ·  quedan 264.00€ en 2 cuotas  ·  abierta
    Entierro                       8.00€/mes  ·  quedan 10000.00€ en 1250 cuotas  ·  abierta
    Este período: pagado 132.00€ de 140.00€ (faltan 8.00€)

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 12

┌──────────────────────────────────────────────────┐
│               RESERVA SIN DESTINO                │
└──────────────────────────────────────────────────┘
  Dinero libre: de aquí sale deuda, ahorro, o lo que decidas.
  Amanda                           396.51€
  Heri                             396.51€
──────────────────────────────────────────────────────
  TOTAL                            793.02€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 10

  ¿De quién?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

┌──────────────────────────────────────────────────┐
│                 AHORRO DE AMANDA                 │
└──────────────────────────────────────────────────┘
  Todo esto es informativo: el ahorro es elección, no obligación.

amanda's personal saving
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Saldo                              0.00€
  Neto este período                  0.00€

Colchón emergencia
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Saldo                            396.51€
  Neto este período                396.51€

  ┌─ TOTAL DEL PERÍODO ──────────────────┐
  │  Depositado (neto)     396.51€  │
  │  Exigen las metas        0.00€  │
  └───────────────────────────────────────┘


  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 
"""

# Sospechas: En amanda se declararon varios gastos variables pero compartidos de los cuales yo le debo dinero, sin embargo,
# En su resumen se le contabiliza todo, y se le hace entender que solo le quedan 40 e para gastar, cuando quizas le queda más 
# con el dinero que yo le deba:
""" 
┌──────────────────────────────────────────────────┐
│                 ESTADO DE AMANDA                 │
└──────────────────────────────────────────────────┘

  ┌─ AMANDA ───────────────────────────┐
  │  Ingreso            1413.85€  │
  │  Le toca poner      1269.18€  │
  │  Ha pagado           656.71€  │
  │  Cuota de deuda      118.90€  │
  │  Metas de ahorro       0.00€  │
  └─────────────────────────────────────┘

  Balance (pagado − debido)       -612.47€
      En negativo, debe dinero al hogar.

  ┌────────────────────────────────────────────────────┐
  │ Categoría  │ Acordó   │ Pagó     │ Le falta  │
  ├────────────────────────────────────────────────────┤
  │ Fijos      │ 18.67€   │ 0.00€    │ 18.67€    │
  │ Variables  │ 200.00€  │ 156.71€  │ 43.29€    │
  │ Reserva    │ 396.51€  │ 0.00€    │ 396.51€   │
  │ Alquiler   │ 255.50€  │ 500.00€  │ -244.50€  │
  │ Agua       │ 17.50€   │ 0.00€    │ 17.50€    │
  │ Luz        │ 45.00€   │ 0.00€    │ 45.00€    │
  │ Comida     │ 325.00€  │ 0.00€    │ 325.00€   │
  │ Internet   │ 11.00€   │ 0.00€    │ 11.00€    │
  └────────────────────────────────────────────────────┘


  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 4

  ¿De quién?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 2

┌──────────────────────────────────────────────────┐
│                  ESTADO DE HERI                  │
└──────────────────────────────────────────────────┘

  ┌─ HERI ─────────────────────────────┐
  │  Ingreso            1124.50€  │
  │  Le toca poner      1269.17€  │
  │  Ha pagado           198.90€  │
  │  Cuota de deuda      140.00€  │
  │  Metas de ahorro       0.00€  │
  └─────────────────────────────────────┘

  Balance (pagado − debido)      -1070.27€
      En negativo, debe dinero al hogar.

  ┌───────────────────────────────────────────────────┐
  │ Categoría  │ Acordó   │ Pagó    │ Le falta  │
  ├───────────────────────────────────────────────────┤
  │ Fijos      │ 18.66€   │ 0.00€   │ 18.66€    │
  │ Variables  │ 200.00€  │ 71.65€  │ 128.35€   │
  │ Reserva    │ 396.51€  │ 0.00€   │ 396.51€   │
  │ Alquiler   │ 255.50€  │ 11.00€  │ 244.50€   │
  │ Agua       │ 17.50€   │ 0.00€   │ 17.50€    │
  │ Luz        │ 45.00€   │ 94.25€  │ -49.25€   │
  │ Comida     │ 325.00€  │ 0.00€   │ 325.00€   │
  │ Internet   │ 11.00€   │ 22.00€  │ -11.00€   │
  └───────────────────────────────────────────────────┘


  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 2

┌──────────────────────────────────────────────────┐
│         SETTLEMENT — GASTOS COMPARTIDOS          │
└──────────────────────────────────────────────────┘
  Heri debe 193.82€ a Amanda

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
"""

# Al declarar la deuda y pagarla, no lo contabiliza en reserva. Por tanto independientemente de ahorro o deuda, reserva sigue mostrando estar igual.

""" 
┌──────────────────────────────────────────────────┐
│               RESERVA SIN DESTINO                │
└──────────────────────────────────────────────────┘
  Dinero libre: de aquí sale deuda, ahorro, o lo que decidas.
  Amanda                           396.51€
  Heri                             396.51€
──────────────────────────────────────────────────────
  TOTAL                            793.02€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 0

══════════════════════════════════════════════════════
  Hogar #1  ·  Período #1 desde 06/08/2026  ·  MONTH
  Amanda, Heri  ·  ingreso del hogar 2538.35€
══════════════════════════════════════════════════════

  ¿Qué haces? (fase MONTH)
     1  Registrar un gasto
     2  Registrar un pago de deuda
     3  Depositar en un bucket
     4  Retirar de un bucket
     5  Consultar ▸
     6  Deuda ▸
     7  Ahorro ▸
     8  Cerrar el mes
     9  Salir
     0  volver
  › Opción: 5

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 1

  ┌─ BALANCE DEL MES ────────────────┐
  │  Presupuestado    2538.35€  │
  │  Gastado           855.61€  │
  │  Restante         1682.74€  │
  └───────────────────────────────────┘


  ┌────────────────────────────────────────────────────────┐
  │ Categoría     │ Presup.   │ Gastado  │ Restante  │
  ├────────────────────────────────────────────────────────┤
  │ Fijos         │ 1345.33€  │ 627.25€  │ 718.08€   │
  │   · Alquiler  │ 511.00€   │ 511.00€  │ 0.00€     │
  │   · Agua      │ 35.00€    │ 0.00€    │ 35.00€    │
  │   · Luz       │ 90.00€    │ 94.25€   │ -4.25€    │
  │   · Comida    │ 650.00€   │ 0.00€    │ 650.00€   │
  │   · Internet  │ 22.00€    │ 22.00€   │ 0.00€     │
  │ Variables     │ 400.00€   │ 228.36€  │ 171.64€   │
  │ Reserva       │ 793.02€   │ 0.00€    │ 793.02€   │
  └────────────────────────────────────────────────────────┘


Por miembro — lo acordado frente a lo pagado
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Amanda (pagado − acordado)      -612.47€
      acordó 1269.18€  ·  pagó 656.71€
  Heri (pagado − acordado)       -1070.27€
      acordó 1269.17€  ·  pagó 198.90€

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 7

┌──────────────────────────────────────────────────┐
│                 DEUDA DECLARADA                  │
└──────────────────────────────────────────────────┘

Amanda
▸▸▸▸▸▸▸▸
    Oposición                    118.90€/mes  ·  quedan 3881.10€ en 33 cuotas  ·  abierta
    Este período: pagado 118.90€ de 118.90€ (faltan 0.00€)

Heri
▸▸▸▸▸▸
    Financiación moto            132.00€/mes  ·  quedan 264.00€ en 2 cuotas  ·  abierta
    Entierro                       8.00€/mes  ·  quedan 10000.00€ en 1250 cuotas  ·  abierta
    Este período: pagado 132.00€ de 140.00€ (faltan 8.00€)

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 9

┌──────────────────────────────────────────────────┐
│                BUCKETS DE AHORRO                 │
└──────────────────────────────────────────────────┘
  amanda's personal saving           0.00€
      sin meta  ·  Amanda
  heri's personal saving             0.00€
      sin meta  ·  Heri
  Colchón emergencia   █░░░░░░░░░░░░░░░░░░░   6.61%
      396.51€ de 6000.00€  ·  Amanda, Heri

  Consultar
     1  Resumen del mes
     2  Settlement — quién debe a quién
     3  Gastos del período, uno a uno
     4  Estado de un miembro
     5  Presupuesto
     6  Quién pone qué
     7  Deuda del hogar
     8  Deuda de un miembro
     9  Buckets de ahorro
    10  Ahorro de un miembro
    11  Ahorro compartido
    12  Reserva sin destino
    13  Miembros e ingresos
     0  volver
  › Opción: 10

  ¿De quién?
     1  Amanda
     2  Heri
     0  volver
  › Opción: 1

┌──────────────────────────────────────────────────┐
│                 AHORRO DE AMANDA                 │
└──────────────────────────────────────────────────┘
  Todo esto es informativo: el ahorro es elección, no obligación.

amanda's personal saving
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Saldo                              0.00€
  Neto este período                  0.00€

Colchón emergencia
▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸
  Saldo                            396.51€
  Neto este período                396.51€

  ┌─ TOTAL DEL PERÍODO ──────────────────┐
  │  Depositado (neto)     396.51€  │
  │  Exigen las metas        0.00€  │
  └───────────────────────────────────────┘

"""