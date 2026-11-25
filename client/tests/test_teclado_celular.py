"""En el celular, tocar un campo de texto abre el cuadro del navegador con el teclado."""

import os
import sys
import types

import pygame
import pytest

from src import navegador
from src.screens.componentes import CampoTexto


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((960, 640))
    yield
    pygame.quit()


def toque(campo):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=campo.rect.center, button=1)


def campo_nuevo(oculto=False):
    return CampoTexto(pygame.Rect(300, 200, 360, 42), "Usuario", oculto)


@pytest.fixture
def celular(monkeypatch):
    """Simula el `window` del navegador de un celular; guarda lo que se le preguntó."""
    preguntas = []
    respuestas = []

    class Consulta:
        matches = True

    ventana = types.SimpleNamespace(
        matchMedia=lambda consulta: Consulta(),
        prompt=lambda etiqueta, actual: preguntas.append((etiqueta, actual)) or respuestas.pop(0),
    )
    monkeypatch.setattr(navegador, "EN_NAVEGADOR", True)
    monkeypatch.setitem(sys.modules, "platform", types.SimpleNamespace(window=ventana))
    return preguntas, respuestas


def test_en_escritorio_no_se_abre_ningun_cuadro():
    assert navegador.es_pantalla_tactil() is False
    assert navegador.pedir_texto("Usuario") is None


def test_en_el_celular_tocar_el_campo_pide_el_texto(celular):
    preguntas, respuestas = celular
    respuestas.append("francisco")
    campo = campo_nuevo()

    campo.handle_event(toque(campo))

    assert campo.activo and campo.texto == "francisco"
    assert preguntas == [("Usuario", "")]


def test_si_se_cancela_el_campo_queda_como_estaba(celular):
    _, respuestas = celular
    respuestas.append(None)
    campo = campo_nuevo()
    campo.texto = "ana"

    campo.handle_event(toque(campo))

    assert campo.texto == "ana"


def test_la_contrasena_no_se_muestra_en_el_cuadro(celular):
    preguntas, respuestas = celular
    respuestas.append("nueva123")
    campo = campo_nuevo(oculto=True)
    campo.texto = "vieja"

    campo.handle_event(toque(campo))

    assert preguntas == [("Usuario", "")]  # no se le pasa la contraseña anterior
    assert campo.texto == "nueva123"


def test_respeta_el_largo_maximo_y_quita_saltos_de_linea(celular):
    _, respuestas = celular
    respuestas.append("a\nb" + "c" * 200)
    campo = campo_nuevo()

    campo.handle_event(toque(campo))

    assert campo.texto.startswith("abc") and len(campo.texto) == campo.largo_maximo


def test_tocar_fuera_del_campo_no_pide_nada(celular):
    preguntas, _ = celular
    campo = campo_nuevo()

    campo.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(5, 5), button=1))

    assert preguntas == [] and not campo.activo


def test_en_un_navegador_de_compu_se_escribe_con_el_teclado_normal(celular, monkeypatch):
    preguntas, _ = celular
    ventana = sys.modules["platform"].window
    monkeypatch.setattr(
        ventana, "matchMedia", lambda consulta: types.SimpleNamespace(matches=False)
    )
    campo = campo_nuevo()

    campo.handle_event(toque(campo))

    assert preguntas == [] and campo.activo
