import psycopg2


class HouseholdRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = db.cursor()

    def add_household(self) -> int | None:
        try:
            self.cursor.execute(
                """  
                INSERT INTO households DEFAULT VALUES RETURNING id;
                """
            )
            household_id = self.cursor.fetchone()[0]
            self.db.commit()
            return household_id
        except Exception as e:
            self.db.rollback()
            print("Error:", e)

    def del_household(self, household_id: int):
        try:
            self.cursor.execute(
                "DELETE FROM households WHERE id = (%s);", (household_id,)
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print("Error:", e)

    def list_households(self):
        try:
            self.cursor.execute("SELECT * FROM households;")
            return self.cursor.fetchall()
        except Exception as e:
            print("Error:", e)

    def get_household(self, household_id: int):
        try:
            self.cursor.execute(
                "SELECT * FROM households WHERE id = (%s);", (household_id,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            print("Error:", e)
