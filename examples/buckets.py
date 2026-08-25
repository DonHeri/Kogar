from src.models.bucket_entry import BucketEntry
from src.models.bucket_tracker import BucketTracker
from src.models.saving_bucket import SavingBucket
from src.models.constants import SavingScope
from datetime import datetime


# ====== Buckets SHARED ======

viaje_japon = SavingBucket(
    bucket_name="Viaje a Japón",
    deadline=datetime(2027, 4, 23),
    goal_cents=280_000,
    scope=SavingScope.SHARED,
    owners=["amanda", "heri"],
)

fondo_emergencia = SavingBucket(
    bucket_name="Fondo de emergencia",
    goal_cents=600_000,
    scope=SavingScope.SHARED,
    owners=["amanda", "heri"],
    description="3 meses de gastos fijos cubiertos",
)

nuevo_sofa = SavingBucket(
    bucket_name="Sofá nuevo",
    deadline=datetime(2026, 9, 1),
    goal_cents=80_000,
    scope=SavingScope.SHARED,
    owners=["amanda", "heri"],
    description="Para el salón reformado",
)

# ====== Buckets PERSONAL ======

mac_heri = SavingBucket(
    bucket_name="MacBook Pro",
    deadline=datetime(2026, 11, 1),
    goal_cents=220_000,
    scope=SavingScope.PERSONAL,
    owners=["heri"],
)

curso_amanda = SavingBucket(
    bucket_name="Curso de diseño UX",
    goal_cents=45_000,
    scope=SavingScope.PERSONAL,
    owners=["amanda"],
    description="Máster online",
)

# ====== Registrar en tracker ======

tracker = BucketTracker()
for bucket in [viaje_japon, fondo_emergencia, nuevo_sofa, mac_heri, curso_amanda]:
    tracker.add_bucket(bucket)

# ====== Depósitos de prueba ======

viaje_japon.deposit(50_000, "heri", datetime(2026, 1, 15))
viaje_japon.deposit(40_000, "amanda", datetime(2026, 2, 1))
viaje_japon.deposit(30_000, "heri", datetime(2026, 3, 10))
fondo_emergencia.deposit(100_000, "heri", datetime(2026, 1, 5))
fondo_emergencia.deposit(80_000, "amanda", datetime(2026, 2, 5))
nuevo_sofa.deposit(20_000, "heri", datetime(2026, 3, 1))
nuevo_sofa.deposit(15_000, "amanda", datetime(2026, 3, 1))
nuevo_sofa.withdraw(5_000, "heri", datetime(2026, 3, 20))
mac_heri.deposit(60_000, "heri", datetime(2026, 1, 31))
mac_heri.deposit(60_000, "heri", datetime(2026, 2, 28))
curso_amanda.deposit(20_000, "amanda", datetime(2026, 3, 15))

# ====== Output ======

print("=== Todos los buckets ===\n")
for id, bucket in tracker.get_all_buckets().items():
    print(bucket)
    print()

print("=== Buckets de heri ===\n")
for name, bucket in tracker.get_bucket_by_member("heri").items():
    print(bucket)
    print()

print("=== Buckets de amanda ===\n")
for name, bucket in tracker.get_bucket_by_member("amanda").items():
    print(bucket)
    print()
