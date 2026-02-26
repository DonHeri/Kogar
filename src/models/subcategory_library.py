class CategoryLibrary:
    """Biblioteca de categorías principales"""

    STANDARD = {
        "fijos": "Gastos fijos mensuales recurrentes",
        "variables": "Gastos variables del día a día",
        "deuda": "Pagos de deudas y préstamos",
        "ahorro": "Ahorro mensual",
    }

    EXTENDED = {
        "salud": "Gastos médicos y farmacia",
        "transporte": "Coche, gasolina, transporte público",
        "ocio": "Entretenimiento y hobbies",
        "educacion": "Formación, cursos, libros",
        "mascotas": "Cuidado y gastos de mascotas",
        "regalos": "Regalos y celebraciones",
        "viajes": "Vacaciones y escapadas",
        "tecnologia": "Dispositivos, software, suscripciones digitales",
    }


class SubcategoryLibrary:
    """Biblioteca de subcategorías sugeridas por categoría"""

    SUGGESTIONS = {
        "fijos": [
            "alquiler",
            "hipoteca",
            "luz",
            "agua",
            "gas",
            "internet",
            "telefono",
            "seguros",
            "comunidad",
            "impuestos",
        ],
        "variables": [
            "supermercado",
            "restaurantes",
            "cafeterias",
            "ropa",
            "calzado",
            "peluqueria",
            "limpieza",
            "hogar",
            "otros",
        ],
        "deuda": [
            "prestamo_personal",
            "prestamo_coche",
            "tarjeta_credito",
            "prestamo_estudios",
            "otros_prestamos",
        ],
        "ahorro": [
            "emergencias",
            "vacaciones",
            "compra_grande",
            "jubilacion",
            "inversion",
            "fondo_libre",
        ],
        "salud": [
            "medico",
            "farmacia",
            "dentista",
            "optica",
            "fisioterapia",
            "psicologia",
            "seguro_salud",
        ],
        "transporte": [
            "gasolina",
            "parking",
            "peajes",
            "transporte_publico",
            "taxi_uber",
            "mantenimiento_coche",
            "seguro_coche",
            "impuestos_coche",
        ],
        "ocio": [
            "cine",
            "conciertos",
            "deportes",
            "gimnasio",
            "suscripciones_streaming",
            "videojuegos",
            "libros",
            "hobbies",
        ],
        "educacion": [
            "matricula",
            "libros",
            "material",
            "cursos_online",
            "idiomas",
            "academias",
        ],
        "mascotas": [
            "veterinario",
            "comida",
            "accesorios",
            "peluqueria_mascotas",
            "seguro_mascotas",
        ],
        "regalos": ["cumpleanos", "navidad", "aniversarios", "bodas", "otros_eventos"],
        "viajes": [
            "vuelos",
            "alojamiento",
            "actividades",
            "comida_viaje",
            "transporte_viaje",
            "souvenirs",
        ],
        "tecnologia": [
            "ordenador",
            "movil",
            "tablet",
            "software",
            "suscripciones_digitales",
            "reparaciones",
            "accesorios",
        ],
    }

    @classmethod
    def get_suggestions_for(cls, category: str) -> list[str]:
        """Devuelve subcategorías sugeridas para una categoría"""
        return cls.SUGGESTIONS.get(category, [])
