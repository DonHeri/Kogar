from datetime import datetime
from uuid import UUID

from src.models.constants import SavingScope
from src.models.saving_bucket import SavingBucket


class BucketTracker:
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

    # ====== Validadores ======
