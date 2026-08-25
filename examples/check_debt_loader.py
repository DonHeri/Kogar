"""
PLANTILLA — comprobar la hidratación de deuda mientras se construye.

No es un smoke test del flujo completo (para eso está full_month_simulation.py).
Es un script mínimo: mete un household + miembro + un DebtBucket con un pago
directo por repositorio, y te deja un hueco marcado para llamar a tu
load_with_debts / _hydrate_debts en cuanto los tengas escritos.

No persiste nada real: hace rollback al final, así que puedes correrlo las
veces que haga falta sin ensuciar la BD de desarrollo.
"""

from datetime import date, datetime

from src.models.member import Member
from src.models.period import Period
from src.models.constants import Phase, MetodoReparto
from src.models.debt_bucket import DebtBucket

from src.storage.household_repository import HouseholdRepository
from src.storage.member_repository import MemberRepository
from src.storage.period_repository import PeriodRepository
from src.storage.budget_categories_repository import BudgetCategoryRepository
from src.storage.expense_repository import ExpenseRepository
from src.storage.debt_bucket_repository import DebtBucketRepository
from src.storage.debt_entry_repository import DebtEntryRepository
from src.workflow.household_loader import HouseholdLoader
from src.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

import psycopg2

conn = psycopg2.connect(
    database=DB_NAME, user=DB_USER, host=DB_HOST, password=DB_PASSWORD, port=DB_PORT
)

try:
    household_repo = HouseholdRepository(conn)
    member_repo = MemberRepository(conn)
    period_repo = PeriodRepository(conn)
    budget_categories_repo = BudgetCategoryRepository(conn)
    expense_repo = ExpenseRepository(conn)
    debt_bucket_repo = DebtBucketRepository(conn)
    debt_entry_repo = DebtEntryRepository(conn)

    # =============================================
    # SETUP — datos mínimos directos por repositorio
    # =============================================

    household_id = household_repo.save()

    heri = Member(name="Heri")
    heri.add_incomes(300000)
    heri_id = member_repo.save(member=heri, household_id=household_id)
    member_ids = {"heri": heri_id}

    period = Period(
        household_id=household_id,
        start_date=date.today(),
        status=Phase.MONTH,
        method=MetodoReparto.PROPORTIONAL,
    )
    period_id = period_repo.save(period)

    bucket = DebtBucket(
        debt_bucket_name="financiacion moto",
        principal_cents=350000,
        owner="heri",
        installment_cents=13080,
        description="Financiación moto HONDA PCX 125",
    )
    bucket_id = debt_bucket_repo.save(
        debt_bucket=bucket, household_id=household_id, members_ids=member_ids
    )

    bucket.pay(amount_cents=13080, member_name="heri", date=datetime.now())
    entry = bucket.entries[-1]
    debt_entry_repo.save(
        debt_entry=entry,
        debt_bucket_id=bucket_id,
        period_id=period_id,
        members_ids=member_ids,
    )

    print(f"household_id={household_id} period_id={period_id} bucket_id={bucket_id}")
    print(f"En BD: 1 bucket ({bucket.bucket_name}), 1 pago de {entry.amount_cents}¢")

    # =============================================
    # AQUÍ — cuando tengas load_with_debts / _hydrate_debts
    # =============================================

    loader = HouseholdLoader(
        household_repo=household_repo,
        member_repo=member_repo,
        period_repo=period_repo,
        budget_categories_repo=budget_categories_repo,
        expense_repository=expense_repo,
        debt_bucket_repository=debt_bucket_repo,
        debt_entry_repository=debt_entry_repo,
    )

    # TODO: descomenta y adapta cuando exista load_with_debts
    # household, member_ids, phase = loader.load_with_debts(
    #    household_id=household_id, period_id=period_id
    # )

    loader.load_with_debts(household_id=household_id, period_id=period_id)

    # rehydrated_bucket = household.debt_bucket_tracker.get_bucket_by_id(bucket_id)
    # print(f"Rehidratado: {rehydrated_bucket.bucket_name}")
    # print(f"  id coincide: {rehydrated_bucket.id == bucket_id}")
    # print(f"  total_paid: {rehydrated_bucket.total_paid} (esperado: 13080)")
    # print(f"  remaining_balance: {rehydrated_bucket.remaining_balance} (esperado: 336920)")
    # print(f"  nº entries: {len(rehydrated_bucket.entries)} (esperado: 1)")
    # print(f"  entry.id coincide: {rehydrated_bucket.entries[0].id == entry.id}")

finally:
    conn.rollback()
    conn.close()
