"""Pruebas del dibujo de los obstáculos (US-14)."""

import os

import pygame
import pytest

from src import sprites
from src.screens import dibujo_obstaculos
from src.screens.dibujo_obstaculos import (
    ACERO,
    BORDE_ACERO,
    GRIS,
    MARRON,
    NARANJA,
    VERDE,
    dibujar_obstaculos,
)

BLANCO = (255, 255, 255)


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def sin_sprites(monkeypatch):
    """Sin la imagen del muro: las barreras se dibujan con su color de siempre."""
    monkeypatch.setattr(dibujo_obstaculos.sprites, "cargar", lambda *a, **k: None)


def pantalla_con(obstaculos):
    superficie = pygame.Surface((300, 200))
    superficie.fill(BLANCO)
    dibujar_obstaculos(superficie, obstaculos)
    return superficie


def color(superficie, x, y):
    return tuple(superficie.get_at((x, y)))[:3]


def obstaculo(tipo, **extra):
    return {"x": 100, "y": 50, "ancho": 60, "alto": 40, "tipo": tipo, **extra}


def test_la_barrera_es_gris(sin_sprites):
    assert color(pantalla_con([obstaculo("barrera")]), 130, 70) == GRIS


def test_la_trampa_es_naranja():
    assert color(pantalla_con([obstaculo("trampa")]), 130, 70) == NARANJA


def test_la_puerta_cerrada_es_marron_y_rellena():
    assert color(pantalla_con([obstaculo("puerta", abierta=False)]), 130, 70) == MARRON


def test_la_puerta_abierta_solo_dibuja_el_contorno():
    pantalla = pantalla_con([obstaculo("puerta", abierta=True)])
    assert color(pantalla, 100, 70) == VERDE  # el borde
    assert color(pantalla, 130, 70) == BLANCO  # el centro queda libre


def test_la_barrera_movil_es_de_otro_color_que_la_fija_y_tiene_borde(sin_sprites):
    pantalla = pantalla_con([obstaculo("barrera_movil")])
    assert color(pantalla, 130, 70) == ACERO
    assert color(pantalla, 100, 70) == BORDE_ACERO
    assert ACERO != GRIS


def test_la_barrera_movil_se_dibuja_donde_el_servidor_dice(sin_sprites):
    # el servidor manda la posición de ahora: al moverse, el dibujo la sigue
    antes = pantalla_con([obstaculo("barrera_movil")])
    despues = pantalla_con([obstaculo("barrera_movil", x=160)])
    assert color(antes, 130, 70) == ACERO and color(despues, 130, 70) == BLANCO
    assert color(despues, 190, 70) == ACERO


def test_un_tipo_desconocido_se_dibuja_como_barrera(sin_sprites):
    assert color(pantalla_con([obstaculo("otro")]), 130, 70) == GRIS


def test_no_dibuja_fuera_del_rectangulo():
    assert color(pantalla_con([obstaculo("barrera")]), 20, 20) == BLANCO


def test_sin_obstaculos_no_falla():
    assert color(pantalla_con([]), 130, 70) == BLANCO


# --- con el sprite del muro ---------------------------------------------------------------------


def pixel_del_muro(dx, dy):
    return tuple(sprites.cargar("muro", (30, 30)).get_at((dx, dy)))[:3]


def punto_opaco_del_muro():
    muro = sprites.cargar("muro", (30, 30))
    return next((x, y) for y in range(30) for x in range(30) if muro.get_at((x, y)).a == 255)


def test_la_barrera_se_rellena_con_el_sprite_del_muro_en_cuadros_de_30():
    dx, dy = punto_opaco_del_muro()
    pantalla = pantalla_con([obstaculo("barrera")])  # 60 x 40 en (100, 50)
    assert color(pantalla, 100 + dx, 50 + dy) == pixel_del_muro(dx, dy)
    assert color(pantalla, 130 + dx, 50 + dy) == pixel_del_muro(dx, dy)  # segundo cuadro


def test_el_muro_no_se_sale_del_rectangulo():
    pantalla = pantalla_con([obstaculo("barrera")])  # termina en y = 90
    assert all(color(pantalla, x, y) == BLANCO for x in range(100, 160) for y in range(90, 100))
    assert color(pantalla, 99, 70) == BLANCO and color(pantalla, 160, 70) == BLANCO


def test_la_barrera_movil_lleva_el_muro_y_su_borde():
    dx, dy = 10, 10
    pantalla = pantalla_con([obstaculo("barrera_movil")])
    assert color(pantalla, 100, 70) == BORDE_ACERO
    assert color(pantalla, 100 + dx, 50 + dy) == pixel_del_muro(dx, dy)


def test_la_trampa_y_la_puerta_no_cambian_con_el_muro():
    assert color(pantalla_con([obstaculo("trampa")]), 130, 70) == NARANJA
    assert color(pantalla_con([obstaculo("puerta", abierta=False)]), 130, 70) == MARRON
