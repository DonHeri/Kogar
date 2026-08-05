from datetime import date

import psycopg2.extras

from src.models.constants import Phase, MetodoReparto
from src.models.period import Period


class PeriodRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = self.db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(self, period: Period) -> int:
        self.cursor.execute(
            """
            INSERT INTO household_periods (household_id, start_date, status, method)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                period.household_id,
                period.start_date,
                period.status.value,
                period.method.value,
            ),
        )
        return self.cursor.fetchone()["id"]

    def find_by_id(self, period_id: int) -> Period | None:
        self.cursor.execute(
            "SELECT * FROM household_periods WHERE id = %s", (period_id,)
        )
        row = self.cursor.fetchone()
        if row:
            return self._to_period(row)

    def get_current(self, household_id: int) -> Period | None:
        """Devuelve período actual"""
        self.cursor.execute(
            """
            SELECT * FROM household_periods
            WHERE household_id = %s AND status != 'closed'
            ORDER BY start_date DESC
            LIMIT 1
            """,
            (household_id,),
        )
        row = self.cursor.fetchone()
        return self._to_period(row) if row else None

    def get_last(self, household_id: int) -> Period | None:
        """Devuelve el último período cerrado"""
        self.cursor.execute(
            """
            SELECT * FROM household_periods
            WHERE household_id = %s 
                AND status = 'closed' 
                AND end_date IS NOT NULL
            ORDER BY end_date DESC
            LIMIT 1
            """,
            (household_id,),
        )
        row = self.cursor.fetchone()
        return self._to_period(row) if row else None

    def update_status(self, period_id: int, status: Phase) -> None:
        self.cursor.execute(
            "UPDATE household_periods SET status = %s WHERE id = %s",
            (status.value, period_id),
        )

    def update_method(self, period_id: int, method: MetodoReparto) -> None:
        self.cursor.execute(
            "UPDATE household_periods SET method = %s WHERE id = %s",
            (method.value, period_id),
        )

    def update_end_date(self, period_id: int, end_date: date) -> None:
        self.cursor.execute(
            "UPDATE household_periods SET end_date = %s WHERE id = %s",
            (end_date, period_id),
        )

    def _to_period(self, row: dict) -> Period:
        return Period(
            id=row["id"],
            household_id=row["household_id"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            status=Phase(row["status"]),
            method=MetodoReparto(row["method"]),
        )

    def save_agreed_contributions(
        self, period_id: int, contributions: dict[str, dict[str, int]]
    ) -> None:
        """Guarda el acuerdo desglosado de un período.

        Recibe {categoría: {miembro: céntimos}}. Se borra antes de insertar: una
        categoría que desaparece del plan tiene que desaparecer del acuerdo, y un
        ON CONFLICT solo actualiza lo que vuelve a llegar.
        """
        self.cursor.execute(
            " DELETE FROM period_agreed_contributions WHERE period_id = %s ",
            (period_id,),
        )

        member_ids = self._member_ids_by_name()

        for category_name, by_member in contributions.items():
            for full_name, amount_cents in by_member.items():
                if full_name not in member_ids:
                    raise ValueError(f"Miembro {full_name} no está en la base de datos ")
                self.cursor.execute(
                    """
                    INSERT INTO period_agreed_contributions
                        (period_id, member_id, category_name, amount_cents)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (period_id, member_ids[full_name], category_name, amount_cents),
                )

    def get_agreed_contributions(self, period_id: int) -> dict[str, dict[str, int]]:
        """Lee el acuerdo desglosado. Devuelve {categoría: {miembro: céntimos}}."""
        self.cursor.execute(
            """
            SELECT m.full_name, pac.category_name, pac.amount_cents
            FROM period_agreed_contributions pac
            INNER JOIN members m ON m.id = pac.member_id
            WHERE pac.period_id = %s
            """,
            (period_id,),
        )

        agreement: dict[str, dict[str, int]] = {}
        for row in self.cursor.fetchall():
            category = agreement.setdefault(row["category_name"], {})
            category[row["full_name"]] = row["amount_cents"]
        return agreement

    def save_percentages(self, period_id: int, percentages: dict[str, int]) -> None:
        """Guarda los porcentajes de reparto del período, en basis points.

        Los escriben dos momentos distintos: el usuario al definir un reparto
        propio durante PLANNING, y finish_planning al congelar el acuerdo. Con
        método CUSTOM son el mismo número, así que no se pisan; con los demás,
        la tabla está vacía hasta que se congela. Lo que distingue borrador de
        acuerdo es la fase del período, que ya está persistida.
        """
        member_ids = self._member_ids_by_name()

        for full_name, percentage_basis_points in percentages.items():
            if full_name not in member_ids:
                raise ValueError(f"Miembro {full_name} no está en la base de datos ")
            self.cursor.execute(
                """
                INSERT INTO period_percentages(period_id,member_id,percentage_basis_points)
                VALUES (%s,%s,%s)
                ON CONFLICT (period_id,member_id)
                DO UPDATE SET percentage_basis_points = EXCLUDED.percentage_basis_points
                """,
                (period_id, member_ids[full_name], percentage_basis_points),
            )

    def get_percentages(self, period_id: int) -> dict[str, int]:
        """Lee los porcentajes del período. Devuelve {nombre: percentage_basis_points}."""
        self.cursor.execute(
            """
            SELECT m.full_name, pp.percentage_basis_points
            FROM period_percentages pp
            INNER JOIN members m ON m.id = pp.member_id
            WHERE pp.period_id = %s
            """,
            (period_id,),
        )
        return {
            row["full_name"]: row["percentage_basis_points"]
            for row in self.cursor.fetchall()
        }

    def _member_ids_by_name(self) -> dict[str, int]:
        """{full_name: id} de todos los miembros, en una sola consulta.

        Antes se resolvía con un SELECT por fila dentro del bucle de escritura.
        """
        self.cursor.execute(" SELECT id, full_name FROM members ")
        return {row["full_name"]: row["id"] for row in self.cursor.fetchall()}
