import psycopg2
import psycopg2.extras

from src.models.budget_category import BudgetCategory


class BudgetCategoryRepository:
    def __init__(self, db) -> None:

        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(self, household_period_id: int, budget_category: BudgetCategory) -> int:
        self.cursor.execute(
            """
            INSERT INTO budget_categories (household_period_id, name, is_shared, planned_amount, parent_name)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                household_period_id,
                budget_category.name,
                budget_category.is_shared,
                budget_category.planned_amount,
                budget_category.parent,
            ),
        )
        return self.cursor.fetchone()["id"]

    def find_by_id(self, category_id: int) -> dict:
        self.cursor.execute(
            """ SELECT * FROM budget_categories WHERE id = (%s) """,
            (category_id,),
        )
        return self.cursor.fetchone()

    def find_by_period(self, period_id: int) -> list[dict]:
        self.cursor.execute(
            """ SELECT * FROM budget_categories WHERE household_period_id = (%s) """,
            (period_id,),
        )
        return self.cursor.fetchall()
