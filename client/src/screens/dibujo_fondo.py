"""Fondo de la arena según el escenario de la partida (US-09).

Cada escenario tiene su imagen en assets/sprites. Se ajusta al tamaño de la arena del servidor
(960 x 540) y se dibuja 1 a 1 desde la esquina de arriba a la izquierda. Si el escenario no trae
imagen (o no se conoce el escenario), no se dibuja nada y queda el fondo liso de siempre.
"""

import pygame

from src import sprites

TAMANO_ARENA = (960, 540)  # la arena del servidor (ANCHO_ARENA x ALTO_ARENA)

FONDOS = {
    "laboratorio": "lab",
    "estacion_espacial": "estacion",
    "planta_industrial": "fabrica",
    "centro_investigacion": "centroinvestigacion",
    "complejo_militar": "militar",
}


def dibujar_fondo(pantalla: pygame.Surface, escenario: str | None) -> bool:
    """Dibuja el fondo del escenario. Devuelve False si no hay imagen para dibujar."""
    nombre = FONDOS.get(escenario or "")
    if nombre is None:
        return False
    fondo = sprites.cargar_fondo(nombre, TAMANO_ARENA)
    if fondo is None:
        return False
    pantalla.blit(fondo, (0, 0))
    return True