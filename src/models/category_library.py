class CategoryLibrary:
    """Biblioteca de categorías principales"""

    STANDARD_CATEGORIES = {
        "fijos": "Gastos fijos mensuales recurrentes",
        "variables": "Gastos variables del día a día",
        "deuda": "Pagos de deudas y préstamos",
        "ahorro": "Ahorro mensual",
    }

    EXTENDED_CATEGORIES = {
        "salud": "Gastos médicos y farmacia",
        "transporte": "Coche, gasolina, transporte público",
        "ocio": "Entretenimiento y hobbies",
        "educacion": "Formación, cursos, libros",
        "mascotas": "Cuidado y gastos de mascotas",
        "regalos": "Regalos y celebraciones",
        "viajes": "Vacaciones y escapadas",
        "tecnologia": "Dispositivos, software, suscripciones digitales",
    }

    @classmethod
    def get_standards_categories(cls) -> dict[str, str]:
        return cls.STANDARD_CATEGORIES.copy()

    @classmethod
    def get_all_suggestions(cls) -> dict[str, str]:
        return {**cls.STANDARD_CATEGORIES, **cls.EXTENDED_CATEGORIES}

    @classmethod
    def is_standard(cls, name: str) -> bool:
        return name in cls.STANDARD_CATEGORIES

    @classmethod
    def is_suggest(cls, name: str) -> bool:
        return name in cls.EXTENDED_CATEGORIES
