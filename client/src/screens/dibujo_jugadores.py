"""Dibujo de los jugadores en la arena: sprite por número de jugador, aro de color y etiqueta.

El servidor manda a cada jugador con su `numero` (1 a 4, el orden de llegada) y su `estado`
(US-15). Cada número tiene su personaje y su color de aro, así se distinguen los cuatro. Si un
guardián lo aturde, el personaje se ve gris; si está escudado, el aro es azul y más grueso. El
jugador propio lleva la etiqueta "Vos". Si falta la imagen, se dibuja el círculo de antes.
"""

import pygame

from src import sprites
from src.screens.dibujo_guardianes import AZUL_ESCUDO, GRIS_ATURDIDO, ROJO

VERDE = (40, 170, 70)
NARANJA = (245, 140, 20)
MAGENTA = (200, 60, 180)
COLORES_NUMERO = {1: ROJO, 2: VERDE, 3: NARANJA, 4: MAGENTA}
GROSOR_ARO = 3
GROSOR_ESCUDO = 5
MARGEN_SPRITE = 4  # el personaje queda dentro del aro
NEGRO = (20, 20, 20)


def color_aro(numero: int | None, estado: str | None) -> tuple[int, int, int]:
    """Gris si está aturdido, azul si está escudado y, si no, el color de su número."""
    if estado == "aturdido":
        return GRIS_ATURDIDO
    if estado == "escudado":
        return AZUL_ESCUDO
    return COLORES_NUMERO.get(numero or 1, ROJO)


def sprite_jugador(numero: int | None, radio: int, aturdido: bool = False) -> pygame.Surface | None:
    lado = max(2 * (radio - MARGEN_SPRITE), 1)
    personaje = numero if numero in COLORES_NUMERO else 1
    imagen = sprites.cargar(f"jugador_{personaje}", (lado, lado))
    if imagen is not None and aturdido:
        imagen = pygame.transform.grayscale(imagen)
    return imagen


def dibujar_jugador(
    pantalla: pygame.Surface,
    x: float,
    y: float,
    radio: int,
    numero: int | None = None,
    estado: str | None = None,
    propio: bool = False,
    fuente: pygame.font.Font | None = None,
) -> None:
    centro = (int(x), int(y))
    color = color_aro(numero, estado)
    imagen = sprite_jugador(numero, radio, aturdido=estado == "aturdido")
    if imagen is None:
        pygame.draw.circle(pantalla, color, centro, radio)  # como antes de los sprites
    else:
        fondo = pygame.Surface((2 * radio, 2 * radio), pygame.SRCALPHA)
        pygame.draw.circle(fondo, (*color, 60), (radio, radio), radio)  # sombra suave del color
        pantalla.blit(fondo, (centro[0] - radio, centro[1] - radio))
        pantalla.blit(imagen, imagen.get_rect(center=centro))
        grosor = GROSOR_ESCUDO if estado == "escudado" else GROSOR_ARO
        pygame.draw.circle(pantalla, color, centro, radio, width=grosor)
    if fuente is not None:
        _etiqueta(pantalla, fuente, "Vos" if propio else f"J{numero or 1}", centro, radio, color)


def _etiqueta(pantalla, fuente, texto, centro, radio, color) -> None:
    imagen = fuente.render(texto, True, color if color != GRIS_ATURDIDO else NEGRO)
    pantalla.blit(imagen, imagen.get_rect(midbottom=(centro[0], centro[1] - radio - 1)))
