"""Pantalla de administración y rol en la sesión (US-28)."""

import asyncio
import os

import pygame
import pytest

from src import api_client, sesion
from src.api_client import ApiError
from src.red import Respuesta
from src.screens import admin
from src.screens.admin import AdminScreen
from src.screens.lobby import LobbyScreen

ANCHO = 960
ESTADISTICAS = {
    "usuarios_registrados": 3,
    "usuarios_bloqueados": 1,
    "partidas_jugadas": 5,
    "partidas_activas": 1,
    "mejores_puntajes": [{"nombre": "ana", "puntaje": 300, "partida_id": 4}],
}
USUARIOS = [
    {"id": 1, "nombre_usuario": "jefe", "rol": "administrador", "bloqueado": False},
    {"id": 2, "nombre_usuario": "ana", "rol": "jugador", "bloqueado": False},
    {"id": 3, "nombre_usuario": "beto", "rol": "jugador", "bloqueado": True},
]
PARTIDAS = [{"id": 8, "estado": "en_curso", "escenario": "laboratorio", "jugadores": 2}]


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, 640))
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def sin_sesion():
    sesion.cerrar()
    yield
    sesion.cerrar()


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=boton.rect.center, button=1)


def tocar(pantalla, boton):
    """Clic en un botón y espera a que termine lo que pidió al servidor."""

    async def escenario():
        pantalla.handle_event(clic(boton))
        while pantalla.ocupada():
            await asyncio.sleep(0)

    asyncio.run(escenario())


def pantalla_admin(monkeypatch, error=None):
    acciones = []

    async def estadisticas(token):
        if error:
            raise error
        return ESTADISTICAS

    async def usuarios(token):
        return USUARIOS

    async def partidas(token):
        return PARTIDAS

    async def bloquear(token, usuario_id, bloquear):
        acciones.append(("bloquear" if bloquear else "desbloquear", usuario_id))

    async def cerrar(token, partida_id):
        acciones.append(("cerrar", partida_id))

    for nombre, falsa in (
        ("admin_estadisticas", estadisticas),
        ("admin_usuarios", usuarios),
        ("admin_partidas", partidas),
        ("admin_bloquear", bloquear),
        ("admin_cerrar_partida", cerrar),
    ):
        monkeypatch.setattr(admin, nombre, falsa)

    pantalla = AdminScreen(ANCHO)

    async def mostrar():
        pantalla.al_mostrar()
        while pantalla.ocupada():
            await asyncio.sleep(0)

    asyncio.run(mostrar())
    return pantalla, acciones


# sesión y lobby


def test_la_sesion_guarda_el_rol():
    assert not sesion.iniciar("t", {"id": 1, "nombre_usuario": "ana"}).es_admin  # sin rol
    jefe = sesion.iniciar("t", {"id": 2, "nombre_usuario": "jefe", "rol": "administrador"})
    assert jefe.es_admin


def test_el_boton_de_administracion_solo_sirve_para_un_admin():
    lobby = LobbyScreen(ANCHO)
    sesion.iniciar("t", {"id": 1, "nombre_usuario": "ana", "rol": "jugador"})
    lobby.handle_event(clic(lobby.boton_admin))
    assert lobby.siguiente_pantalla is None

    sesion.iniciar("t", {"id": 2, "nombre_usuario": "jefe", "rol": "administrador"})
    lobby.handle_event(clic(lobby.boton_admin))
    assert lobby.siguiente_pantalla == "admin"
    lobby.draw(pygame.display.get_surface())


# llamadas al servidor


@pytest.mark.parametrize(
    ("llamada", "metodo", "ruta"),
    [
        (lambda: api_client.admin_estadisticas("t"), "GET", "/admin/estadisticas"),
        (lambda: api_client.admin_usuarios("t"), "GET", "/admin/usuarios"),
        (lambda: api_client.admin_partidas("t"), "GET", "/admin/partidas"),
        (lambda: api_client.admin_bloquear("t", 3, True), "POST", "/admin/usuarios/3/bloquear"),
        (
            lambda: api_client.admin_bloquear("t", 3, False),
            "POST",
            "/admin/usuarios/3/desbloquear",
        ),
        (lambda: api_client.admin_cerrar_partida("t", 8), "POST", "/admin/partidas/8/cerrar"),
    ],
)
def test_las_llamadas_de_administracion(monkeypatch, llamada, metodo, ruta):
    enviadas = []

    async def falsa(metodo, url, cuerpo=None, timeout=5.0, headers=None):
        enviadas.append((metodo, url, headers))
        return Respuesta(200, {})

    monkeypatch.setattr(api_client, "solicitar", falsa)

    asyncio.run(llamada())

    assert enviadas == [(metodo, api_client.SERVER_URL + ruta, {"Authorization": "Bearer t"})]


# pantalla


def test_carga_estadisticas_usuarios_y_partidas(monkeypatch):
    pantalla, _ = pantalla_admin(monkeypatch)

    assert pantalla.estadisticas == ESTADISTICAS
    assert [u["nombre_usuario"] for _, u in pantalla.botones_usuarios] == ["ana", "beto"]
    assert [b.texto for b, _ in pantalla.botones_usuarios] == ["Bloquear", "Desbloquear"]
    pantalla.draw(pygame.display.get_surface())


def test_bloquear_y_desbloquear_desde_la_lista(monkeypatch):
    pantalla, acciones = pantalla_admin(monkeypatch)
    (boton_ana, _), (boton_beto, _) = pantalla.botones_usuarios

    tocar(pantalla, boton_ana)
    tocar(pantalla, boton_beto)

    assert acciones == [("bloquear", 2), ("desbloquear", 3)]
    assert pantalla.mensaje == "beto quedó desbloqueado"


def test_cerrar_una_partida_colgada(monkeypatch):
    pantalla, acciones = pantalla_admin(monkeypatch)
    (boton, _), = pantalla.botones_partidas

    tocar(pantalla, boton)

    assert acciones == [("cerrar", 8)]
    assert pantalla.mensaje == "Partida #8 cerrada"


def test_si_el_servidor_niega_el_acceso_se_muestra_el_motivo(monkeypatch):
    pantalla, _ = pantalla_admin(monkeypatch, ApiError("Solo un administrador puede hacer esto"))

    assert pantalla.mensaje == "Solo un administrador puede hacer esto"
    assert pantalla.mensaje_es_error
    pantalla.draw(pygame.display.get_surface())


def test_volver_lleva_al_lobby():
    pantalla = AdminScreen(ANCHO)
    pantalla.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert pantalla.siguiente_pantalla == "lobby"
