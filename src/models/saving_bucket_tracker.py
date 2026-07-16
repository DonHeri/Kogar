from datetime import date, datetime
from uuid import UUID


from src.models.saving_bucket import SavingBucket


class SavingBucketTracker:
    """
    Gestiona los Buckets de ahorro de todos los miembros del hogar.

    Responsabilidades:
    - Crear y almacenar los Buckets
    - Exponer queries agregadas sobre Buckets
    - Filtrar por miembro
    """

    def __init__(self) -> None:
        self.buckets: dict[UUID, SavingBucket] = {}

    # ====== GESTIÓN DE BUCKETS ======
    def add_bucket(self, bucket: SavingBucket) -> UUID:
        """Crea y registra un nuevo bucket. Retorna su UUID."""
        self.buckets[bucket.id] = bucket
        return bucket.id

    def deposit(
        self,
        bucket_id: UUID,
        amount_cents: int,
        member_name: str,
        date: datetime | None = None,
    ) -> None:
        """
        Registra un depósito en un bucket.

        Args:
            bucket_id: Identificador del bucket en el tracker
            amount_cents: Monto en céntimos, debe ser positivo
            member_name: Nombre del miembro que hace el depósito
            date: Fecha del depósito. Si no se indica, usa la fecha actual
        """
        self.get_bucket_by_id(bucket_id).deposit(
            amount_cents=amount_cents, member_name=member_name, date=date
        )

    def withdraw(
        self,
        bucket_id: UUID,
        amount_cents: int,
        member_name: str,
        date: datetime | None = None,
    ) -> None:
        """
        Registra un retiro de un bucket.

        Args:
            bucket_id: Identificador del bucket en el tracker
            amount_cents: Monto en céntimos, debe ser positivo
            member_name: Nombre del miembro que hace el retiro
            date: Fecha del retiro. Si no se indica, usa la fecha actual
        """
        self.get_bucket_by_id(bucket_id).withdraw(
            amount_cents=amount_cents, member_name=member_name, date=date
        )

    # ====== QUERIES ======
    def get_all_buckets(self) -> dict[UUID, SavingBucket]:
        """Retorna una copia de todos los buckets registrados."""
        return self.buckets.copy()

    def get_bucket_by_id(self, bucket_id: UUID) -> SavingBucket:
        """Retorna el bucket asociado al UUID. Lanza ValueError si no existe."""
        if bucket_id not in self.buckets:
            raise ValueError(f"Bucket {bucket_id} no existe")
        return self.buckets[bucket_id]

    def get_bucket_by_member(self, member_name: str) -> dict[UUID, SavingBucket]:
        """Retorna todos los buckets en los que participa un miembro."""
        return {
            id: bucket
            for id, bucket in self.buckets.items()
            if member_name in bucket.owners
        }

    def get_total_shared(self) -> int:
        """Total ahorrado en buckets compartidos (todos los miembros)."""
        return sum(bucket.balance for bucket in self.buckets.values() if bucket.is_shared)

    def get_member_saved_in_period(
        self, member_name: str, start_date: date, end_date: date
    ) -> int:
        """Neto ahorrado por un miembro (todos sus buckets) en el rango del período.
        Los retiros cuentan en negativo (BucketEntry negativa)."""
        total = 0
        for bucket in self.get_bucket_by_member(member_name).values():
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
        for bucket in self.buckets.values():
            if not bucket.is_shared:
                continue
            for entry in bucket.entries:
                if start_date <= entry.date.date() <= end_date:
                    result.setdefault(entry.member_name, []).append(entry)
        return result

    # ====== Validadores ======
