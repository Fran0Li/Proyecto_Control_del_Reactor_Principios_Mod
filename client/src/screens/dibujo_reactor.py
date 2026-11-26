"""Dibujo del reactor central, el mismo en todos los mapas.

Con la imagen del reactor (assets/sprites/extra) se dibuja el sprite con un halo que late y que se
apaga, junto con el sprite, al vaciarse la energía. Si falta la imagen se dibuja una carcasa con un
núcleo que late.
"""

import math

import pygame

from src import sprites

SPRITE = "extra/Base_Futurista"
LADO_SPRITE = 90  # el sprite es de 30 x 30: se amplía 3 veces, sin deformar los píxeles
HALO = (60, 220, 240)
ALPHA_HALO = 90  # transparencia del halo con la energía llena
BRILLO_MINIMO = 110  # el sprite nunca se oscurece del todo (255 = sin oscurecer)
CARCASA = (25, 70, 90)
BORDE = (10, 35, 50)
NUCLEO = (60, 220, 240)  # energía llena
NUCLEO_APAGADO = (60, 95, 110)  # casi sin energía
PERIODO_LATIDO_S = 1.2
AMPLITUD_LATIDO = 0.08  # el núcleo crece y se encoge hasta un 8 %
FRACCION_NUCLEO = 0.75  # tamaño del núcleo respecto a la carcasa, con la energía llena
FRACCION_MINIMA = 0.35  # el núcleo nunca desaparece del todo


def _mezclar(apagado: tuple[int, int, int], lleno: tuple[int, int, int], t: float) -> tuple:
    return tuple(round(a + (b - a) * t) for a, b in zip(apagado, lleno, strict=True))


def dibujar_reactor(
    pantalla: pygame.Surface,
    reactor: dict,
    energia: float | None = None,
    capacidad: float | None = None,
    tiempo: float = 0.0,
) -> None:
    """Dibuja el reactor donde dice el servidor. La carcasa mide justo lo que mide en el juego
    (ahí se extrae energía); el núcleo late con el `tiempo` y se apaga según la energía."""
    centro = (int(reactor["x"]), int(reactor["y"]))
    radio = int(reactor["radio"])
    if energia is None or not capacidad:
        carga = 1.0
    else:
        carga = min(max(energia / capacidad, 0.0), 1.0)
    latido = 1 + AMPLITUD_LATIDO * math.sin(2 * math.pi * tiempo / PERIODO_LATIDO_S)
    imagen = sprites.cargar(SPRITE, (LADO_SPRITE, LADO_SPRITE))
    if imagen is not None:
        _dibujar_sprite(pantalla, imagen, centro, radio, carga, latido)
        return
    radio_nucleo = radio * FRACCION_NUCLEO * (FRACCION_MINIMA + (1 - FRACCION_MINIMA) * carga)
    pygame.draw.circle(pantalla, CARCASA, centro, radio)
    pygame.draw.circle(pantalla, BORDE, centro, radio, width=3)
    color_nucleo = _mezclar(NUCLEO_APAGADO, NUCLEO, carga)
    pygame.draw.circle(pantalla, color_nucleo, centro, max(1, int(radio_nucleo * latido)))


def _dibujar_sprite(
    pantalla: pygame.Surface,
    imagen: pygame.Surface,
    centro: tuple[int, int],
    radio: int,
    carga: float,
    latido: float,
) -> None:
    """El halo late alrededor del reactor y se apaga con la energía; el sprite se oscurece."""
    radio_halo = int(radio * 1.3 * latido)
    halo = pygame.Surface((2 * radio_halo, 2 * radio_halo), pygame.SRCALPHA)
    pygame.draw.circle(
        halo, (*HALO, int(ALPHA_HALO * carga)), (radio_halo, radio_halo), radio_halo
    )
    pantalla.blit(halo, halo.get_rect(center=centro))
    brillo = int(BRILLO_MINIMO + (255 - BRILLO_MINIMO) * carga)
    if brillo < 255:
        imagen = imagen.copy()
        imagen.fill((brillo, brillo, brillo, 255), special_flags=pygame.BLEND_RGBA_MULT)
    pantalla.blit(imagen, imagen.get_rect(center=centro))