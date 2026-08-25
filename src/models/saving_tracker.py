from datetime import date
from uuid import UUID

from src.models.saving_bucket_tracker import SavingBucketTracker
from src.models.saving_bucket import SavingBucket


class SavingTracker:
    """
    Gestiona el ahorro del hogar. Todo el ahorro vive en buckets: no hay cuentas
    ni scope. Personal vs compartido se deriva de los owners de cada bucket
    (is_shared). El ahorro "libre" es un depósito a un bucket sin meta.

    Responsabilidades:
    - Crear y almacenar los buckets (delegado en SavingBucketTracker)
    - Exponer queries agregadas (total compartido, ahorrado por período)
    """

    def __init__(self) -> None:
        self._bucket_tracker = SavingBucketTracker()

    # ====== GESTIÓN DE BUCKETS ======
    def add_saving_bucket(self, bucket: SavingBucket) -> UUID:
        return self._bucket_tracker.add_bucket(bucket)

    def deposit_to_bucket(
        self, bucket_id: UUID, member_name: str, amount_cents: int, date=None
    ) -> None:
        self._bucket_tracker.deposit(bucket_id, amount_cents, member_name, date)

    def withdraw_from_bucket(
        self, bucket_id: UUID, member_name: str, amount_cents: int, date=None
    ) -> None:
        self._bucket_tracker.withdraw(bucket_id, amount_cents, member_name, date)

    def get_bucket_by_id(self, bucket_id: UUID) -> SavingBucket:
        return self._bucket_tracker.get_bucket_by_id(bucket_id)

    def get_all_buckets(self) -> dict[UUID, SavingBucket]:
        return self._bucket_tracker.get_all_buckets()

    def get_buckets_by_member(self, member_name: str) -> dict[UUID, SavingBucket]:
        return self._bucket_tracker.get_bucket_by_member(member_name)

    # ====== QUERIES ======

    def get_total_shared(self) -> int:
        """Total ahorrado en buckets compartidos (todos los miembros)."""
        return sum(
            bucket.balance
            for bucket in self._bucket_tracker.get_all_buckets().values()
            if bucket.is_shared
        )

    def get_member_saved_in_period(
        self, member_name: str, start_date: date, end_date: date
    ) -> int:
        """Neto ahorrado por un miembro (todos sus buckets) en el rango del período.
        Los retiros cuentan en negativo (BucketEntry negativa)."""
        total = 0
        for bucket in self._bucket_tracker.get_bucket_by_member(member_name).values():
            for entry in bucket.entries:
                if (
                    entry.member_name == member_name
                    and start_date <= entry.date.date() <= end_date
                ):
                    total += entry.amount_cents
        return total

    def get_shared_by_period(
        self, start_date: date, end_date: date
    ) -> dict[str, list]:
        """Movimientos en buckets compartidos dentro del rango, agrupados por miembro."""
        result: dict[str, list] = {}
        for bucket in self._bucket_tracker.get_all_buckets().values():
            if not bucket.is_shared:
                continue
            for entry in bucket.entries:
                if start_date <= entry.date.date() <= end_date:
                    result.setdefault(entry.member_name, []).append(entry)
        return result
