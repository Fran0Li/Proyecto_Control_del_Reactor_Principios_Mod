import asyncio
import os

import pygame
import pytest

from src import sesion
from src.api_client import ApiError
from src.screens import perfil
from src.screens.lobby import LobbyScreen
from src.screens.perfil import PerfilScreen

ANCHO = 960
PERFIL = {
    "id": 7,
    "nombre_usuario": "luis",
    "correo": "luis@mail.com",
    "descripcion": "",
    "avatar": "azul",
    "fecha_registro": None,
    "con_google": False,
    "partidas_jugadas": 3,
    "victorias": 1,
    "puntos_totales": 420,
}


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, 640))
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def con_sesion():
    sesion.iniciar("token-luis", PERFIL)
    yield
    sesion.cerrar()


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=boton.rect.center, button=1)


class Servidor:
    def __init__(self, monkeypatch, error_al_cargar=None, error_al_guardar=None):
        self.cargas = []
        self.cambios = []

        async def obtener(token):
            self.cargas.append(token)
            if error_al_cargar:
                raise error_al_cargar
            return dict(PERFIL)

        async def editar(token, cambios):
            self.cambios.append((token, cambios))
            if error_al_guardar:
                raise error_al_guardar
            return {**PERFIL, **cambios}

        monkeypatch.setattr(perfil, "obtener_perfil", obtener)
        monkeypatch.setattr(perfil, "editar_perfil", editar)


async def esperar(pantalla):
    while pantalla.ocupada():
        await asyncio.sleep(0)


def abrir_perfil():
    pantalla = PerfilScreen(ANCHO)

    async def escenario():
        pantalla.al_mostrar()
        await esperar(pantalla)

    asyncio.run(escenario())
    return pantalla


def presionar(pantalla, boton):
    async def escenario():
        pantalla.handle_event(clic(boton))
        await esperar(pantalla)

    asyncio.run(escenario())


def test_desde_el_lobby_se_llega_al_perfil():
    lobby = LobbyScreen(ANCHO)

    lobby.handle_event(clic(lobby.boton_perfil))

    assert lobby.siguiente_pantalla == "perfil"


def test_al_abrir_carga_el_perfil_con_el_token_de_la_sesion(monkeypatch):
    servidor = Servidor(monkeypatch)

    pantalla = abrir_perfil()

    assert servidor.cargas == ["token-luis"]
    assert pantalla.perfil["puntos_totales"] == 420
    assert pantalla.nombre.texto == "luis"
    assert pantalla.mensaje == ""


def test_cambiar_avatar_pasa_al_siguiente_color(monkeypatch):
    Servidor(monkeypatch)
    pantalla = abrir_perfil()

    pantalla.handle_event(clic(pantalla.boton_avatar))

    assert pantalla.avatar == "verde"


def test_guardar_manda_los_cambios_y_actualiza_la_sesion(monkeypatch):
    servidor = Servidor(monkeypatch)
    pantalla = abrir_perfil()
    pantalla.nombre.texto = "luis_07"
    pantalla.descripcion.texto = "Me gusta ganar"
    pantalla.handle_event(clic(pantalla.boton_avatar))

    presionar(pantalla, pantalla.boton_guardar)

    token, cambios = servidor.cambios[0]
    assert token == "token-luis"
    assert cambios == {
        "nombre_usuario": "luis_07",
        "descripcion": "Me gusta ganar",
        "avatar": "verde",
    }
    assert sesion.actual().nombre_usuario == "luis_07"
    assert pantalla.mensaje == "Cambios guardados"


def test_nombre_ocupado_muestra_el_error(monkeypatch):
    error = ApiError("El nombre de usuario ya está en uso", 409)
    Servidor(monkeypatch, error_al_guardar=error)
    pantalla = abrir_perfil()
    pantalla.nombre.texto = "ana"

    presionar(pantalla, pantalla.boton_guardar)

    assert pantalla.mensaje == "El nombre de usuario ya está en uso"
    assert pantalla.mensaje_es_error
    assert sesion.actual().nombre_usuario == "luis"


def test_si_la_sesion_ya_no_sirve_vuelve_al_login(monkeypatch):
    Servidor(monkeypatch, error_al_cargar=ApiError("La sesión no es válida", 401))

    pantalla = abrir_perfil()

    assert pantalla.siguiente_pantalla == "login"
    assert sesion.actual() is None


def test_mientras_carga_no_se_puede_guardar(monkeypatch):
    servidor = Servidor(monkeypatch)
    pantalla = PerfilScreen(ANCHO)

    pantalla.handle_event(clic(pantalla.boton_guardar))

    assert servidor.cambios == []


def test_volver_lleva_al_lobby():
    pantalla = PerfilScreen(ANCHO)

    pantalla.handle_event(clic(pantalla.boton_volver))

    assert pantalla.siguiente_pantalla == "lobby"
