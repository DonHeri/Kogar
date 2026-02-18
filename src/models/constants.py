from enum import Enum

class MetodoReparto(Enum):
    PROPORCIONAL = "proporcional"
    IGUAL = "igual"
    CUSTOM = "custom"


class Fase(Enum):
    REGISTRO = "registro"
    CALCULOS = "calculos"
    MES = "transcurso_mes"
    CIERRE = "cierre"


