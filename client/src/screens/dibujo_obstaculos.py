"""Dibujo de los obstáculos de la arena (US-14): barrera, trampa, puerta y barrera móvil.

Las barreras (fijas y móviles) se rellenan con el sprite del muro en cuadros de 30 x 30, la
medida con la que están hechos los escenarios. Si falta la imagen, se dibuja el color de antes.
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


def dibujar_obstaculos(pantalla: pygame.Surface, obstaculos: list[dict]) -> None:
    for obstaculo in obstaculos:
        rect = pygame.Rect(obstaculo["x"], obstaculo["y"], obstaculo["ancho"], obstaculo["alto"])
        tipo = obstaculo.get("tipo", "barrera")
        if tipo == "trampa":
            pygame.draw.rect(pantalla, NARANJA, rect)
        elif tipo == "puerta":
            if obstaculo.get("abierta", False):
                pygame.draw.rect(pantalla, VERDE, rect, width=2)  # abierta: solo el contorno
            else:
                pygame.draw.rect(pantalla, MARRON, rect)
        elif tipo == "barrera_movil":
            if not _rellenar_con_muro(pantalla, rect):
                pygame.draw.rect(pantalla, ACERO, rect)
            pygame.draw.rect(pantalla, BORDE_ACERO, rect, width=3)  # se distingue de la fija
        elif not _rellenar_con_muro(pantalla, rect):
            pygame.draw.rect(pantalla, GRIS, rect)


def _rellenar_con_muro(pantalla: pygame.Surface, rect: pygame.Rect) -> bool:
    """Repite el sprite del muro dentro del rectángulo. False si no hay imagen."""
    muro = sprites.cargar("muro", (LADO_MURO, LADO_MURO))
    if muro is None:
        return False
    pygame.draw.rect(pantalla, GRIS, rect)  # fondo sólido: que se vea que no se puede pasar
    recorte_anterior = pantalla.get_clip()
    pantalla.set_clip(rect.clip(recorte_anterior) if recorte_anterior else rect)
    for x in range(rect.left, rect.right, LADO_MURO):
        for y in range(rect.top, rect.bottom, LADO_MURO):
            pantalla.blit(muro, (x, y))
    pantalla.set_clip(recorte_anterior)
    return True
