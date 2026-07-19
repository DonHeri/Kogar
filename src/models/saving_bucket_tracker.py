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

    def total_required_contribution_by_member(self, member_name: str) -> int:
        """Suma de lo que exigirían las metas con deadline del miembro, ahora mismo.
        Informativo — no es un compromiso, solo agrega lo que ya calcula cada bucket."""
        total = sum(
            bucket.required_monthly_contribution or 0
            for bucket in self.buckets.values()
            if member_name in bucket.owners
        )
        return total

    def member_saving_summary(
        self, member_name: str, start_date: date, end_date: date
    ) -> dict:
        """Resumen de ahorro de un miembro: detalle por bucket (meta, deadline, cuota
        informativa, lo depositado este período) + totales. Espeja member_debt_summary,
        pero sin 'committed' — aquí nada se compromete de antemano.

        Returns:
            {
              "buckets": {bucket_id: {
                  "name", "goal", "deadline", "balance",
                  "remaining_goal", "required_this_month", "paid_this_period",
              }},
              "totals": {"paid_this_period": int, "required_this_month": int},
            }
        """
        buckets = {}
        total_paid = 0
        total_required = 0
        for id, bucket in self.get_bucket_by_member(member_name).items():
            paid = bucket.get_period_deposits(start_date, end_date)
            required = bucket.required_monthly_contribution
            buckets[id] = {
                "name": bucket.bucket_name,
                "goal": bucket.goal,
                "deadline": bucket.deadline,
                "balance": bucket.balance,
                "remaining_goal": bucket.remaining_goal,
                "required_this_month": required,
                "paid_this_period": paid,
            }
            total_paid += paid
            total_required += required or 0

        return {
            "buckets": buckets,
            "totals": {
                "paid_this_period": total_paid,
                "required_this_month": total_required,
            },
        }

    # ====== QUERIES ======
    def get_default_bucket_by_member(
        self, member_name: str
    ) -> dict[UUID, SavingBucket] | None:
        """Devuelve el bucket por defecto de un miembro. Si no tiene devuelve None"""
        default_bucket = {
            id: bucket
            for id, bucket in self.buckets.items()
            if member_name in bucket.owners and bucket.is_default
        }
        if default_bucket:
            return default_bucket
        else:
            return None

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
        return sum(
            bucket.balance for bucket in self.buckets.values() if bucket.is_shared
        )

    def get_shared_buckets(self, participant: str) -> dict[UUID, SavingBucket]:
        shared_buckets = {}
        for id, bucket in self.buckets.items():
            if participant in bucket.owners and bucket.is_shared:
                shared_buckets[id] = bucket

        return shared_buckets

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

    def get_shared_by_period(self, start_date: date, end_date: date) -> dict[str, list]:
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
