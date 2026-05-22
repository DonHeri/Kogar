import psycopg2
import psycopg2.extras


class HouseholdRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def add_household(self) -> int | None:
        self.cursor.execute(
            """  
            INSERT INTO households DEFAULT VALUES RETURNING id;
            """
        )
        household_id = self.cursor.fetchone()["id"]
        return household_id

    def del_household(self, household_id: int):

        self.cursor.execute("DELETE FROM households WHERE id = (%s);", (household_id,))

    def list_households(self):

        self.cursor.execute("SELECT * FROM households;")
        return self.cursor.fetchall()

    def get_household(self, household_id: int):

        self.cursor.execute(
            "SELECT * FROM households WHERE id = (%s);", (household_id,)
        )
        return self.cursor.fetchone()
