from enum import Enum


class CategoryBehavior(Enum):
    SHARED = "Los gastos en esta categoría, son por defecto compartidos. Entran en el settlement"
    PERSONAL = "Los gastos en esta categoría, son por defecto personales. No entran en el settlement"


class SavingScope(Enum):
    SHARED = "ahorro que contribuye al fondo conjunto del hogar"
    PERSONAL = "ahorro que solo pertenece al miembro, no se agrega al hogar"


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
