class CategoryLibrary:
    """Biblioteca de categorías estándar y extendidas con validación normalizada"""

    STANDARD_CATEGORIES = {
        "fijos": "Gastos fijos mensuales recurrentes",
        "variables": "Gastos variables del día a día",
        "reserva": "Reserva personal: deuda y ahorro individual",
    }

    EXTENDED_CATEGORIES = {
        "deuda": "Préstamos e intereses personales",
        "salud": "Gastos médicos y farmacia",
        "transporte": "Coche, gasolina, transporte público",
        "ocio": "Entretenimiento y hobbies",
        "educacion": "Formación, cursos, libros",
        "mascotas": "Cuidado y gastos de mascotas",
        "regalos": "Regalos y celebraciones",
        "viajes": "Vacaciones y escapadas",
        "tecnologia": "Dispositivos, software, suscripciones digitales",
    }

    # ====== MUTATIONS ======
    @classmethod
    def add_category(cls, name: str) -> None:
        """Agrega una nueva categoría a la librería extendida"""
        normalized = cls.normalize(name)
        cls.EXTENDED_CATEGORIES[normalized] = ""

    # ====== QUERIES ======
    @classmethod
    def get_standards_categories(cls) -> dict[str, str]:
        """Retorna copia de las categorías estándar"""
        return cls.STANDARD_CATEGORIES.copy()

    @classmethod
    def get_all_suggestions(cls) -> dict[str, str]:
        """Retorna todas las categorías (estándar + extendida)"""
        return {**cls.STANDARD_CATEGORIES, **cls.EXTENDED_CATEGORIES}

    @classmethod
    def is_standard(cls, name: str) -> bool:
        """Verifica si una categoría es estándar"""
        return name in cls.STANDARD_CATEGORIES

    @classmethod
    def is_suggest(cls, name: str) -> bool:
        """Verifica si una categoría está en la librería extendida"""
        return name in cls.EXTENDED_CATEGORIES

    @classmethod
    def is_known(cls, name: str) -> bool:
        """Verifica si una categoría es conocida (estándar o extendida)"""
        normalized = cls.normalize(name)
        all_categories = {**cls.STANDARD_CATEGORIES, **cls.EXTENDED_CATEGORIES}
        return normalized in all_categories

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


