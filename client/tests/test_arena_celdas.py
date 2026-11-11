"""Pruebas del dibujo de las celdas de energía en la arena (US-13)."""

import os

import pygame
import pytest

from src.screens.arena import AMARILLO, BLANCO, RADIO_CELDA, ROJO
from tests.test_arena import ALTO, ANCHO, ARENA, PanelFalso, arena_con, dibujar


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    yield
    pygame.quit()


def panel_con_celdas(celdas, jugadores=()):
    panel = PanelFalso()
    panel.estado = {
        "tipo": "estado",
        "jugadores": [{"jugador_id": i, "x": x, "y": y} for i, x, y in jugadores],
        "arena": {**ARENA, "celdas": celdas},
    }
    return panel


def celda(celda_id, x, y, valor=10):
    return {"id": celda_id, "x": x, "y": y, "valor": valor}


def test_una_celda_se_dibuja_amarilla_en_su_posicion():
    arena = arena_con(panel_con_celdas([celda(1, 300, 200)]))

    assert dibujar(arena).get_at((300, 200))[:3] == AMARILLO


def test_la_celda_ocupa_su_radio_y_nada_mas():
    arena = arena_con(panel_con_celdas([celda(1, 300, 200)]))
    superficie = dibujar(arena)

    assert superficie.get_at((300 + RADIO_CELDA - 2, 200))[:3] == AMARILLO
    assert superficie.get_at((300 + RADIO_CELDA + 3, 200))[:3] == BLANCO


def test_se_dibujan_todas_las_celdas():
    celdas = [celda(1, 100, 100), celda(2, 500, 300), celda(3, 800, 400)]
    arena = arena_con(panel_con_celdas(celdas))
    superficie = dibujar(arena)

    for x, y in [(100, 100), (500, 300), (800, 400)]:
        assert superficie.get_at((x, y))[:3] == AMARILLO


def test_si_el_servidor_no_manda_celdas_solo_se_ve_el_fondo():
    panel = PanelFalso([(1, 240, 135)])  # su estado no trae la lista de celdas
    superficie = dibujar(arena_con(panel))

    assert superficie.get_at((600, 300))[:3] == BLANCO


def test_una_celda_recogida_deja_de_dibujarse():
    panel = panel_con_celdas([celda(1, 300, 200)])
    arena = arena_con(panel)
    assert dibujar(arena).get_at((300, 200))[:3] == AMARILLO

    panel.estado["arena"]["celdas"] = []  # el servidor ya no la manda

    assert dibujar(arena).get_at((300, 200))[:3] == BLANCO


def test_los_jugadores_se_dibujan_encima_de_las_celdas():
    arena = arena_con(panel_con_celdas([celda(1, 300, 200)], jugadores=[(1, 300, 200)]))

    assert dibujar(arena).get_at((300, 200))[:3] == ROJO