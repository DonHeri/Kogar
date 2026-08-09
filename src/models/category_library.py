from dataclasses import dataclass

from src.models.category import AutoCalculatedCategory, Category


@dataclass
class CategoryInfo:
    description: str
    auto_calculated: bool = False


class CategoryLibrary:
    """Biblioteca de categorías estándar y extendidas.
    Las categorías custom son por instancia — cada Budget tiene su propia librería."""

    STANDARD_CATEGORIES: dict[str, CategoryInfo] = {
        "fijos": CategoryInfo("Gastos fijos mensuales recurrentes"),
        "variables": CategoryInfo("Gastos variables del día a día"),
        "reserva": CategoryInfo(
            "Reserva personal: deuda y ahorro", auto_calculated=True
        ),
    }

    EXTENDED_CATEGORIES: dict[str, CategoryInfo] = {
        "deuda": CategoryInfo("Préstamos e intereses personales"),
        "salud": CategoryInfo("Gastos médicos y farmacia"),
        "transporte": CategoryInfo("Coche, gasolina, transporte público"),
        "ocio": CategoryInfo("Entretenimiento y hobbies"),
        "educacion": CategoryInfo("Formación, cursos, libros"),
        "mascotas": CategoryInfo("Cuidado y gastos de mascotas"),
        "regalos": CategoryInfo("Regalos y celebraciones"),
        "viajes": CategoryInfo("Vacaciones y escapadas"),
        "tecnologia": CategoryInfo("Dispositivos, software, suscripciones"),
    }

    def __init__(self):
        self._custom_categories: dict[str, CategoryInfo] = {}

    # ====== CLASS METHODS ======

    @classmethod
    def get_standards_categories(cls) -> dict[str, str]:
        """Retorna {nombre: descripción} de las categorías estándar"""
        return {
            name: info.description for name, info in cls.STANDARD_CATEGORIES.items()
        }

    @classmethod
    def is_standard(cls, name: str) -> bool:
        """Verifica si una categoría es estándar"""
        return name in cls.STANDARD_CATEGORIES

    @classmethod
    def is_suggested(cls, name: str) -> bool:
        """Verifica si una categoría está en la librería extendida"""
        return name in cls.EXTENDED_CATEGORIES

    # ====== STATIC METHODS ======

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

    # ====== API PÚBLICA ======

    def create_category(self, name: str) -> Category:
        """Fabrica el objeto Category a partir de su nombre.
        reserva → AutoCalculatedCategory. El resto → Category."""
        normalized = self.normalize(name)
        info = self._get_info(normalized)

        if info.auto_calculated:
            return AutoCalculatedCategory(normalized)
        return Category(normalized)

    def add_category(self, name: str) -> None:
        """Registra una categoría custom en esta instancia"""
        normalized = self.normalize(name)
        self._custom_categories[normalized] = CategoryInfo("")

    def get_all_suggestions(self) -> dict[str, str]:
        """Retorna {nombre: descripción} de todas las categorías"""
        all_cats = {
            **self.STANDARD_CATEGORIES,
            **self.EXTENDED_CATEGORIES,
            **self._custom_categories,
        }
        return {name: info.description for name, info in all_cats.items()}

    def is_known(self, name: str) -> bool:
        """Verifica si una categoría es conocida (estándar, extendida o custom)"""
        normalized = self.normalize(name)
        return (
            normalized in self.STANDARD_CATEGORIES
            or normalized in self.EXTENDED_CATEGORIES
            or normalized in self._custom_categories
        )

    # ====== PRIVADOS ======

    def _get_info(self, normalized: str) -> CategoryInfo:
        """Retorna el CategoryInfo de una categoría. Fallback: compartida."""
        all_cats = {
            **self.STANDARD_CATEGORIES,
            **self.EXTENDED_CATEGORIES,
            **self._custom_categories,
        }
        return all_cats.get(normalized, CategoryInfo(""))
