"""Dibujo de los obstáculos de la arena (US-14): barrera, trampa, puerta y barrera móvil."""

import pygame

GRIS = (70, 75, 85)  # barrera
NARANJA = (255, 170, 0)  # trampa
MARRON = (150, 60, 40)  # puerta cerrada
VERDE = (60, 170, 80)  # contorno de la puerta abierta
ACERO = (90, 110, 150)  # barrera móvil: se distingue de la barrera fija por el color y el borde
BORDE_ACERO = (30, 40, 70)


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
            pygame.draw.rect(pantalla, ACERO, rect)
            pygame.draw.rect(pantalla, BORDE_ACERO, rect, width=3)
        else:
            pygame.draw.rect(pantalla, GRIS, rect)
