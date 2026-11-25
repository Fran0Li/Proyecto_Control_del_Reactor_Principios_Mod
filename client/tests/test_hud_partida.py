"""Reloj y tabla de posiciones encima de la arena (US-24 y US-22)."""

import os

import pygame
import pytest

from src.screens.hud_partida import (
    COLOR_EVENTO,
    COLORES_EVENTO,
    HudPartida,
    formato_evento,
    formato_reloj,
    posiciones,
    texto_reloj,
)


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


def estado_con_evento(evento):
    partida = {"estado": "en_curso", "tiempo_restante": 100, "puntaje_objetivo": 500}
    if evento:
        partida["evento"] = evento
    return {"jugadores": [{"jugador_id": 1, "nombre": "ana", "puntaje": 10}], "partida": partida}


def dibujar_y_pintar(evento):
    pantalla = pygame.display.get_surface()
    pantalla.fill((255, 255, 255))
    HudPartida().dibujar(pantalla, estado_con_evento(evento), mi_id=1)
    return pantalla


def test_el_evento_se_escribe_con_su_nombre_y_los_segundos():
    assert formato_evento({"nombre": "Invasión", "restante": 8}) == ("Invasión", "8 s")
    assert formato_evento({"nombre": "Puntos dobles", "restante": 0}) == ("Puntos dobles", "0 s")


def test_el_cuadro_crece_solo_cuando_hay_un_evento():
    x, y = pygame.display.get_surface().get_width() - 20, 100
    evento = {"clave": "invasion", "nombre": "Invasión", "restante": 7}
    assert dibujar_y_pintar(None).get_at((x, y))[:3] == (255, 255, 255)
    assert dibujar_y_pintar(evento).get_at((x, y))[:3] != (255, 255, 255)


def hay_color(pantalla, color):
    ancho = pantalla.get_width()
    zona = pygame.Rect(ancho - 252, 12, 240, 110)
    return any(
        pantalla.get_at((x, y))[:3] == color
        for x in range(zona.left, zona.right)
        for y in range(zona.top, zona.bottom)
    )


@pytest.mark.parametrize("clave", sorted(COLORES_EVENTO))
def test_cada_evento_se_pinta_de_su_color(clave):
    pantalla = dibujar_y_pintar({"clave": clave, "nombre": "X", "restante": 5})
    assert hay_color(pantalla, COLORES_EVENTO[clave])


def test_un_evento_desconocido_usa_el_color_por_defecto():
    pantalla = dibujar_y_pintar({"clave": "otro", "nombre": "Otro", "restante": 5})
    assert hay_color(pantalla, COLOR_EVENTO)


def test_sin_evento_no_hay_color_de_evento():
    pantalla = dibujar_y_pintar(None)
    assert not any(hay_color(pantalla, c) for c in COLORES_EVENTO.values())