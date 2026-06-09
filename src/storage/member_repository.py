import psycopg2
import psycopg2.extras

from src.models.member import Member
from src.utils.text import normalize_name


class MemberRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.cursor = self.db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def save(self, member: Member, household_id: int, status: bool = True):
        full_name = member.name
        monthly_income = member.monthly_income

        self.cursor.execute(
            "INSERT INTO members (full_name,monthly_income,status,household_id) VALUES (%s,%s,%s,%s) RETURNING id",
            (full_name, monthly_income, status, household_id),
        )
        member_id = self.cursor.fetchone()["id"]
        return member_id

    def del_member(self, member_id: int):

        self.cursor.execute("DELETE FROM members WHERE id = (%s)", (member_id,))

    def list_members(self, household_id: int):

        self.cursor.execute(
            "SELECT * FROM members WHERE household_id = (%s)", (household_id,)
        )
        return self.cursor.fetchall()

    def get_member_by_id(self, member_id: int) -> dict:
        self.cursor.execute(""" SELECT * FROM members WHERE id=(%s)""", (member_id,))
        return self.cursor.fetchone()

    def rename(self, new_name: str, member_id: int):

        normalized = normalize_name(new_name)
        if not normalized:
            raise ValueError("El nombre del miembro no puede estar vacío")

        self.cursor.execute(
            "UPDATE members SET full_name = (%s) WHERE id = (%s)",
            (normalized, member_id),
        )

    def change_incomes(self, new_incomes_cents: int, member_id: int):
        self._validate_income(new_incomes_cents)

        self.cursor.execute(
            "UPDATE members SET monthly_income = (%s) WHERE id = (%s)",
            (new_incomes_cents, member_id),
        )

    def _validate_income(self, income_cents: int):
        """Valida que el ingreso es positivo"""
        if income_cents < 0:
            raise ValueError("Ingreso no puede ser negativo")
