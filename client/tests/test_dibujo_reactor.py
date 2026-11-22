"""Pruebas del dibujo del reactor central."""

import os

import pygame
import pytest

from src.screens.dibujo_reactor import (
    BORDE,
    CARCASA,
    NUCLEO,
    NUCLEO_APAGADO,
    PERIODO_LATIDO_S,
    dibujar_reactor,
)

BLANCO = (255, 255, 255)
REACTOR = {"x": 150, "y": 100, "radio": 40}


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    yield
    pygame.quit()


def pantalla_con(energia=None, capacidad=None, tiempo=0.0, reactor=REACTOR):
    superficie = pygame.Surface((300, 200))
    superficie.fill(BLANCO)
    dibujar_reactor(superficie, reactor, energia, capacidad, tiempo)
    return superficie


def color(superficie, x, y):
    return tuple(superficie.get_at((x, y)))[:3]


def test_el_reactor_se_ve_en_el_centro_que_dice_el_servidor():
    assert color(pantalla_con(100, 100), 150, 100) == NUCLEO


def test_la_carcasa_ocupa_el_radio_del_reactor_y_nada_mas():
    pantalla = pantalla_con(100, 100)
    assert color(pantalla, 150 + 33, 100) == CARCASA  # entre el núcleo y el borde
    assert color(pantalla, 150 + 39, 100) == BORDE
    assert color(pantalla, 150 + 43, 100) == BLANCO


def test_sin_dato_de_energia_se_dibuja_lleno():
    assert color(pantalla_con(), 150, 100) == NUCLEO


def test_el_nucleo_se_apaga_cuando_se_vacia_la_energia():
    assert color(pantalla_con(0, 100), 150, 100) == NUCLEO_APAGADO


def test_el_nucleo_se_encoge_al_perder_energia():
    lleno = pantalla_con(100, 100)
    medio = pantalla_con(50, 100)
    # a 25 px del centro el núcleo lleno todavía llega y el de media energía ya no
    assert color(lleno, 150 + 25, 100) == NUCLEO
    assert color(medio, 150 + 25, 100) == CARCASA


def test_el_nucleo_late_con_el_tiempo():
    quieto = pantalla_con(100, 100, tiempo=0.0)
    grande = pantalla_con(100, 100, tiempo=PERIODO_LATIDO_S / 4)  # el punto más alto
    pequeno = pantalla_con(100, 100, tiempo=3 * PERIODO_LATIDO_S / 4)  # el más bajo
    # el borde del núcleo (30 px) queda dentro con el latido grande y fuera con el pequeño
    assert color(grande, 150 + 31, 100) == NUCLEO
    assert color(pequeno, 150 + 31, 100) == CARCASA
    assert color(quieto, 150, 100) == NUCLEO


def test_una_energia_fuera_de_rango_no_rompe_el_dibujo():
    assert color(pantalla_con(500, 100), 150, 100) == NUCLEO
    assert color(pantalla_con(-5, 100), 150, 100) == NUCLEO_APAGADO
    assert color(pantalla_con(10, 0), 150, 100) == NUCLEO  # capacidad 0: se dibuja lleno