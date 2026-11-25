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
    """Sin imágenes: los obstáculos se dibujan con sus colores de siempre."""
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


def test_la_trampa_es_naranja(sin_sprites):
    assert color(pantalla_con([obstaculo("trampa")]), 130, 70) == NARANJA


def test_la_puerta_cerrada_es_marron_y_rellena(sin_sprites):
    assert color(pantalla_con([obstaculo("puerta", abierta=False)]), 130, 70) == MARRON


def test_la_puerta_abierta_solo_dibuja_el_contorno(sin_sprites):
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


# con el sprite del muro


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


# con el sprite de la trampa


def test_la_trampa_se_rellena_con_su_sprite_en_cuadros_de_30():
    trampa = sprites.cargar("trampa", (30, 30))
    dx, dy = next((x, y) for y in range(30) for x in range(30) if trampa.get_at((x, y)).a == 255)
    esperado = tuple(trampa.get_at((dx, dy)))[:3]
    pantalla = pantalla_con([obstaculo("trampa")])  # 60 x 40 en (100, 50)
    assert color(pantalla, 100 + dx, 50 + dy) == esperado
    assert color(pantalla, 130 + dx, 50 + dy) == esperado  # segundo cuadro
    assert color(pantalla, 99, 70) == BLANCO and color(pantalla, 160, 70) == BLANCO


def test_la_trampa_no_tapa_el_suelo_donde_el_sprite_es_transparente():
    trampa = sprites.cargar("trampa", (30, 30))
    transparente = [(x, y) for y in range(30) for x in range(30) if trampa.get_at((x, y)).a == 0]
    if not transparente:
        pytest.skip("el sprite de la trampa no tiene huecos")
    dx, dy = transparente[0]
    assert color(pantalla_con([obstaculo("trampa")]), 100 + dx, 50 + dy) == BLANCO


# con el sprite de la puerta (muro intermitente)


def sprite_de_puerta():
    return sprites.cargar("muro_intermitente", (30, 30))


def punto_opaco_de_puerta():
    puerta = sprite_de_puerta()
    return next((x, y) for y in range(30) for x in range(30) if puerta.get_at((x, y)).a == 255)


def test_la_puerta_cerrada_lleva_el_sprite_normal():
    dx, dy = punto_opaco_de_puerta()
    pantalla = pantalla_con([obstaculo("puerta", abierta=False)])
    assert color(pantalla, 100 + dx, 50 + dy) == tuple(sprite_de_puerta().get_at((dx, dy)))[:3]


def test_la_puerta_abierta_es_el_mismo_sprite_pero_mas_oscuro():
    dx, dy = punto_opaco_de_puerta()
    cerrada = color(pantalla_con([obstaculo("puerta", abierta=False)]), 100 + dx, 50 + dy)
    abierta = color(pantalla_con([obstaculo("puerta", abierta=True)]), 100 + dx, 50 + dy)
    assert sum(abierta) < sum(cerrada)
    assert abierta != BLANCO


def test_la_puerta_abierta_sigue_ocupando_el_mismo_rectangulo():
    pantalla = pantalla_con([obstaculo("puerta", abierta=True)])
    assert color(pantalla, 99, 70) == BLANCO and color(pantalla, 160, 70) == BLANCO
    assert color(pantalla, 130, 90) == BLANCO


def test_al_abrir_y_cerrar_el_dibujo_cambia_cada_vez():
    dx, dy = punto_opaco_de_puerta()
    punto = (100 + dx, 50 + dy)
    estados = [
        color(pantalla_con([obstaculo("puerta", abierta=a)]), *punto) for a in (False, True, False)
    ]
    assert estados[0] == estados[2] != estados[1]


def test_el_sprite_original_de_la_puerta_no_se_oscurece_para_siempre():
    dx, dy = punto_opaco_de_puerta()
    antes = tuple(sprite_de_puerta().get_at((dx, dy)))
    pantalla_con([obstaculo("puerta", abierta=True)])
    assert tuple(sprite_de_puerta().get_at((dx, dy))) == antes


def test_estan_las_imagenes_de_la_trampa_y_la_puerta():
    for nombre in ("trampa", "muro_intermitente"):
        assert (sprites.CARPETA / f"{nombre}.png").exists(), f"falta {nombre}.png"
        assert sprites.cargar(nombre, (30, 30)) is not None


def test_sin_imagen_la_puerta_vuelve_a_sus_colores(sin_sprites):
    assert color(pantalla_con([obstaculo("puerta", abierta=False)]), 130, 70) == MARRON
    assert color(pantalla_con([obstaculo("puerta", abierta=True)]), 100, 70) == VERDE