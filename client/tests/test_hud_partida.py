"""Reloj y tabla de posiciones encima de la arena (US-24 y US-22)."""

import os

import pygame
import pytest

from src.screens.hud_partida import HudPartida, formato_reloj, posiciones, texto_reloj


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((960, 640))
    yield
    pygame.quit()


@pytest.mark.parametrize(
    ("segundos", "texto"), [(300, "5:00"), (61, "1:01"), (9, "0:09"), (0, "0:00"), (-3, "0:00")]
)
def test_el_reloj_se_muestra_en_minutos_y_segundos(segundos, texto):
    assert formato_reloj(segundos) == texto


def test_el_reloj_dice_si_la_partida_no_empezo_o_ya_termino():
    assert texto_reloj({"estado": "esperando"}) == "Esperando inicio"
    assert texto_reloj({"estado": "en_curso", "tiempo_restante": 125}) == "2:05"
    assert texto_reloj({"estado": "finalizada", "tiempo_restante": 0}) == "Fin"


def test_la_tabla_ordena_por_puntaje_y_los_empates_comparten_puesto():
    jugadores = [
        {"jugador_id": 1, "nombre": "ana", "puntaje": 40},
        {"jugador_id": 2, "nombre": "beto", "puntaje": 120},
        {"jugador_id": 3, "nombre": "", "puntaje": 40},
        {"jugador_id": 4, "nombre": "dani", "puntaje": 10},
    ]

    assert posiciones(jugadores) == [
        (1, "beto", 120, 2),
        (2, "ana", 40, 1),
        (2, "Jugador 3", 40, 3),
        (4, "dani", 10, 4),
    ]


def test_la_tabla_cambia_cuando_cambian_los_puntajes():
    antes = [{"jugador_id": 1, "puntaje": 0}, {"jugador_id": 2, "puntaje": 5}]
    despues = [{"jugador_id": 1, "puntaje": 30}, {"jugador_id": 2, "puntaje": 5}]

    assert posiciones(antes)[0][3] == 2
    assert posiciones(despues)[0][3] == 1


@pytest.mark.parametrize(
    "partida",
    [
        {"estado": "esperando"},
        {"estado": "en_curso", "tiempo_restante": 12, "puntaje_objetivo": 500},
        {"estado": "finalizada", "tiempo_restante": 0},
    ],
)
def test_el_hud_se_dibuja_en_cada_estado_de_la_partida(partida):
    pantalla = pygame.display.get_surface()
    pantalla.fill((255, 255, 255))
    estado = {
        "jugadores": [{"jugador_id": 1, "nombre": "ana", "puntaje": 10}],
        "partida": partida,
    }

    HudPartida().dibujar(pantalla, estado, mi_id=1)

    assert pantalla.get_at((pantalla.get_width() - 20, 20))[:3] != (255, 255, 255)  # la tabla


def test_sin_jugadores_no_dibuja_la_tabla():
    pantalla = pygame.display.get_surface()
    pantalla.fill((255, 255, 255))

    HudPartida().dibujar(pantalla, {"jugadores": [], "partida": {"estado": "esperando"}})

    assert pantalla.get_at((pantalla.get_width() - 20, 20))[:3] == (255, 255, 255)
