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
    # REGISTRATION quedó en desuso al absorberla PLANNING. Se mantiene por el CHECK
    # de household_periods y por las filas antiguas; está fuera del ciclo vivo.
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

    @classmethod
    def cycle(cls) -> tuple["Phase", ...]:
        """Fases del ciclo de un período, en orden."""
        return (cls.PLANNING, cls.MONTH, cls.CLOSING)

    @property
    def order(self) -> int:
        """Posición en el ciclo. REGISTRATION devuelve -1: está fuera.

        Permite preguntar si una fase ya pasó sin llevar la cuenta en memoria, que
        es lo único posible cuando el estado vive en BD y no en un objeto.
        """
        cycle = Phase.cycle()
        return cycle.index(self) if self in cycle else -1

    def is_at_least(self, other: "Phase") -> bool:
        """True si esta fase es la pedida o una posterior del ciclo."""
        return self.order >= other.order

    def _require(self, ok: bool, expected: str) -> None:
        if not ok:
            raise ValueError(
                f"Operación solo permitida en fase {expected}. Fase actual: {self.value}"
            )

    def require(self, expected: "Phase") -> None:
        self._require(self == expected, expected.value)

    def require_at_least(self, minimum: "Phase") -> None:
        self._require(self.order >= minimum.order, f"{minimum.value} o posterior")

    def require_at_most(self, maximum: "Phase") -> None:
        self._require(self.order <= maximum.order, f"{maximum.value} o anterior")