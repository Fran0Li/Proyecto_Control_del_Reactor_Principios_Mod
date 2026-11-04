"""Modelo de la arena: lo que hay en el mapa además de los jugadores (US-09, US-13, US-14).

Son datos simples, sin lógica de juego. Las mecánicas (obstáculos que frenan, celdas que se
recolectan, guardianes) usan este modelo, pero viven en archivos aparte.
"""

from dataclasses import dataclass, field

ANCHO_ARENA = 960
ALTO_ARENA = 540
RADIO_JUGADOR = 20
PUNTOS_DE_INICIO = ((240, 135), (720, 135), (240, 405), (720, 405))


@dataclass(frozen=True)
class Reactor:
    """El reactor del que los jugadores extraen energía."""

    x: float
    y: float
    radio: float

    def a_dict(self) -> dict:
        return {"x": round(self.x), "y": round(self.y), "radio": round(self.radio)}


@dataclass(frozen=True)
class Obstaculo:
    """Un rectángulo del mapa. `tipo` dice qué hace: barrera, trampa, puerta..."""

    x: float
    y: float
    ancho: float
    alto: float
    tipo: str = "barrera"

    def a_dict(self) -> dict:
        return {
            "x": round(self.x),
            "y": round(self.y),
            "ancho": round(self.ancho),
            "alto": round(self.alto),
            "tipo": self.tipo,
        }


@dataclass(frozen=True)
class Celda:
    """Una celda de energía que da `valor` puntos al recolectarla."""

    id: int
    x: float
    y: float
    valor: int

    def a_dict(self) -> dict:
        return {"id": self.id, "x": round(self.x), "y": round(self.y), "valor": self.valor}


@dataclass
class Arena:
    """Todo lo que hay en el mapa de una partida."""

    reactor: Reactor
    ancho: int = ANCHO_ARENA
    alto: int = ALTO_ARENA
    radio_jugador: int = RADIO_JUGADOR
    puntos_inicio: tuple[tuple[int, int], ...] = PUNTOS_DE_INICIO
    obstaculos: list[Obstaculo] = field(default_factory=list)
    celdas: list[Celda] = field(default_factory=list)

    def a_dict(self) -> dict:
        """La parte `arena` del mensaje de estado (ver el contrato). Los puntos de inicio
        no se mandan: el cliente ya recibe la posición de cada jugador."""
        return {
            "ancho": self.ancho,
            "alto": self.alto,
            "radio": self.radio_jugador,
            "reactor": self.reactor.a_dict(),
            "obstaculos": [o.a_dict() for o in self.obstaculos],
            "celdas": [c.a_dict() for c in self.celdas],
        }


def arena_basica() -> Arena:
    """Arena de partida: el reactor al centro y nada más. Los escenarios (US-09) la reemplazan."""
    return Arena(reactor=Reactor(x=ANCHO_ARENA / 2, y=ALTO_ARENA / 2, radio=40))