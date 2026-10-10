"""Intérprete de la capa 1 del contrato de hardware (líneas de texto del Arduino).

Formato (docs/contrato-api-hardware.md):
    HELLO <id> <version>
    BTN <UP|DOWN|LEFT|RIGHT|ACTION> <PRESS|RELEASE>
    HB
"""

from dataclasses import dataclass

BOTONES = {
    "UP": "arriba",
    "DOWN": "abajo",
    "LEFT": "izquierda",
    "RIGHT": "derecha",
    "ACTION": "accion",
}
ESTADOS = {"PRESS": "presionado", "RELEASE": "liberado"}


@dataclass(frozen=True)
class Saludo:
    id_dispositivo: str
    version: str


@dataclass(frozen=True)
class Boton:
    control: str  # valor del contrato: arriba, abajo, izquierda, derecha, accion
    estado: str  # presionado o liberado


@dataclass(frozen=True)
class Latido:
    pass


Mensaje = Saludo | Boton | Latido


def interpretar_linea(linea: str) -> Mensaje | None:
    """Convierte una línea en un mensaje. Devuelve None si no cumple el formato (CU-07, E1)."""
    partes = linea.strip().split()
    if partes == ["HB"]:
        return Latido()
    if len(partes) == 3 and partes[0] == "HELLO":
        return Saludo(id_dispositivo=partes[1], version=partes[2])
    if len(partes) == 3 and partes[0] == "BTN":
        control = BOTONES.get(partes[1])
        estado = ESTADOS.get(partes[2])
        if control is not None and estado is not None:
            return Boton(control=control, estado=estado)
    return None
