"""Escenarios de la partida (US-09, patrón Factory).

Un escenario es solo datos: qué obstáculos, celdas y guardianes tiene el mapa. Las reglas del
juego son las mismas en todos, solo cambia la distribución.

Para que ningún jugador parta con ventaja, cada mapa se dibuja en el cuadrante de arriba a la
izquierda y se refleja en los otros tres. Los guardianes se ponen a mano porque no siempre son
simétricos.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.realtime.arena import (
    ALTO_ARENA,
    ANCHO_ARENA,
    Arena,
    Celda,
    Obstaculo,
    Reactor,
)
from app.realtime.guardianes import Guardian, Patrulla, Perseguir, RutaFija
from app.realtime.obstaculos import BARRERA, BARRERA_MOVIL, PUERTA, TRAMPA

VALOR_CELDA = 5  # CU-10 del ERS: una celda da 10 puntos


@dataclass(frozen=True)
class Escenario:
    nombre: str
    # (x, y, ancho, alto, tipo) del cuadrante de arriba a la izquierda
    obstaculos: tuple[tuple[int, int, int, int, str], ...]
    # (x, y, valor) del cuadrante de arriba a la izquierda
    celdas: tuple[tuple[int, int, int], ...]
    # Cada llamada devuelve guardianes nuevos: tienen estado y no se comparten entre partidas
    guardianes: Callable[[], list[Guardian]]
    # (x, y, ancho, alto, destino_x, destino_y) del cuadrante de arriba a la izquierda: barreras
    # que van y vienen en línea recta entre (x, y) y (destino_x, destino_y)
    moviles: tuple[tuple[int, int, int, int, int, int], ...] = ()


def _reflejar_obstaculo(x: int, y: int, ancho: int, alto: int, tipo: str) -> list[Obstaculo]:
    """El mismo rectángulo en los cuatro cuadrantes de la arena."""
    espejo_x = ANCHO_ARENA - x - ancho
    espejo_y = ALTO_ARENA - y - alto
    return [
        Obstaculo(x, y, ancho, alto, tipo),
        Obstaculo(espejo_x, y, ancho, alto, tipo),
        Obstaculo(x, espejo_y, ancho, alto, tipo),
        Obstaculo(espejo_x, espejo_y, ancho, alto, tipo),
    ]


def _reflejar_movil(
    x: int, y: int, ancho: int, alto: int, destino_x: int, destino_y: int
) -> list[Obstaculo]:
    """La misma barrera móvil en los cuatro cuadrantes, con el recorrido también reflejado."""
    resultado = []
    for reflejar_x in (False, True):
        for reflejar_y in (False, True):
            ox = ANCHO_ARENA - x - ancho if reflejar_x else x
            oy = ALTO_ARENA - y - alto if reflejar_y else y
            dx = ANCHO_ARENA - destino_x - ancho if reflejar_x else destino_x
            dy = ALTO_ARENA - destino_y - alto if reflejar_y else destino_y
            resultado.append(Obstaculo(ox, oy, ancho, alto, BARRERA_MOVIL, dx, dy))
    return resultado


def _reflejar_celda(x: int, y: int) -> list[tuple[int, int]]:
    return [
        (x, y),
        (ANCHO_ARENA - x, y),
        (x, ALTO_ARENA - y),
        (ANCHO_ARENA - x, ALTO_ARENA - y),
    ]


# Laboratorio: el mapa más abierto, para aprender. Pocas barreras y una trampa por esquina.
def _guardianes_laboratorio() -> list[Guardian]:
    return [Guardian(1, 480, 40, Patrulla([(480, 40), (480, 160)]))]


# Estación espacial: pasillos cerrados por puertas que se abren y se cierran.
def _guardianes_estacion() -> list[Guardian]:
    circuito = [(400, 110), (560, 110), (560, 430), (400, 430)]
    return [Guardian(1, 400, 110, RutaFija(circuito))]


# Planta industrial: muchas trampas que frenan. Dos guardianes vigilan los lados.
def _guardianes_planta() -> list[Guardian]:
    return [
        Guardian(1, 90, 270, Patrulla([(90, 270), (390, 270)])),
        Guardian(2, 870, 270, Patrulla([(870, 270), (570, 270)])),
    ]


# Centro de investigación: casi sin paredes, pero dos guardianes persiguen al que se acerca.
def _guardianes_centro() -> list[Guardian]:
    return [
        Guardian(1, 480, 60, Perseguir()),
        Guardian(2, 480, 480, Perseguir()),
    ]


# Complejo militar: de todo un poco.
def _guardianes_complejo() -> list[Guardian]:
    return [
        Guardian(1, 90, 270, Patrulla([(90, 270), (330, 270)])),
        Guardian(2, 870, 270, Patrulla([(870, 270), (630, 270)])),
        Guardian(3, 480, 60, Perseguir()),
    ]


ESCENARIOS: dict[str, Escenario] = {
    "laboratorio": Escenario(
        nombre="laboratorio",
        obstaculos=(
            (60, 60, 90, 30, BARRERA),
            (330, 90, 30, 90, BARRERA),
            (90, 180, 60, 60, TRAMPA),
        ),
        celdas=((240, 45, VALOR_CELDA), (420, 110, VALOR_CELDA)),
        guardianes=_guardianes_laboratorio,
        moviles=((180, 180, 30, 60, 270, 180),),
    ),
    "estacion_espacial": Escenario(
        nombre="estacion_espacial",
        obstaculos=(
            (120, 30, 30, 150, BARRERA),
            (330, 30, 30, 120, BARRERA),
            (120, 180, 30, 60, PUERTA),
            (330, 150, 30, 60, PUERTA),
        ),
        celdas=((240, 45, VALOR_CELDA), (420, 110, VALOR_CELDA)),
        guardianes=_guardianes_estacion,
    ),
    "planta_industrial": Escenario(
        nombre="planta_industrial",
        obstaculos=(
            (60, 60, 90, 60, TRAMPA),
            (330, 180, 60, 60, TRAMPA),
            (180, 210, 90, 30, BARRERA),
        ),
        celdas=((240, 45, VALOR_CELDA), (420, 110, VALOR_CELDA)),
        guardianes=_guardianes_planta,
    ),
    "centro_investigacion": Escenario(
        nombre="centro_investigacion",
        obstaculos=(
            (90, 90, 60, 90, BARRERA),
            (330, 60, 60, 60, TRAMPA),
        ),
        celdas=((240, 30, VALOR_CELDA), (420, 180, VALOR_CELDA)),
        guardianes=_guardianes_centro,
        moviles=((150, 210, 90, 30, 240, 210),),
    ),
    "complejo_militar": Escenario(
        nombre="complejo_militar",
        obstaculos=(
            (60, 30, 90, 30, BARRERA),
            (330, 30, 30, 90, BARRERA),
            (150, 210, 90, 30, PUERTA),
            (300, 210, 60, 60, TRAMPA),
        ),
        celdas=((240, 45, VALOR_CELDA), (420, 110, VALOR_CELDA)),
        guardianes=_guardianes_complejo,
    ),
}

NOMBRES_ESCENARIOS = tuple(ESCENARIOS)


class EscenarioDesconocidoError(ValueError):
    """Se pidió un escenario que no existe."""


def crear_escenario(nombre: str) -> tuple[Arena, list[Guardian]]:
    """Construye la arena y los guardianes del escenario. Cada llamada devuelve objetos nuevos,
    así dos partidas del mismo escenario no comparten estado."""
    escenario = ESCENARIOS.get(nombre)
    if escenario is None:
        raise EscenarioDesconocidoError(f"Escenario no válido: {nombre}")
    obstaculos = [o for datos in escenario.obstaculos for o in _reflejar_obstaculo(*datos)]
    obstaculos += [o for datos in escenario.moviles for o in _reflejar_movil(*datos)]
    celdas = []
    for x, y, valor in escenario.celdas:
        for cx, cy in _reflejar_celda(x, y):
            celdas.append(Celda(id=len(celdas) + 1, x=cx, y=cy, valor=valor))
    arena = Arena(
        reactor=Reactor(x=ANCHO_ARENA / 2, y=ALTO_ARENA / 2, radio=40),
        obstaculos=obstaculos,
        celdas=celdas,
    )
    return arena, escenario.guardianes()