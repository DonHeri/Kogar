from enum import Enum


class SavingScope(Enum):
    SHARED = "ahorro que contribuye al fondo conjunto del hogar"
    PERSONAL = "ahorro que solo pertenece al miembro, no se agrega al hogar"


class MetodoReparto(Enum):
    PROPORTIONAL = "proportional"
    EQUAL = "equal"
    CUSTOM = "custom"

    @classmethod
    def get_names(cls):
        return [phase.name for phase in cls]

    @classmethod
    def get_values(cls):
        return [phase.value for phase in cls]


class Phase(Enum):
    REGISTRATION = "registration"
    PLANNING = "planning"
    MONTH = "month"
    CLOSING = "closed"

    @classmethod
    def get_names(cls):
        return [phase.name for phase in cls]

    @classmethod
    def get_values(cls):
        return [phase.value for phase in cls]


class IncomeDestination(Enum):
    DISTRIBUTION = "distribution"
    CATEGORY = "category"
    SAVING = "saving"
    DEBT = "debt"

    @classmethod
    def get_names(cls):
        return [destination.name for destination in cls]

    @classmethod
    def get_values(cls):
        return [destination.value for destination in cls]
