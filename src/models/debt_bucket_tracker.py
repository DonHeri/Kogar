from src.models.debt_bucket import DebtBucket
from uuid import UUID
from datetime import datetime, date


class DebtBucketTracker:
    """
    Gestiona los Buckets de deuda de todos los miembros del hogar.

    Responsabilidades:
    - Crear y almacenar los Buckets
    - Exponer queries agregadas sobre Buckets
    - Filtrar por miembro
    """

    def __init__(self):

        self.buckets: dict[UUID, DebtBucket] = {}

    # ====== GESTIÓN DE BUCKETS ======
    def add_bucket(self, bucket: DebtBucket) -> UUID:
        """Crea y registra un nuevo bucket de deuda. Retorna su UUID"""
        self.buckets[bucket.id] = bucket
        return bucket.id

    def pay(
        self,
        bucket_id: UUID,
        amount_cents: int,
        member_name: str,
        date: datetime | None = None,
    ) -> None:
        """
        Representa un pago sobre un bucket de deuda

        Args:
            bucket_id: identificador del bucket
            amount_cent: cantidad a pagar en céntimos
            member_name: nombre del pagados
            date: Se puede dar, o se autogenera. Fecha del pago
        """
        self.validate_bucket_exist(bucket_id)

        self.get_bucket_by_id(bucket_id).pay(
            amount_cents=amount_cents, member_name=member_name, date=date
        )

    # ====== QUERIES ======

    def member_debt_summary(
        self, member_name: str, start_date: date, end_date: date | None = None
    ) -> dict:
        """Resumen completo de la deuda de un miembro: una sola llamada con toda la foto.

        Devuelve el detalle de cada bucket
        (histórico de la deuda + balance del período) y los totales del período.

        Returns:
            {
              "buckets": {bucket_id: {
                  "name", "principal", "installment",
                  "total_paid", "remaining_balance", "remaining_installments",
                  "is_closed", "period": {"committed", "paid", "remaining"},
              }},
              "totals": {"committed", "paid", "remaining"},  # del período
            }
        """
        if end_date is None:
            end_date = date.today()

        buckets: dict = {}
        totals = {"committed": 0, "paid": 0, "remaining": 0}

        for id, bucket in self.get_bucket_by_member(member_name).items():
            period = bucket.get_period_balance(start_date=start_date, end_date=end_date)
            buckets[id] = {
                "name": bucket.name,
                "principal": bucket.principal_cents,
                "installment": bucket.installment_cents,
                "total_paid": bucket.total_paid,
                "remaining_balance": bucket.remaining_balance,
                "remaining_installments": bucket.remaining_installments,
                "is_closed": bucket.is_closed,
                "period": period,
            }
            for key in totals:
                totals[key] += period[key]

        return {"buckets": buckets, "totals": totals}

    def total_expected_installment_by_member(self, member_name: str) -> int:
        return sum(
            bucket.next_installment
            for bucket in self.buckets.values()
            if bucket.owner == member_name
        )

    def get_all_buckets(self) -> dict[UUID, DebtBucket]:
        """Retorna una copia de todos los buckets registrados."""
        return self.buckets.copy()

    def get_bucket_by_id(self, bucket_id: UUID) -> DebtBucket:
        """Retorna el bucket asociado al UUID. Lanza ValueError si no existe."""
        if bucket_id not in self.buckets:
            raise ValueError(f"Bucket {bucket_id} no existe")
        return self.buckets[bucket_id]

    def get_bucket_by_member(self, member_name: str) -> dict[UUID, DebtBucket]:
        """Retorna todos los buckets de los que un miembro es owner."""
        return {
            id: bucket
            for id, bucket in self.buckets.items()
            if bucket.owner == member_name
        }

    def set_bucket_installment(self, bucket_id: UUID, amount_cents: int):
        """Fija la cuota mensual de un bucket (la settea el usuario)"""
        self.validate_bucket_exist(bucket_id)
        self.buckets[bucket_id].set_installment(amount_cents)

    def remove_bucket(self, bucket_id: UUID):
        """Método para eliminar bucket"""
        self.validate_bucket_exist(bucket_id)
        del self.buckets[bucket_id]

    # ====== VALIDADORES ======
    def validate_bucket_exist(self, bucket_id: UUID):
        if bucket_id not in self.buckets:
            raise ValueError("El id introducido no pertenece a ningún bucket")
