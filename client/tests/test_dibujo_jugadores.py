"""Pruebas de los sprites de los jugadores en la arena."""

import os

import pygame
import pytest

from src import sprites
from src.screens import dibujo_jugadores
from src.screens.dibujo_guardianes import AZUL_ESCUDO, GRIS_ATURDIDO, ROJO
from src.screens.dibujo_jugadores import (
    COLORES_NUMERO,
    MARGEN_SPRITE,
    color_aro,
    dibujar_jugador,
    sprite_jugador,
)

BLANCO = (255, 255, 255)
RADIO = 20


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    yield
    pygame.quit()


def pantalla_con(**datos):
    superficie = pygame.Surface((200, 200))
    superficie.fill(BLANCO)
    dibujar_jugador(superficie, 100, 100, RADIO, **datos)
    return superficie


def color(superficie, x, y):
    return tuple(superficie.get_at((x, y)))[:3]


def test_estan_los_cuatro_personajes_y_el_muro():
    for nombre in ("jugador_1", "jugador_2", "jugador_3", "jugador_4", "muro"):
        assert (sprites.CARPETA / f"{nombre}.png").exists()
        assert sprites.cargar(nombre) is not None


def test_el_personaje_cabe_dentro_del_aro():
    imagen = sprite_jugador(1, RADIO)
    lado = 2 * (RADIO - MARGEN_SPRITE)
    assert imagen.get_size() == (lado, lado)


def test_cada_numero_tiene_su_personaje_y_su_color():
    imagenes = [pygame.image.tobytes(sprite_jugador(n, RADIO), "RGBA") for n in (1, 2, 3, 4)]
    assert len(set(imagenes)) == 4
    assert len(set(COLORES_NUMERO.values())) == 4
    assert color_aro(1, "normal") == ROJO


def test_sin_numero_o_con_uno_raro_usa_el_primero():
    uno = pygame.image.tobytes(sprite_jugador(1, RADIO), "RGBA")
    assert pygame.image.tobytes(sprite_jugador(None, RADIO), "RGBA") == uno
    assert pygame.image.tobytes(sprite_jugador(9, RADIO), "RGBA") == uno


def test_dibuja_el_aro_del_color_de_su_numero_y_el_personaje_adentro():
    pantalla = pantalla_con(numero=2)
    assert color(pantalla, 100 + RADIO - 1, 100) == COLORES_NUMERO[2]
    assert color(pantalla, 100, 100) != BLANCO
    assert color(pantalla, 100 + RADIO + 3, 100) == BLANCO


def test_aturdido_se_ve_gris():
    assert color_aro(3, "aturdido") == GRIS_ATURDIDO
    imagen = sprite_jugador(1, RADIO, aturdido=True)
    w, h = imagen.get_size()
    pixeles = [imagen.get_at((x, y)) for x in range(w) for y in range(h)]
    visibles = [p for p in pixeles if p.a > 0]
    assert visibles and all(p.r == p.g == p.b for p in visibles)


def test_escudado_tiene_el_aro_azul_y_mas_grueso():
    pantalla = pantalla_con(numero=1, estado="escudado")
    assert color(pantalla, 100 + RADIO - 4, 100) == AZUL_ESCUDO
    assert color_aro(1, "escudado") == AZUL_ESCUDO


def test_la_etiqueta_va_arriba_del_jugador():
    fuente = pygame.font.Font(None, 20)
    sin = pantalla_con(numero=1)
    con = pantalla_con(numero=1, propio=True, fuente=fuente)
    franja = [(x, y) for x in range(80, 121) for y in range(60, 79)]
    assert all(color(sin, x, y) == BLANCO for x, y in franja)
    assert any(color(con, x, y) != BLANCO for x, y in franja)


def test_si_falta_la_imagen_dibuja_el_circulo_de_antes(monkeypatch):
    monkeypatch.setattr(dibujo_jugadores.sprites, "cargar", lambda *a, **k: None)
    pantalla = pantalla_con(numero=3)
    assert color(pantalla, 100, 100) == COLORES_NUMERO[3]


def test_una_imagen_que_no_existe_devuelve_none():
    assert sprites.cargar("no_existe") is None
