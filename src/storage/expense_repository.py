import psycopg2
import psycopg2.extras
from uuid import UUID

from src.models.expense import Expense


class ExpenseRepository:
    def __init__(self, db) -> None:
        psycopg2.extras.register_uuid()
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(
        self, expense: Expense, period_id: int, member_ids: dict[str, int]
    ) -> UUID:
        """Inserta en expenses y luego por cada nombre en expense.participants busca su member_id e inserta en expense_participants. Devuelve el expense_id."""
        expense_id = expense.id
        amount_cents = expense.amount
        payer_id = member_ids[expense.member]
        category = expense.category.name
        description = expense.description
        expense_date = expense.date
        self.cursor.execute(
            """
            INSERT INTO expenses (id, period_id, payer_id, amount_cents, category, description, expense_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                expense_id,
                period_id,
                payer_id,
                amount_cents,
                category,
                description,
                expense_date,
            ),
        )

        for member in expense.participants:
            self.cursor.execute(
                """
                INSERT INTO expense_participants (expense_id,member_id,weight)
                VALUES (%s,%s,%s)
                """,
                (expense_id, member_ids[member], expense.weights[member]),
            )

        return expense_id

    def find_with_participants(self, period_id: int) -> list[dict]:
        """JOIN entre expenses, expense_participants y members para que cada resultado
        incluya la lista de participantes y el peso de cada uno.

        weights viene como dict {nombre: basis_points}: un array paralelo a
        participants dependería de que las dos agregaciones ordenen igual, y eso
        Postgres no lo garantiza.
        """
        self.cursor.execute(
            """
            SELECT e.*,
                array_agg(m.full_name) AS participants,
                json_object_agg(m.full_name, ep.weight) AS weights
            FROM expenses e
            JOIN expense_participants ep ON ep.expense_id = e.id
            JOIN members m ON m.id = ep.member_id
            WHERE e.period_id = (%s)
            GROUP BY e.id
            """,
            (period_id,),
        )
        expenses = self.cursor.fetchall()
        return expenses

    def find_by_period(self, period_id) -> list[dict]:
        """SELECT simple sobre expenses filtrado por period_id."""
        self.cursor.execute(
            """ 
            SELECT * FROM expenses e WHERE e.period_id = (%s)
            """,
            (period_id,),
        )
        return self.cursor.fetchall()
