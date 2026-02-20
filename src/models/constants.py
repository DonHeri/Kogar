from enum import Enum


class MetodoReparto(Enum):
    PROPORTIONAL = "proporcional"
    EQUAL = "igual"
    CUSTOM = "custom"

    @classmethod
    def get_names(cls):
        return [phase.name for phase in cls]

    @classmethod
    def get_values(cls):
        return [phase.value for phase in cls]


class Phase(Enum):
    REGISTRATION = "registro"
    PLANNING = "planificación"
    MONTH = "transcurso_mes"
    CLOSING = "cierre"

    @classmethod
    def get_names(cls):
        return [phase.name for phase in cls]

    @classmethod
    def get_values(cls):
        return [phase.value for phase in cls]
