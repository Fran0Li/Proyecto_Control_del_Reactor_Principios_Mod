"""La arena dibuja el fondo del mapa, el reactor y las celdas con sus sprites (US-09)."""

import os

import pygame
import pytest

from src import sprites
from src.screens import dibujo_reactor
from src.screens.arena import AMARILLO, SPRITE_CELDA
from tests.test_arena import ALTO, ANCHO, ARENA, PanelFalso, arena_con, dibujar

REACTOR = {"x": 480, "y": 270, "radio": 40}


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    yield
    pygame.quit()


@pytest.fixture
def carpeta_falsa(tmp_path, monkeypatch):
    monkeypatch.setattr(sprites, "CARPETA", tmp_path)
    sprites.limpiar_cache()
    yield tmp_path
    sprites.limpiar_cache()


def panel(**extra):
    panel = PanelFalso()
    panel.estado = {"tipo": "estado", "jugadores": [], "arena": ARENA, **extra}
    return panel


def color(superficie, x, y):
    return tuple(superficie.get_at((x, y)))[:3]


def test_la_arena_dibuja_el_fondo_del_escenario_de_la_partida(carpeta_falsa):
    imagen = pygame.Surface((960, 540))
    imagen.fill((10, 20, 30))
    pygame.image.save(imagen, str(carpeta_falsa / "lab.png"))

    superficie = dibujar(arena_con(panel(escenario="laboratorio")))

    assert color(superficie, 5, 5) == (10, 20, 30)


def test_sin_escenario_la_arena_queda_con_el_fondo_liso(carpeta_falsa):
    imagen = pygame.Surface((960, 540))
    imagen.fill((10, 20, 30))
    pygame.image.save(imagen, str(carpeta_falsa / "lab.png"))

    assert color(dibujar(arena_con(panel())), 5, 5) == (255, 255, 255)


def test_si_falta_la_imagen_del_fondo_la_arena_sigue_funcionando(carpeta_falsa):
    assert color(dibujar(arena_con(panel(escenario="militar_que_no_existe"))), 5, 5) == (
        255,
        255,
        255,
    )


def test_la_celda_se_dibuja_con_su_sprite(con_sprites_extra):
    celda = {"id": 1, "x": 300, "y": 200, "valor": 10}
    estado = panel()
    estado.estado["arena"] = {**ARENA, "celdas": [celda]}

    superficie = dibujar(arena_con(estado))

    assert sprites.cargar(SPRITE_CELDA) is not None
    assert color(superficie, 300, 200) != AMARILLO  # ya no es el círculo amarillo
    esquina = sprites.cargar(SPRITE_CELDA, (30, 30)).get_at((0, 0))
    assert esquina.a == 0  # la esquina del sprite es transparente: se ve lo que hay detrás


def test_la_celda_sin_sprite_vuelve_al_circulo_amarillo():
    celda = {"id": 1, "x": 300, "y": 200, "valor": 10}
    estado = panel()
    estado.estado["arena"] = {**ARENA, "celdas": [celda]}

    assert color(dibujar(arena_con(estado)), 300, 200) == AMARILLO


def test_el_reactor_se_dibuja_con_su_sprite_en_la_arena(con_sprites_extra):
    estado = panel(reactor={"energia": 100, "capacidad": 100})
    estado.estado["arena"] = {**ARENA, "reactor": REACTOR}

    superficie = dibujar(arena_con(estado))

    assert sprites.cargar(dibujo_reactor.SPRITE) is not None
    assert color(superficie, 480, 270) != dibujo_reactor.NUCLEO  # no es la figura de antes