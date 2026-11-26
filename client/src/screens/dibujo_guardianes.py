"""Dibujo de los guardianes y color del jugador según su estado (US-15).

Cada guardián es el sprite del tanque teñido de morado (para que se note que es enemigo y no un
jugador) dentro de un aro morado oscuro. Si falta la imagen, se dibuja el círculo de antes.
"""

import pygame

from src import sprites

MORADO = (120, 40, 160)
MORADO_OSCURO = (60, 10, 90)
ROJO = (220, 30, 30)  # jugador normal
GRIS_ATURDIDO = (150, 150, 150)
AZUL_ESCUDO = (60, 130, 230)

COLORES_JUGADOR = {"aturdido": GRIS_ATURDIDO, "escudado": AZUL_ESCUDO}
TINTE_GUARDIAN = (255, 150, 255)  # multiplica el sprite en gris: queda morado
MARGEN_SPRITE = 2
GROSOR_BORDE = 3

_teñidos: dict[int, pygame.Surface | None] = {}


def color_jugador(estado: str | None) -> tuple[int, int, int]:
    """Rojo si está normal (o el servidor no manda estado); gris si está aturdido; azul si
    está escudado."""
    return COLORES_JUGADOR.get(estado or "", ROJO)


def sprite_guardian(radio: int) -> pygame.Surface | None:
    if radio not in _teñidos:
        lado = max(2 * (radio - MARGEN_SPRITE), 1)
        imagen = sprites.cargar("guardian", (lado, lado))
        if imagen is not None:
            imagen = pygame.transform.grayscale(imagen)  # primero gris, después morado
            imagen.fill((*TINTE_GUARDIAN, 255), special_flags=pygame.BLEND_RGBA_MULT)
        _teñidos[radio] = imagen
    return _teñidos[radio]


def dibujar_guardianes(pantalla: pygame.Surface, guardianes: list[dict]) -> None:
    for guardian in guardianes:
        centro = (int(guardian["x"]), int(guardian["y"]))
        radio = int(guardian["radio"])
        imagen = sprite_guardian(radio)
        if imagen is None:
            pygame.draw.circle(pantalla, MORADO, centro, radio)
        else:
            fondo = pygame.Surface((2 * radio, 2 * radio), pygame.SRCALPHA)
            pygame.draw.circle(fondo, (*MORADO, 70), (radio, radio), radio)
            pantalla.blit(fondo, (centro[0] - radio, centro[1] - radio))
            pantalla.blit(imagen, imagen.get_rect(center=centro))
        pygame.draw.circle(pantalla, MORADO_OSCURO, centro, radio, width=GROSOR_BORDE)
