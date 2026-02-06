from typing import Protocol, List

# Aquí quiero definir Protocolos para empezar
# `to_dict`
# `from_dict`


# Protocolo to_dict
class Saver(Protocol):
    def to_dict(self) -> dict: ...


# Protocolo from_dict
class Loader(Protocol):
    def from_dict(self) -> dict: ...


""" 
Ahora, `participante`, `household` cuando incluyan esos métodos, solo necesitaré una interfaz que lo pase todo a dict, o lo extraiga.

# 3. La función que usa el protocolo (El Cliente)

def guardar_en_base_de_datos(items: List[Guardable]):
    for item in items:
        # Python sabe que 'item' tiene el método .to_dict() 
        # gracias al protocolo, aunque las clases sean distintas.
        datos = item.to_dict()
        print(f"Guardando en DB: {datos}")
"""
