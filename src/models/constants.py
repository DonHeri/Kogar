from enum import Enum


class MetodoReparto(Enum):
    PROPORTIONAL = "proporcional"
    EQUAL = "igual"
    CUSTOM = "custom"


class Phase(Enum):
    REGISTRATION = "registro"
    PLANNING = "planificación"
    MONTH = "transcurso_mes"
    CLOSING = "cierre"
