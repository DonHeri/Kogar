import psycopg2

from src.models.member import Member
from src.utils.text import normalize_name


class MemberRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cur = self.db.cursor()

    def add_member(self, member: Member, household_id: int, status: bool = True):
        full_name = member.name
        monthly_income = member.monthly_income
        try:
            self.cur.execute(
                "INSERT INTO members (full_name,monthly_income,status,household_id) VALUES (%s,%s,%s,%s)",
                (full_name, monthly_income, status, household_id),
            )
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            print("ERROR", e)

    def del_member(self, member_id: int):
        try:
            self.cur.execute("DELETE FROM members WHERE id = (%s)", (member_id,))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print("ERROR", e)

    def list_members(self, household_id: int):
        try:
            self.cur.execute(
                "SELECT * FROM members WHERE household_id = (%s)", (household_id,)
            )
            return self.cur.fetchall()
        except Exception as e:
            print("ERROR", e)

    def rename(self, new_name: str, member_id: int):

        normalized = normalize_name(new_name)
        if not normalized:
            raise ValueError("El nombre del miembro no puede estar vacío")
        try:
            self.cur.execute(
                "UPDATE members SET full_name = (%s) WHERE id = (%s)",
                (normalized, member_id),
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print("ERROR", e)

    def change_incomes(self, new_incomes_cents: int, member_id: int):
        self._validate_income(new_incomes_cents)
        try:
            self.cur.execute(
                "UPDATE members SET monthly_income = (%s) WHERE id = (%s)",
                (new_incomes_cents, member_id),
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print("ERROR", e)

    def _validate_income(self, income_cents: int):
        """Valida que el ingreso es positivo"""
        if income_cents < 0:
            raise ValueError("Ingreso no puede ser negativo")
