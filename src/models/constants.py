from enum import Enum


class SavingScope(Enum):
    SHARED = "shared"
    PERSONAL = "personal"


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
