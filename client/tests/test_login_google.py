import asyncio
import os

import pygame
import pytest

from src import api_client, sesion
from src.api_client import ApiError
from src.red import Respuesta
from src.screens import login
from src.screens.login import LoginScreen

ANCHO = 960
DATOS = {
    "access_token": "abc",
    "token_type": "bearer",
    "usuario": {"id": 9, "nombre_usuario": "luisserrano", "correo": "luis@gmail.com"},
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
def sin_esperas(monkeypatch):
    monkeypatch.setattr(login, "ESPERA_GOOGLE_S", 0)
    sesion.cerrar()
    yield
    sesion.cerrar()


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=boton.rect.center, button=1)


def entrar_con_google(monkeypatch, respuestas):
    """`respuestas`: lo que devuelve el servidor en cada consulta (None = todavía no)."""
    abiertas = []
    consultas = []
    pendientes = list(respuestas)

    async def resultado(sesion_id):
        consultas.append(sesion_id)
        respuesta = pendientes.pop(0) if pendientes else None
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(login, "abrir_url", abiertas.append)
    monkeypatch.setattr(login, "resultado_login_google", resultado)
    pantalla = LoginScreen(ANCHO)

    async def escenario():
        pantalla.handle_event(clic(pantalla.boton_google))
        while pantalla.ocupada():
            await asyncio.sleep(0)

    asyncio.run(escenario())
    return pantalla, abiertas, consultas


def test_abre_el_navegador_y_entra_cuando_termina(monkeypatch):
    pantalla, abiertas, consultas = entrar_con_google(monkeypatch, [None, None, DATOS])

    assert len(abiertas) == 1
    assert "/auth/google/iniciar?sesion=" in abiertas[0]
    assert len(consultas) == 3
    assert abiertas[0].endswith(consultas[0])  # pregunta por la misma sesión que abrió
    assert sesion.jugador_id() == 9
    assert pantalla.siguiente_pantalla == "lobby"


def test_si_falla_en_google_muestra_el_error(monkeypatch):
    error = ApiError("Se canceló el login con Google", 400)
    pantalla, _, _ = entrar_con_google(monkeypatch, [None, error])

    assert pantalla.mensaje == "Se canceló el login con Google"
    assert pantalla.mensaje_es_error
    assert sesion.actual() is None


def test_si_nunca_termina_avisa_que_se_acabo_el_tiempo(monkeypatch):
    monkeypatch.setattr(login, "INTENTOS_GOOGLE", 3)

    pantalla, _, consultas = entrar_con_google(monkeypatch, [])

    assert len(consultas) == 3
    assert "tiempo" in pantalla.mensaje
    assert pantalla.siguiente_pantalla is None


def respuesta_del_servidor(monkeypatch, respuesta):
    async def falsa(metodo, url, cuerpo=None, timeout=5.0):
        return respuesta

    monkeypatch.setattr(api_client, "solicitar", falsa)


def test_resultado_pendiente_devuelve_none(monkeypatch):
    respuesta_del_servidor(monkeypatch, Respuesta(202, {"detail": "Esperando"}))

    assert asyncio.run(api_client.resultado_login_google("x" * 22)) is None


def test_resultado_listo_devuelve_la_sesion(monkeypatch):
    respuesta_del_servidor(monkeypatch, Respuesta(200, DATOS))

    assert asyncio.run(api_client.resultado_login_google("x" * 22)) == DATOS


def test_resultado_con_error(monkeypatch):
    respuesta_del_servidor(monkeypatch, Respuesta(400, {"detail": "No se pudo entrar"}))

    with pytest.raises(ApiError, match="No se pudo entrar"):
        asyncio.run(api_client.resultado_login_google("x" * 22))
