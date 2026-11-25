"""Fondos del juego (US-09).

Fondo de la arena: cada escenario tiene su imagen en assets/sprites. Se ajusta al tamaño de la
arena del servidor (960 x 540) y se dibuja 1 a 1 desde la esquina de arriba a la izquierda. Si el
escenario no trae imagen (o no se conoce el escenario), no se dibuja nada y queda el fondo liso.

Fondo de las demás pantallas (login, registro, lobby, ceremonia...): una sola imagen que cubre
toda la ventana, con un velo oscuro encima para que el texto se lea. Si falta la imagen se pinta
el color liso de siempre.
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


FONDO_MENU = "fondo_menu"
VELO_MENU = (12, 16, 32, 90)  # el azul oscuro de siempre, algo transparente

_velos: dict[tuple[int, int], pygame.Surface] = {}


def dibujar_fondo_menu(
    pantalla: pygame.Surface, color_respaldo: tuple[int, int, int] = VELO_MENU[:3]
) -> bool:
    """Dibuja el fondo de las pantallas que no son de partida, del tamaño de la ventana.
    Si falta la imagen pinta `color_respaldo`. Devuelve True si dibujó la imagen."""
    tamano = pantalla.get_size()
    fondo = sprites.cargar_fondo(FONDO_MENU, tamano)
    if fondo is None:
        pantalla.fill(color_respaldo)
        return False
    pantalla.blit(fondo, (0, 0))
    velo = _velos.get(tamano)
    if velo is None:
        velo = pygame.Surface(tamano, pygame.SRCALPHA)
        velo.fill(VELO_MENU)
        _velos[tamano] = velo
    pantalla.blit(velo, (0, 0))
    return True