import asyncio
import os

import pygame
import pytest

from src import api_client
from src.api_client import ApiError
from src.red import Respuesta
from src.screens import login, registro, verificar_correo
from src.screens.login import LoginScreen
from src.screens.registro import RegistroScreen
from src.screens.verificar_correo import VerificarCorreoScreen

ANCHO = 960


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, 640))
    yield
    pygame.quit()


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=boton.rect.center, button=1)


def presionar(pantalla, boton):
    async def escenario():
        pantalla.handle_event(clic(boton))
        while pantalla.ocupada():
            await asyncio.sleep(0)

    asyncio.run(escenario())


def falso(monkeypatch, modulo, nombre, error=None):
    llamadas = []

    async def funcion(*args):
        llamadas.append(args)
        if error:
            raise error
        return {}

    monkeypatch.setattr(modulo, nombre, funcion)
    return llamadas


def test_despues_de_registrarse_pasa_a_verificar_con_el_correo(monkeypatch):
    falso(monkeypatch, registro, "registrar_usuario")
    pantalla = RegistroScreen(ANCHO)
    pantalla.usuario.texto = "luis"
    pantalla.correo.texto = "luis@mail.com"
    pantalla.contrasena.texto = "Secreta123"
    pantalla.confirmacion.texto = "Secreta123"

    presionar(pantalla, pantalla.boton_crear)

    assert pantalla.siguiente_pantalla == "verificar"
    assert pantalla.correo_pendiente == "luis@mail.com"
    assert pantalla.contrasena.texto == ""


def test_login_sin_verificar_lleva_a_verificar(monkeypatch):
    falso(monkeypatch, login, "iniciar_sesion", ApiError("Verificá tu correo", 403))
    pantalla = LoginScreen(ANCHO)
    pantalla.usuario.texto = "luis@mail.com"
    pantalla.contrasena.texto = "Secreta123"

    presionar(pantalla, pantalla.boton_entrar)

    assert pantalla.siguiente_pantalla == "verificar"
    assert pantalla.correo_pendiente == "luis@mail.com"


def test_login_sin_verificar_con_nombre_de_usuario_no_inventa_el_correo(monkeypatch):
    falso(monkeypatch, login, "iniciar_sesion", ApiError("Verificá tu correo", 403))
    pantalla = LoginScreen(ANCHO)
    pantalla.usuario.texto = "luis"
    pantalla.contrasena.texto = "Secreta123"

    presionar(pantalla, pantalla.boton_entrar)

    assert pantalla.correo_pendiente == ""


def test_reenviar_el_correo(monkeypatch):
    llamadas = falso(monkeypatch, verificar_correo, "reenviar_verificacion")
    pantalla = VerificarCorreoScreen(ANCHO)
    pantalla.preparar("luis@mail.com")

    presionar(pantalla, pantalla.boton_reenviar)

    assert llamadas == [("luis@mail.com",)]
    assert "revisá tu correo" in pantalla.mensaje
    assert not pantalla.mensaje_es_error


def test_reenviar_con_correo_mal_escrito_no_llama_al_servidor(monkeypatch):
    llamadas = falso(monkeypatch, verificar_correo, "reenviar_verificacion")
    pantalla = VerificarCorreoScreen(ANCHO)
    pantalla.preparar("luis")

    presionar(pantalla, pantalla.boton_reenviar)

    assert llamadas == []
    assert pantalla.mensaje_es_error


def test_reenviar_con_error_del_servidor(monkeypatch):
    error = ApiError("No se pudo enviar el correo, probá más tarde", 503)
    falso(monkeypatch, verificar_correo, "reenviar_verificacion", error)
    pantalla = VerificarCorreoScreen(ANCHO)
    pantalla.preparar("luis@mail.com")

    presionar(pantalla, pantalla.boton_reenviar)

    assert pantalla.mensaje == "No se pudo enviar el correo, probá más tarde"
    assert pantalla.mensaje_es_error


def test_el_error_de_la_api_trae_el_codigo_http(monkeypatch):
    async def falsa(metodo, url, cuerpo=None, timeout=5.0):
        return Respuesta(403, {"detail": "Verificá tu correo antes de iniciar sesión"})

    monkeypatch.setattr(api_client, "solicitar", falsa)

    with pytest.raises(ApiError) as error:
        asyncio.run(api_client.iniciar_sesion("luis", "Secreta123"))

    assert error.value.estado == 403
