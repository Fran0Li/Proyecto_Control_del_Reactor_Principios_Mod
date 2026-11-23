"""Dibujo del reactor central: una carcasa fija y un núcleo que late y se apaga al vaciarse."""

import math

import pygame

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
    radio_nucleo = radio * FRACCION_NUCLEO * (FRACCION_MINIMA + (1 - FRACCION_MINIMA) * carga)
    pygame.draw.circle(pantalla, CARCASA, centro, radio)
    pygame.draw.circle(pantalla, BORDE, centro, radio, width=3)
    color_nucleo = _mezclar(NUCLEO_APAGADO, NUCLEO, carga)
    pygame.draw.circle(pantalla, color_nucleo, centro, max(1, int(radio_nucleo * latido)))
