"""Pantallas del ranking global (US-19) y del historial del jugador (US-20)."""

import asyncio
import os

import pygame
import pytest

from src import api_client
from src.api_client import ApiError
from src.red import Respuesta
from src.screens import historial, ranking
from src.screens.historial import HistorialScreen, describir_partida
from src.screens.lobby import LobbyScreen
from src.screens.ranking import RankingScreen

ANCHO = 960
RANKING = {
    "top": [
        {"posicion": 1, "jugador_id": 5, "nombre": "carla", "puntos_totales": 900, "victorias": 4},
        {"posicion": 2, "jugador_id": 6, "nombre": "beto", "puntos_totales": 700, "victorias": 3},
    ],
    "yo": {"posicion": 14, "jugador_id": 1, "nombre": None, "puntos_totales": 20, "victorias": 0},
}
HISTORIAL = {
    "resumen": {
        "partidas_jugadas": 2,
        "victorias": 1,
        "puntos_totales": 240,
        "mejor_puntaje": 180,
        "logros": 1,
    },
    "partidas": [
        {
            "partida_id": 12,
            "fecha": "2026-11-19T21:30:00",
            "escenario": "planta_industrial",
            "puntaje": 180,
            "posicion": 1,
            "jugadores": 3,
            "gano": True,
        },
        {
            "partida_id": 9,
            "fecha": None,
            "escenario": "laboratorio",
            "puntaje": 60,
            "posicion": None,
            "jugadores": 2,
            "gano": False,
        },
    ],
}
LOGROS = [
    {"clave": "primera_partida", "nombre": "Bautizo nuclear", "obtenido": True},
    {"clave": "energia_300", "nombre": "Sobrecarga", "obtenido": False},
]


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, 640))
    yield
    pygame.quit()


def mostrar(pantalla):
    async def escenario():
        pantalla.al_mostrar()
        while pantalla.ocupada():
            await asyncio.sleep(0)

    asyncio.run(escenario())
    pantalla.draw(pygame.display.get_surface())  # no debe fallar
    return pantalla


def devuelve(valor):
    async def falsa(token):
        if isinstance(valor, Exception):
            raise valor
        return valor

    return falsa


# llamadas al servidor


@pytest.mark.parametrize(
    ("funcion", "ruta"),
    [
        (api_client.obtener_ranking, "/ranking"),
        (api_client.obtener_historial, "/historial"),
        (api_client.obtener_logros, "/logros"),
    ],
)
def test_las_consultas_van_con_el_token(monkeypatch, funcion, ruta):
    llamadas = []

    async def falsa(metodo, url, cuerpo=None, timeout=5.0, headers=None):
        llamadas.append((metodo, url, headers))
        return Respuesta(200, [])

    monkeypatch.setattr(api_client, "solicitar", falsa)

    asyncio.run(funcion("abc"))

    assert llamadas == [("GET", api_client.SERVER_URL + ruta, {"Authorization": "Bearer abc"})]


# ranking


def test_el_ranking_carga_el_top_y_el_puesto_propio(monkeypatch):
    monkeypatch.setattr(ranking, "obtener_ranking", devuelve(RANKING))

    pantalla = mostrar(RankingScreen(ANCHO))

    assert pantalla.ranking == RANKING
    assert pantalla.mensaje == ""


def test_el_ranking_vacio_avisa(monkeypatch):
    monkeypatch.setattr(ranking, "obtener_ranking", devuelve({"top": [], "yo": None}))

    pantalla = mostrar(RankingScreen(ANCHO))

    assert pantalla.mensaje == "Todavía nadie terminó una partida."


def test_el_ranking_muestra_el_error_del_servidor(monkeypatch):
    monkeypatch.setattr(ranking, "obtener_ranking", devuelve(ApiError("Sin conexión")))

    pantalla = mostrar(RankingScreen(ANCHO))

    assert pantalla.mensaje_es_error and pantalla.ranking is None


# historial


def test_el_historial_carga_las_partidas_el_resumen_y_los_logros(monkeypatch):
    monkeypatch.setattr(historial, "obtener_historial", devuelve(HISTORIAL))
    monkeypatch.setattr(historial, "obtener_logros", devuelve(LOGROS))

    pantalla = mostrar(HistorialScreen(ANCHO))

    assert pantalla.historial == HISTORIAL
    assert pantalla.logros == ["Bautizo nuclear"]  # solo los desbloqueados


def test_el_historial_vacio_avisa(monkeypatch):
    vacio = {"resumen": HISTORIAL["resumen"], "partidas": []}
    monkeypatch.setattr(historial, "obtener_historial", devuelve(vacio))
    monkeypatch.setattr(historial, "obtener_logros", devuelve([]))

    pantalla = mostrar(HistorialScreen(ANCHO))

    assert pantalla.mensaje == "Todavía no terminaste ninguna partida."


def test_el_historial_muestra_el_error_del_servidor(monkeypatch):
    monkeypatch.setattr(historial, "obtener_historial", devuelve(ApiError("Sin conexión")))

    pantalla = mostrar(HistorialScreen(ANCHO))

    assert pantalla.mensaje_es_error and pantalla.historial is None


def test_cada_partida_se_describe_en_una_linea():
    reciente, sin_puesto = HISTORIAL["partidas"]

    assert describir_partida(reciente) == (
        "2026-11-19   Partida #12   planta industrial   puesto 1 de 3   180 pts"
    )
    assert "puesto - de 2" in describir_partida(sin_puesto)


@pytest.mark.parametrize("clase", [RankingScreen, HistorialScreen])
def test_volver_lleva_al_lobby(clase):
    pantalla = clase(ANCHO)
    pantalla.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert pantalla.siguiente_pantalla == "lobby"


# lobby


@pytest.mark.parametrize(
    ("boton", "destino"), [("boton_ranking", "ranking"), ("boton_historial", "historial")]
)
def test_el_lobby_lleva_al_ranking_y_al_historial(boton, destino):
    pantalla = LobbyScreen(ANCHO)
    rect = getattr(pantalla, boton).rect

    pantalla.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1))

    assert pantalla.siguiente_pantalla == destino
