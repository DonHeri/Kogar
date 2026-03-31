from src.models.bucket_entry import BucketEntry
from src.models.saving_bucket import SavingBucket
from datetime import datetime
from uuid import UUID


class BucketTracker:
    """
    Gestiona los Buckets de ahorro de todos los miembros del hogar.

    Responsabilidades:
    - Crear y almacenar los Buckets
    - Exponer queries agregadas sobre Buckets compartido entre los miembros
    - Filtrar movimientos por miembro, destino y mes

    """

    def __init__(self) -> None:
        self._buckets: dict[UUID, SavingBucket] = {}


