"""Dibujo de los guardianes y color del jugador según su estado (US-15)."""

import pygame

MORADO = (120, 40, 160)
MORADO_OSCURO = (60, 10, 90)
ROJO = (220, 30, 30)  # jugador normal
GRIS_ATURDIDO = (150, 150, 150)
AZUL_ESCUDO = (60, 130, 230)

COLORES_JUGADOR = {"aturdido": GRIS_ATURDIDO, "escudado": AZUL_ESCUDO}


def color_jugador(estado: str | None) -> tuple[int, int, int]:
    """Rojo si está normal (o el servidor no manda estado); gris si está aturdido; azul si
    está escudado."""
    return COLORES_JUGADOR.get(estado or "", ROJO)


def dibujar_guardianes(pantalla: pygame.Surface, guardianes: list[dict]) -> None:
    for guardian in guardianes:
        centro = (int(guardian["x"]), int(guardian["y"]))
        pygame.draw.circle(pantalla, MORADO, centro, guardian["radio"])
        pygame.draw.circle(pantalla, MORADO_OSCURO, centro, guardian["radio"], width=3)
