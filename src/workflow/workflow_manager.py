from src.models.member import Member
from src.models.household import Household
from src.models.constants import Phase


class WorkflowManager:
    def __init__(self, household: Household) -> None:
        self.household = household
        self.current_phase = Phase.REGISTRATION

    # ====== FASE REGISTRO ======
    # En esta fase registramos a los usuarios
    def register_member(self, member: Member):
        """Registra miembros en fase inicial"""
        self.validate_phase(Phase.REGISTRATION)
        self.household.register_member(member)

    # Ingresamos salarios
    def set_incomes(self, name: str, amount: float):
        """Registra ingresos"""
        self.validate_phase(Phase.REGISTRATION)
        self.household.set_member_income(name, amount)

    # Si hay miembros e ingresos > 0; cambiamos de fase
    def finish_registration(self):
        """Validar y avanzar a planificación"""
        if not self.household.members:
            raise ValueError("Registra al menos un miembro")
        if self.household.get_total_incomes() <= 0:
            raise ValueError("Al menos un miembro debe tener ingresos")

        # Cambiar fase
        self.current_phase = Phase.PLANNING

    # ====== FASE PLANIFICACIÓN ======  
    """ 
    En fase de planificación 
    """

    # ====== FASE MES ======
    # ====== FASE CIERRE ======

    # ==================== QUERIES (Phase-independent) ====================
    def get_registered_members(self) -> list[str]:
        """Muestra miembros registrados"""
        return list(self.household.members.keys())

    def get_member_income(self, name: str):
        """Get a specific member incomes in cents (available in all phases)"""
        if name not in self.household.members:
            raise ValueError(f"{name} does not exist")

        return self.household.members[name].monthly_income

    def get_total_incomes(self) -> int:
        """Get total household income in cents (available in all phases)"""
        return self.household.get_total_incomes()

    # ====== HELPERS ======
    def validate_phase(self, required_phase: Phase):
        if self.current_phase != required_phase:
            raise ValueError(
                f"Operación solo permitida en fase {required_phase.value}. "
                f"Fase actual: {self.current_phase.value}"
            )
