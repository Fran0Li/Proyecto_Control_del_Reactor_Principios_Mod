"""Pruebas del dibujo de los guardianes y del color del jugador por estado (US-15)."""

import os

import pygame
import pytest

from src.screens.dibujo_guardianes import (
    AZUL_ESCUDO,
    GRIS_ATURDIDO,
    MORADO,
    MORADO_OSCURO,
    ROJO,
    color_jugador,
    dibujar_guardianes,
)

BLANCO = (255, 255, 255)


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    yield
    pygame.quit()


def pantalla_con(guardianes):
    superficie = pygame.Surface((300, 200))
    superficie.fill(BLANCO)
    dibujar_guardianes(superficie, guardianes)
    return superficie


def color(superficie, x, y):
    return tuple(superficie.get_at((x, y)))[:3]


GUARDIAN = {"id": 1, "x": 150, "y": 100, "radio": 18}


def test_el_guardian_es_un_circulo_morado_con_borde_oscuro():
    pantalla = pantalla_con([GUARDIAN])
    assert color(pantalla, 150, 100) == MORADO
    assert color(pantalla, 150 + 17, 100) == MORADO_OSCURO


def test_no_dibuja_fuera_del_radio():
    pantalla = pantalla_con([GUARDIAN])
    assert color(pantalla, 150 + 25, 100) == BLANCO


def test_dibuja_varios_guardianes():
    otro = {"id": 2, "x": 50, "y": 50, "radio": 18}
    pantalla = pantalla_con([GUARDIAN, otro])
    assert color(pantalla, 150, 100) == MORADO
    assert color(pantalla, 50, 50) == MORADO


def test_sin_guardianes_no_falla():
    assert color(pantalla_con([]), 150, 100) == BLANCO


def test_el_jugador_normal_es_rojo():
    assert color_jugador("normal") == ROJO


def test_sin_estado_el_jugador_es_rojo():
    assert color_jugador(None) == ROJO


def test_estado_desconocido_es_rojo():
    assert color_jugador("otro") == ROJO


def test_el_jugador_aturdido_es_gris():
    assert color_jugador("aturdido") == GRIS_ATURDIDO


def test_el_jugador_escudado_es_azul():
    assert color_jugador("escudado") == AZUL_ESCUDO
