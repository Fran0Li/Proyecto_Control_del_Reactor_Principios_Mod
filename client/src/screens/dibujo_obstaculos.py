"""Dibujo de los obstáculos de la arena (US-14): barrera, trampa, puerta y barrera móvil.

Cada tipo se rellena con su sprite en cuadros de 30 x 30, la medida con la que están hechos los
escenarios: la barrera y la barrera móvil con `muro`, la trampa con `trampa` y la puerta con
`muro_intermitente` (oscurecido mientras está abierta). Si falta una imagen, se dibuja el color
o el contorno de antes.
"""

import pygame

from src import sprites

GRIS = (70, 75, 85)  # barrera
NARANJA = (255, 170, 0)  # trampa
MARRON = (150, 60, 40)  # puerta cerrada
VERDE = (60, 170, 80)  # contorno de la puerta abierta
ACERO = (90, 110, 150)  # barrera móvil: se distingue de la barrera fija por el color y el borde
BORDE_ACERO = (30, 40, 70)
LADO_MURO = 30  # los obstáculos de los escenarios miden múltiplos de 30
OSCURECER = (70, 70, 70, 255)  # la puerta abierta se ve así de oscura (255 es normal, 0 negro)

_oscuros: dict[str, tuple[pygame.Surface, pygame.Surface]] = {}


def dibujar_obstaculos(pantalla: pygame.Surface, obstaculos: list[dict]) -> None:
    for obstaculo in obstaculos:
        rect = pygame.Rect(obstaculo["x"], obstaculo["y"], obstaculo["ancho"], obstaculo["alto"])
        tipo = obstaculo.get("tipo", "barrera")
        if tipo == "trampa":
            if not _rellenar(pantalla, rect, _sprite("trampa"), fondo=None):
                pygame.draw.rect(pantalla, NARANJA, rect)
        elif tipo == "puerta":
            _dibujar_puerta(pantalla, rect, obstaculo.get("abierta", False))
        elif tipo == "barrera_movil":
            if not _rellenar(pantalla, rect, _sprite("muro")):
                pygame.draw.rect(pantalla, ACERO, rect)
            pygame.draw.rect(pantalla, BORDE_ACERO, rect, width=3)  # se distingue de la fija
        elif not _rellenar(pantalla, rect, _sprite("muro")):
            pygame.draw.rect(pantalla, GRIS, rect)


def _dibujar_puerta(pantalla: pygame.Surface, rect: pygame.Rect, abierta: bool) -> None:
    """Cerrada: el muro normal. Abierta: el mismo muro, pero oscuro."""
    muro = _sprite("muro_intermitente")
    if muro is not None:
        _rellenar(pantalla, rect, _oscurecido("muro_intermitente", muro) if abierta else muro)
    elif abierta:
        pygame.draw.rect(pantalla, VERDE, rect, width=2)  # abierta: solo el contorno
    else:
        pygame.draw.rect(pantalla, MARRON, rect)


def _sprite(nombre: str) -> pygame.Surface | None:
    return sprites.cargar(nombre, (LADO_MURO, LADO_MURO))


def _oscurecido(nombre: str, original: pygame.Surface) -> pygame.Surface:
    """El sprite con menos brillo, guardado para no recalcularlo en cada cuadro."""
    guardado = _oscuros.get(nombre)
    if guardado is None or guardado[0] is not original:
        oscuro = original.copy()
        oscuro.fill(OSCURECER, special_flags=pygame.BLEND_RGBA_MULT)
        guardado = (original, oscuro)
        _oscuros[nombre] = guardado
    return guardado[1]


def _rellenar(
    pantalla: pygame.Surface,
    rect: pygame.Rect,
    sprite: pygame.Surface | None,
    fondo: tuple[int, int, int] | None = GRIS,
) -> bool:
    """Repite el sprite dentro del rectángulo. False si no hay imagen.
    `fondo` es el color sólido de abajo: que se vea que no se puede pasar."""
    if sprite is None:
        return False
    if fondo is not None:
        pygame.draw.rect(pantalla, fondo, rect)
    recorte_anterior = pantalla.get_clip()
    pantalla.set_clip(rect.clip(recorte_anterior) if recorte_anterior else rect)
    for x in range(rect.left, rect.right, LADO_MURO):
        for y in range(rect.top, rect.bottom, LADO_MURO):
            pantalla.blit(sprite, (x, y))
    pantalla.set_clip(recorte_anterior)
    return True