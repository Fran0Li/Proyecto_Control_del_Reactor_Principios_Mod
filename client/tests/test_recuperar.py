import asyncio
import os

import pygame
import pytest

from src.api_client import ApiError
from src.screens import recuperar
from src.screens.login import LoginScreen
from src.screens.recuperar import RecuperarScreen

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


class Servidor:
    def __init__(self, monkeypatch, error_al_pedir=None, error_al_cambiar=None):
        self.pedidos = []
        self.cambios = []

        async def pedir(correo):
            self.pedidos.append(correo)
            if error_al_pedir:
                raise error_al_pedir
            return {}

        async def cambiar(correo, codigo, contrasena):
            self.cambios.append((correo, codigo, contrasena))
            if error_al_cambiar:
                raise error_al_cambiar
            return {}

        monkeypatch.setattr(recuperar, "solicitar_recuperacion", pedir)
        monkeypatch.setattr(recuperar, "restablecer_contrasena", cambiar)


def con_codigo_pedido(monkeypatch, **errores):
    servidor = Servidor(monkeypatch, **errores)
    pantalla = RecuperarScreen(ANCHO)
    pantalla.correo.texto = "luis@mail.com"
    presionar(pantalla, pantalla.boton_pedir)
    return servidor, pantalla


def test_desde_el_login_se_llega_a_recuperar():
    pantalla = LoginScreen(ANCHO)

    pantalla.handle_event(clic(pantalla.boton_recuperar))

    assert pantalla.siguiente_pantalla == "recuperar"


def test_al_principio_solo_se_pide_el_correo():
    pantalla = RecuperarScreen(ANCHO)

    assert pantalla.campos == [pantalla.correo]
    assert not pantalla.codigo_enviado


def test_pedir_el_codigo_muestra_el_paso_2(monkeypatch):
    servidor, pantalla = con_codigo_pedido(monkeypatch)

    assert servidor.pedidos == ["luis@mail.com"]
    assert pantalla.codigo_enviado
    assert pantalla.codigo.activo
    assert not pantalla.mensaje_es_error


def test_con_correo_mal_escrito_no_pide_nada(monkeypatch):
    servidor = Servidor(monkeypatch)
    pantalla = RecuperarScreen(ANCHO)
    pantalla.correo.texto = "luis"

    presionar(pantalla, pantalla.boton_pedir)

    assert servidor.pedidos == []
    assert not pantalla.codigo_enviado
    assert pantalla.mensaje_es_error


def test_cambiar_la_contrasena(monkeypatch):
    servidor, pantalla = con_codigo_pedido(monkeypatch)
    pantalla.codigo.texto = "AB12CD34"
    pantalla.nueva.texto = "Nueva12345"
    pantalla.confirmacion.texto = "Nueva12345"

    presionar(pantalla, pantalla.boton_cambiar)

    assert servidor.cambios == [("luis@mail.com", "AB12CD34", "Nueva12345")]
    assert "Contraseña cambiada" in pantalla.mensaje
    assert not pantalla.codigo_enviado  # vuelve al inicio
    assert pantalla.nueva.texto == ""


def test_contrasenas_distintas_no_llaman_al_servidor(monkeypatch):
    servidor, pantalla = con_codigo_pedido(monkeypatch)
    pantalla.codigo.texto = "AB12CD34"
    pantalla.nueva.texto = "Nueva12345"
    pantalla.confirmacion.texto = "Otra12345"

    presionar(pantalla, pantalla.boton_cambiar)

    assert servidor.cambios == []
    assert pantalla.mensaje == "Las contraseñas no coinciden"


def test_sin_codigo_no_llama_al_servidor(monkeypatch):
    servidor, pantalla = con_codigo_pedido(monkeypatch)
    pantalla.nueva.texto = "Nueva12345"
    pantalla.confirmacion.texto = "Nueva12345"

    presionar(pantalla, pantalla.boton_cambiar)

    assert servidor.cambios == []
    assert pantalla.mensaje_es_error


def test_codigo_incorrecto_muestra_el_error(monkeypatch):
    error = ApiError("El código no es válido", 400)
    _, pantalla = con_codigo_pedido(monkeypatch, error_al_cambiar=error)
    pantalla.codigo.texto = "XXXXXXXX"
    pantalla.nueva.texto = "Nueva12345"
    pantalla.confirmacion.texto = "Nueva12345"

    presionar(pantalla, pantalla.boton_cambiar)

    assert pantalla.mensaje == "El código no es válido"
    assert pantalla.mensaje_es_error
    assert pantalla.codigo_enviado  # se queda en el paso 2 para corregirlo


def test_volver_lleva_al_login():
    pantalla = RecuperarScreen(ANCHO)

    pantalla.handle_event(clic(pantalla.boton_volver))

    assert pantalla.siguiente_pantalla == "login"
