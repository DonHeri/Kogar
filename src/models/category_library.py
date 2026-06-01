from dataclasses import dataclass

from src.models.category import AutoCalculatedCategory, Category


@dataclass
class CategoryInfo:
    description: str
    is_shared: bool = True
    auto_calculated: bool = False


class CategoryLibrary:
    """Biblioteca de categorías estándar y extendidas.
    Las categorías custom son por instancia — cada Budget tiene su propia librería."""

    STANDARD_CATEGORIES: dict[str, CategoryInfo] = {
        "fijos":     CategoryInfo("Gastos fijos mensuales recurrentes", is_shared=True),
        "variables": CategoryInfo("Gastos variables del día a día",     is_shared=False),
        "reserva":   CategoryInfo("Reserva personal: deuda y ahorro",   is_shared=False, auto_calculated=True),
    }

    EXTENDED_CATEGORIES: dict[str, CategoryInfo] = {
        "deuda":      CategoryInfo("Préstamos e intereses personales",      is_shared=False),
        "salud":      CategoryInfo("Gastos médicos y farmacia",             is_shared=False),
        "transporte": CategoryInfo("Coche, gasolina, transporte público",   is_shared=False),
        "ocio":       CategoryInfo("Entretenimiento y hobbies",             is_shared=False),
        "educacion":  CategoryInfo("Formación, cursos, libros",             is_shared=False),
        "mascotas":   CategoryInfo("Cuidado y gastos de mascotas",          is_shared=False),
        "regalos":    CategoryInfo("Regalos y celebraciones",               is_shared=False),
        "viajes":     CategoryInfo("Vacaciones y escapadas",                is_shared=False),
        "tecnologia": CategoryInfo("Dispositivos, software, suscripciones", is_shared=False),
    }

    def __init__(self):
        self._custom_categories: dict[str, CategoryInfo] = {}

    # ====== FACTORY ======
    def create_category(self, name: str) -> Category:
        """Fabrica el objeto Category a partir de su nombre.
        reserva → AutoCalculatedCategory. El resto → Category con su is_shared por defecto."""
        normalized = self.normalize(name)
        info = self._get_info(normalized)
        if info.auto_calculated:
            return AutoCalculatedCategory(normalized, is_shared=info.is_shared)
        return Category(normalized, is_shared=info.is_shared)

    # ====== MUTATIONS ======
    def add_category(self, name: str, is_shared: bool = True) -> None:
        """Registra una categoría custom en esta instancia"""
        normalized = self.normalize(name)
        self._custom_categories[normalized] = CategoryInfo("", is_shared=is_shared)

    # ====== QUERIES ======
    def _get_info(self, normalized: str) -> CategoryInfo:
        """Retorna el CategoryInfo de una categoría. Fallback: compartida."""
        all_cats = {
            **self.STANDARD_CATEGORIES,
            **self.EXTENDED_CATEGORIES,
            **self._custom_categories,
        }
        return all_cats.get(normalized, CategoryInfo(""))

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
