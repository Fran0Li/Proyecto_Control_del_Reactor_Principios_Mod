import asyncio
import os

import pygame
import pytest

from src import api_client, sesion
from src.api_client import ApiError
from src.config import JUGADOR_ID
from src.red import Respuesta
from src.screens import lobby as pantalla_lobby
from src.screens import login
from src.screens.lobby import LobbyScreen
from src.screens.login import LoginScreen

ANCHO = 960
RESPUESTA_LOGIN = {
    "access_token": "abc.def.ghi",
    "token_type": "bearer",
    "usuario": {"id": 7, "nombre_usuario": "luis", "correo": "luis@mail.com"},
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
def sin_sesion():
    sesion.cerrar()
    yield
    sesion.cerrar()


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=boton.rect.center, button=1)


def servidor_falso(monkeypatch, respuesta=None, error=None):
    llamadas = []

    async def falso(usuario, contrasena):
        llamadas.append((usuario, contrasena))
        if error:
            raise error
        return respuesta

    monkeypatch.setattr(login, "iniciar_sesion", falso)
    return llamadas


def entrar(pantalla, usuario="luis", contrasena="Secreta123"):
    async def escenario():
        pantalla.usuario.texto = usuario
        pantalla.contrasena.texto = contrasena
        pantalla.handle_event(clic(pantalla.boton_entrar))
        while pantalla.ocupada():
            await asyncio.sleep(0)

    asyncio.run(escenario())


def test_login_exitoso_guarda_la_sesion_y_va_al_lobby(monkeypatch):
    llamadas = servidor_falso(monkeypatch, RESPUESTA_LOGIN)
    pantalla = LoginScreen(ANCHO)

    entrar(pantalla, usuario=" luis ")

    assert llamadas == [("luis", "Secreta123")]
    assert sesion.actual().token == "abc.def.ghi"
    assert sesion.jugador_id() == 7
    assert pantalla.siguiente_pantalla == "lobby"
    assert pantalla.contrasena.texto == ""


def test_login_con_error_muestra_el_mensaje(monkeypatch):
    servidor_falso(monkeypatch, error=ApiError("Usuario o contraseña incorrectos"))
    pantalla = LoginScreen(ANCHO)

    entrar(pantalla)

    assert pantalla.mensaje == "Usuario o contraseña incorrectos"
    assert pantalla.mensaje_es_error
    assert pantalla.siguiente_pantalla is None
    assert sesion.actual() is None


def test_con_campos_vacios_no_llama_al_servidor(monkeypatch):
    llamadas = servidor_falso(monkeypatch, RESPUESTA_LOGIN)
    pantalla = LoginScreen(ANCHO)

    entrar(pantalla, usuario="", contrasena="")

    assert llamadas == []
    assert pantalla.mensaje_es_error


def test_boton_crear_cuenta_lleva_al_registro():
    pantalla = LoginScreen(ANCHO)

    pantalla.handle_event(clic(pantalla.boton_registro))

    assert pantalla.siguiente_pantalla == "registro"


def test_cerrar_sesion_desde_el_lobby():
    sesion.iniciar("abc", RESPUESTA_LOGIN["usuario"])
    lobby = LobbyScreen(ANCHO)

    lobby.handle_event(clic(lobby.boton_salir))

    assert sesion.actual() is None
    assert lobby.siguiente_pantalla == "login"


def test_sin_sesion_se_usa_el_jugador_del_entorno():
    assert sesion.jugador_id() == JUGADOR_ID


def test_iniciar_sesion_envia_usuario_y_contrasena(monkeypatch):
    llamadas = []

    async def falsa(metodo, url, cuerpo=None, timeout=5.0, headers=None):
        llamadas.append((metodo, url, cuerpo, headers))
        return Respuesta(200, RESPUESTA_LOGIN)

    monkeypatch.setattr(api_client, "solicitar", falsa)

    datos = asyncio.run(api_client.iniciar_sesion("luis", "Secreta123"))

    assert datos == RESPUESTA_LOGIN
    metodo, url, cuerpo, headers = llamadas[0]
    assert metodo == "POST" and url.endswith("/auth/login")
    assert cuerpo == {"usuario": "luis", "contrasena": "Secreta123"}
    assert headers is None


def test_con_token_se_manda_el_header_authorization(monkeypatch):
    llamadas = []

    async def falsa(metodo, url, cuerpo=None, timeout=5.0, headers=None):
        llamadas.append(headers)
        return Respuesta(200, {})

    monkeypatch.setattr(api_client, "solicitar", falsa)

    asyncio.run(api_client._enviar("GET", "/auth/yo", token="abc"))

    assert llamadas == [{"Authorization": "Bearer abc"}]


def test_el_canal_de_la_partida_se_abre_con_el_token_de_la_sesion(monkeypatch):
    sesion.iniciar("token-de-luis", RESPUESTA_LOGIN["usuario"])
    abiertos = []

    async def crear_partida(creador_id):
        return {"id": 4, "escenario": "laboratorio"}

    class PanelFalso:
        async def abrir(self, partida_id, token):
            abiertos.append((partida_id, token))

        def update(self):
            pass

        def cerrar(self):
            pass

    monkeypatch.setattr(pantalla_lobby, "crear_partida", crear_partida)
    lobby = LobbyScreen(ANCHO)
    lobby.panel = PanelFalso()

    async def escenario():
        lobby.handle_event(clic(lobby.boton_crear))
        while lobby.ocupada():
            await asyncio.sleep(0)

    asyncio.run(escenario())

    assert abiertos == [(4, "token-de-luis")]
