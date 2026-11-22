"""El reactor central se ve en la arena."""

import os

import pygame
import pytest

from src.screens.dibujo_reactor import CARCASA, NUCLEO, NUCLEO_APAGADO
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


def panel_con_reactor(energia=100, capacidad=100):
    panel = PanelFalso()
    panel.estado = {
        "tipo": "estado",
        "jugadores": [],
        "arena": {**ARENA, "reactor": REACTOR},
        "reactor": {"energia": energia, "capacidad": capacidad},
    }
    return panel


def test_el_reactor_se_dibuja_al_centro_de_la_arena():
    superficie = dibujar(arena_con(panel_con_reactor()))

    assert tuple(superficie.get_at((480, 270)))[:3] == NUCLEO
    assert tuple(superficie.get_at((480 + 33, 270)))[:3] == CARCASA


def test_el_reactor_se_apaga_cuando_se_le_acaba_la_energia():
    superficie = dibujar(arena_con(panel_con_reactor(energia=0)))

    assert tuple(superficie.get_at((480, 270)))[:3] == NUCLEO_APAGADO


def test_si_el_servidor_no_manda_el_reactor_no_se_dibuja_nada():
    panel = PanelFalso()
    panel.estado = {"tipo": "estado", "jugadores": [], "arena": ARENA}

    assert tuple(dibujar(arena_con(panel)).get_at((480, 270)))[:3] == (255, 255, 255)


def test_si_falta_la_energia_se_dibuja_lleno():
    panel = PanelFalso()
    panel.estado = {
        "tipo": "estado",
        "jugadores": [],
        "arena": {**ARENA, "reactor": REACTOR},
    }

    assert tuple(dibujar(arena_con(panel)).get_at((480, 270)))[:3] == NUCLEO