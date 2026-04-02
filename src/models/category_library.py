from dataclasses import dataclass, field
from src.models.constants import CategoryBehavior

_S = CategoryBehavior.SHARED
_P = CategoryBehavior.PERSONAL


@dataclass
class CategoryInfo:
    description: str
    behavior: CategoryBehavior = field(default=CategoryBehavior.SHARED)


class CategoryLibrary:
    """Biblioteca de categorías estándar y extendidas.
    Las categorías custom son por instancia — cada Budget tiene su propia librería."""

    STANDARD_CATEGORIES: dict[str, CategoryInfo] = {
        "fijos":     CategoryInfo("Gastos fijos mensuales recurrentes", _S),
        "variables": CategoryInfo("Gastos variables del día a día",     _P),
        "reserva":   CategoryInfo("Reserva personal: deuda y ahorro",   _P),
    }

    EXTENDED_CATEGORIES: dict[str, CategoryInfo] = {
        "deuda":      CategoryInfo("Préstamos e intereses personales",         _P),
        "salud":      CategoryInfo("Gastos médicos y farmacia",                _P),
        "transporte": CategoryInfo("Coche, gasolina, transporte público",      _P),
        "ocio":       CategoryInfo("Entretenimiento y hobbies",                _P),
        "educacion":  CategoryInfo("Formación, cursos, libros",                _P),
        "mascotas":   CategoryInfo("Cuidado y gastos de mascotas",             _P),
        "regalos":    CategoryInfo("Regalos y celebraciones",                  _P),
        "viajes":     CategoryInfo("Vacaciones y escapadas",                   _P),
        "tecnologia": CategoryInfo("Dispositivos, software, suscripciones",    _P),
    }

    def __init__(self):
        self._custom_categories: dict[str, CategoryInfo] = {}

    # ====== MUTATIONS ======
    def add_category(
        self, name: str, behavior: CategoryBehavior = CategoryBehavior.SHARED
    ) -> None:
        """Registra una categoría custom en esta instancia"""
        normalized = self.normalize(name)
        self._custom_categories[normalized] = CategoryInfo("", behavior)

    # ====== QUERIES ======
    def get_default_behavior(self, name: str) -> CategoryBehavior:
        """Retorna el behavior por defecto de una categoría. Fallback: SHARED."""
        normalized = self.normalize(name)
        all_cats = {
            **self.STANDARD_CATEGORIES,
            **self.EXTENDED_CATEGORIES,
            **self._custom_categories,
        }
        if normalized in all_cats:
            return all_cats[normalized].behavior
        return CategoryBehavior.SHARED

    @classmethod
    def get_standards_categories(cls) -> dict[str, str]:
        """Retorna {nombre: descripción} de las categorías estándar"""
        return {
            name: info.description
            for name, info in cls.STANDARD_CATEGORIES.items()
        }

    def get_all_suggestions(self) -> dict[str, str]:
        """Retorna {nombre: descripción} de todas las categorías"""
        all_cats = {
            **self.STANDARD_CATEGORIES,
            **self.EXTENDED_CATEGORIES,
            **self._custom_categories,
        }
        return {name: info.description for name, info in all_cats.items()}

    @classmethod
    def is_standard(cls, name: str) -> bool:
        """Verifica si una categoría es estándar"""
        return name in cls.STANDARD_CATEGORIES

    @classmethod
    def is_suggested(cls, name: str) -> bool:
        """Verifica si una categoría está en la librería extendida"""
        return name in cls.EXTENDED_CATEGORIES

    def is_known(self, name: str) -> bool:
        """Verifica si una categoría es conocida (estándar, extendida o custom)"""
        normalized = self.normalize(name)
        return (
            normalized in self.STANDARD_CATEGORIES
            or normalized in self.EXTENDED_CATEGORIES
            or normalized in self._custom_categories
        )

    # ====== NORMALIZATION ======
    @staticmethod
    def normalize(text: str) -> str:
        """
        Normaliza entrada de usuario a formato estándar

        Convierte a minúsculas: "  FIJOS  " → "fijos"
        """
        if not isinstance(text, str):
            raise ValueError("La categoría debe ser texto")

        normalized = text.strip().lower()

        if not normalized:
            raise ValueError("La categoría no puede estar vacía")

        return normalized


