"""
DRILLS — Ejercicios entrevesados para comprobar que dominas tu propio sistema.

Setup ya hecho (conexión + instancias). A partir de ahí, cada bloque es un
ejercicio: escribe tú el código donde dice "TU CÓDIGO". Los ejercicios saltan
entre deuda / ahorro / gastos a propósito, no van agrupados por feature — así
no puedes resolverlos con el bloque anterior recién copiado en la cabeza.

Algunos llevan "PREDICCIÓN:" — antes de escribir el código, responde en un
comentario qué crees que va a pasar. Luego ejecuta y comprueba si acertaste.
Los marcados "TRAMPA" están para que la caguen a propósito: si no la lías al
menos una vez, no estás poniendo a prueba lo que crees saber, solo lo que ya
sabías que sabías.

No hay solucionario. Cuando lo tengas hecho, tráelo con /revisar.
"""

from datetime import date, datetime

from src.models.budget import Budget
from src.models.constants import MetodoReparto
from src.models.debt_bucket import DebtBucket
from src.models.debt_bucket_tracker import DebtBucketTracker
from src.models.expense_tracker import ExpenseTracker
from src.models.household import Household
from src.models.saving_bucket import SavingBucket
from src.models.saving_bucket_tracker import SavingBucketTracker
from src.workflow.workflow_manager import WorkflowManager

# Persistencia
from src.storage.connection import DatabaseConnection
from src.storage.member_repository import MemberRepository
from src.storage.household_repository import HouseholdRepository
from src.storage.period_repository import PeriodRepository
from src.storage.debt_entry_repository import DebtEntryRepository
from src.storage.budget_categories_repository import BudgetCategoryRepository
from src.storage.expense_repository import ExpenseRepository
from src.storage.income_entry_repository import IncomeEntryRepository
from src.storage.saving_bucket_repository import SavingBucketRepository
from src.storage.saving_bucket_entry_repository import SavingBucketEntryRepository
from src.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

with DatabaseConnection(
    database=DB_NAME,
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
) as conn:
    household_repo = HouseholdRepository(conn)
    member_repo = MemberRepository(conn)
    period_repo = PeriodRepository(conn)
    debt_repo = DebtEntryRepository(conn)
    budget_categories_repo = BudgetCategoryRepository(conn)
    expense_repo = ExpenseRepository(conn)
    income_entry_repo = IncomeEntryRepository(conn)
    saving_bucket_repo = SavingBucketRepository(conn)
    saving_bucket_entry_repo = SavingBucketEntryRepository(conn)

    household = Household(
        budget=Budget(),
        expense_tracker=ExpenseTracker(),
        saving_bucket_tracker=SavingBucketTracker(),
        debt_bucket_tracker=DebtBucketTracker(),
        method=MetodoReparto.PROPORTIONAL,
    )
    wm = WorkflowManager(
        household=household,
        household_repo=household_repo,
        member_repo=member_repo,
        period_repo=period_repo,
        debt_repo=debt_repo,
        budget_categories_repository=budget_categories_repo,
        expense_repo=expense_repo,
        income_entry_repo=income_entry_repo,
        saving_bucket_repo=saving_bucket_repo,
        saving_bucket_entry_repo=saving_bucket_entry_repo,
    )

    # ============================================================
    # EJERCICIO 1 — Registra dos miembros con ingresos distintos.
    # ============================================================
    # TU CÓDIGO
    wm.register_member(name="juan")
    wm.register_member(name="maria")
    wm.set_member_incomes(name="juan", amount_euros=1750.56)
    wm.set_member_incomes(name="juan", amount_euros=1673.86)

    # ============================================================
    # EJERCICIO 2 — TRAMPA. Antes de cerrar el registro, intenta declarar
    # una deuda para uno de los miembros (wm.add_debt_bucket).
    # PREDICCIÓN: ¿qué excepción esperas? ¿la lanza Household o WorkflowManager?
    # ============================================================
    # TU CÓDIGO
    wm.finish_registration()
    wm.add_debt_bucket(
        name="financiación moto",
        owner="juan",
        principal_euros=3250.46,
        installment_euros=154.76,
    )
    """ wm debe mandar una excepción ya que para pagar una deuda primero hay que haber pasado por planning y estar en fase month """

    # ============================================================
    # EJERCICIO 3 — Cierra el registro (finish_registration) y asigna
    # presupuesto a fijos / variables / reserva (set_budget_by_percentages
    # o set_budget_for_category, tú decides).
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 4 — Declara una deuda personal para un miembro: principal
    # + cuota mensual (la que él "decide", no la calculada).
    # PREGUNTA (respóndetela en un comentario, no hace falta código):
    # ¿por qué add_debt_bucket no te pide el número de cuotas?
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 5 — Crea un bucket de ahorro SIN meta (el colchón) para
    # un miembro y deposita algo.
    # PREDICCIÓN: ¿qué devuelve bucket.goal? ¿Y bucket.is_shared?
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 6 — TRAMPA. Declara una segunda deuda para el MISMO
    # miembro del ejercicio 4, con una cuota que sume junto a la primera
    # más de lo que le toca de reserva.
    # PREDICCIÓN: ¿qué método detecta este exceso? ¿en qué momento hay que
    # llamarlo para que sirva de algo (antes o después de finish_planning)?
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 7 — Crea un bucket de ahorro COMPARTIDO con meta, entre
    # los dos miembros.
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 8 — TRAMPA. Intenta que un miembro que NO es owner del
    # bucket del ejercicio 7 deposite en él (invéntate un tercer nombre).
    # PREDICCIÓN: ¿qué excepción salta y desde qué capa (SavingBucket,
    # SavingBucketTracker, Household o WorkflowManager)?
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 9 — auto_assign_saving_goals() y valida que deuda + ahorro
    # no superan la reserva de cada miembro. Luego finish_planning().
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 10 — Registra un gasto compartido y uno personal, sin
    # pasar participants explícitos.
    # PREGUNTA: ¿de qué depende que un gasto sea compartido o no si no
    # se lo dices tú?
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 11 — Paga la cuota completa de la deuda del ejercicio 4.
    # Luego haz un segundo pago sobre la misma deuda que la sobrepague.
    # PREDICCIÓN: ¿lanza excepción el sobrepago? ¿Por qué (qué decisión
    # de diseño es esta y dónde la tomaste)?
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 12 — TRAMPA. Justo después del sobrepago del ejercicio 11,
    # consulta wm.get_debt_status(member).
    # PREDICCIÓN: ¿qué signo tiene "remaining" dentro de "totals"? ¿Por
    # qué no se capa a 0?
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 13 — TRAMPA. En el bucket compartido del ejercicio 7,
    # que un miembro intente retirar más de lo que ÉL aportó, aunque el
    # bucket en total tenga saldo de sobra (porque el otro miembro sí
    # aportó bastante).
    # PREDICCIÓN: ¿por qué falla si el saldo total del bucket alcanza?
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 14 — Consulta wm.get_settlement().
    # PREGUNTA: ¿los gastos personales (no compartidos) entran en este
    # cálculo? ¿Y los depósitos a buckets de ahorro?
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 15 — finish_month() y consulta wm.get_month_summary().
    # PREGUNTA: ¿qué representa exactamente "missing_money"? Dalo con
    # un número concreto de tu propia simulación, no en abstracto.
    # ============================================================
    # TU CÓDIGO

    # ============================================================
    # EJERCICIO 16 — TRAMPA, la última. Ya en CLOSING, intenta
    # wm.add_debt_bucket(...) otra vez.
    # PREDICCIÓN: ¿te frena algo? ¿Household sabe en qué fase está el
    # hogar, o esa responsabilidad es solo de WorkflowManager?
    # ============================================================
    # TU CÓDIGO
