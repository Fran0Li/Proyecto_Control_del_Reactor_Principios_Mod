"""Pruebas del dibujo de los guardianes y del color del jugador por estado (US-15)."""

import os

import pygame
import pytest

from src.screens import dibujo_guardianes
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


@pytest.fixture
def sin_sprites(monkeypatch):
    """Sin la imagen: el guardián es el círculo morado de siempre."""
    monkeypatch.setattr(dibujo_guardianes.sprites, "cargar", lambda *a, **k: None)
    dibujo_guardianes._teñidos.clear()
    yield
    dibujo_guardianes._teñidos.clear()


def pantalla_con(guardianes):
    superficie = pygame.Surface((300, 200))
    superficie.fill(BLANCO)
    dibujar_guardianes(superficie, guardianes)
    return superficie


def color(superficie, x, y):
    return tuple(superficie.get_at((x, y)))[:3]


GUARDIAN = {"id": 1, "x": 150, "y": 100, "radio": 18}


def test_el_guardian_es_un_circulo_morado_con_borde_oscuro(sin_sprites):
    pantalla = pantalla_con([GUARDIAN])
    assert color(pantalla, 150, 100) == MORADO
    assert color(pantalla, 150 + 17, 100) == MORADO_OSCURO


def test_no_dibuja_fuera_del_radio():
    pantalla = pantalla_con([GUARDIAN])
    assert color(pantalla, 150 + 25, 100) == BLANCO


def test_dibuja_varios_guardianes(sin_sprites):
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


# --- con el sprite ------------------------------------------------------------------------------


def test_el_guardian_es_el_tanque_morado_dentro_de_su_aro():
    pantalla = pantalla_con([GUARDIAN])
    assert color(pantalla, 150 + 17, 100) == MORADO_OSCURO  # el aro
    assert color(pantalla, 150, 100) != BLANCO  # el sprite al centro
    assert color(pantalla, 150 + 25, 100) == BLANCO


def test_el_sprite_del_guardian_esta_tenido_de_morado():
    imagen = dibujo_guardianes.sprite_guardian(18)
    assert imagen.get_size() == (32, 32)
    visibles = [imagen.get_at((x, y)) for x in range(32) for y in range(32)]
    visibles = [p for p in visibles if p.a > 0 and (p.r + p.g + p.b) > 60]
    # el tinte deja el verde más bajo que el rojo y el azul: tono morado
    assert visibles and all(p.g <= p.r and p.g <= p.b for p in visibles)
