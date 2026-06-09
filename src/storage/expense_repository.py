import psycopg2
import psycopg2.extras
from src.models.expense import Expense


class ExpenseRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(
        self, expense: Expense, period_id: int, member_ids: dict[str, int]
    ) -> int:
        """Inserta en expenses y luego por cada nombre en expense.participants busca su member_id e inserta en expense_participants. Devuelve el expense_id."""
        amount_cents = expense.amount
        payer_id = member_ids[expense.member]
        category = expense.category.name
        description = expense.description
        expense_date = expense.date
        self.cursor.execute(
            """ 
            INSERT INTO expenses (period_id, payer_id, amount_cents, category, description, expense_date)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (period_id, payer_id, amount_cents, category, description, expense_date),
        )
        expense_id = self.cursor.fetchone()["id"]

        for member in expense.participants:  # TODO
            self.cursor.execute(
                """ 
                INSERT INTO expense_participants (expense_id,member_id)
                VALUES (%s,%s)
                """,
                (expense_id, member_ids[member]),
            )

        return expense_id

    def find_with_participants(self, period_id: int) -> list[dict]:
        """JOIN entre expenses, expense_participants y members para que cada resultado incluya la lista de participantes"""
        self.cursor.execute(
            """ 
            SELECT e.*,
                array_agg(m.full_name) AS participants
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

