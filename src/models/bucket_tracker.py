from uuid import UUID
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
        self._buckets: dict[UUID, SavingBucket] = {}

    def add_bucket(self, id: UUID, bucket: SavingBucket) -> None:
        self._buckets[id] = bucket

    def get_all_buckets(self) -> dict[UUID, SavingBucket]:
        return self._buckets.copy()

    def get_bucket_by_id(self, bucket_id: UUID) -> SavingBucket:
        if bucket_id not in self._buckets:
            raise ValueError(f"Bucket {bucket_id} no existe")
        return self._buckets[bucket_id]

    def get_bucket_by_member(self, member_name: str) -> dict[UUID, SavingBucket]:
        """Retorna todos los buckets en los que participa un miembro"""
        return {
            id: bucket
            for id, bucket in self._buckets.items()
            if member_name in bucket.owners
        }
