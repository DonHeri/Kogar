from enum import Enum

class MetodoReparto(Enum):
    PROPORTIONAL = "proporcional"
    EQUAL = "igual"
    CUSTOM = "custom"


class Fase(Enum):
    REGISTRO = "registro"
    PLANIFICACION = "planificación"
    MES = "transcurso_mes"
    CIERRE = "cierre"


