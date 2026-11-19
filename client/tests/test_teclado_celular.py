"""Campos de texto en el celular: al tocarlos se abre el cuadro de texto del navegador."""

import os

import pygame
import pytest

from src import navegador
from src.screens.componentes import CampoTexto


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((400, 300))
    yield
    pygame.quit()


def tocar(campo, dentro=True):
    pos = campo.rect.center if dentro else (campo.rect.right + 50, campo.rect.bottom + 50)
    campo.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


def campo_con_teclado(respuesta, oculto=False):
    pedidos = []

    def pedir(etiqueta, actual):
        pedidos.append((etiqueta, actual))
        return respuesta

    campo = CampoTexto(pygame.Rect(10, 40, 200, 40), "Usuario", oculto=oculto)
    campo.pedir_texto = pedir
    return campo, pedidos


def test_en_escritorio_no_se_pide_el_texto_aparte():
    assert not navegador.es_pantalla_tactil()
    assert CampoTexto(pygame.Rect(0, 0, 100, 30), "Correo").pedir_texto is None


def test_al_tocar_el_campo_se_escribe_lo_del_teclado_del_celular():
    campo, pedidos = campo_con_teclado("luis_serrano")
    campo.texto = "lu"

    tocar(campo)

    assert pedidos == [("Usuario", "lu")]
    assert campo.texto == "luis_serrano" and campo.activo


def test_si_cancela_queda_lo_que_habia():
    campo, _ = campo_con_teclado(None)
    campo.texto = "luis"

    tocar(campo)

    assert campo.texto == "luis"


def test_la_contrasena_no_se_muestra_en_el_cuadro():
    campo, pedidos = campo_con_teclado("Secreta123", oculto=True)
    campo.texto = "vieja"

    tocar(campo)

    assert pedidos == [("Usuario", "")]
    assert campo.texto == "Secreta123"


def test_respeta_el_largo_maximo():
    campo, _ = campo_con_teclado("x" * 500)
    campo.largo_maximo = 30

    tocar(campo)

    assert campo.texto == "x" * 30


def test_tocar_fuera_del_campo_no_abre_el_teclado():
    campo, pedidos = campo_con_teclado("nada")

    tocar(campo, dentro=False)

    assert pedidos == [] and not campo.activo
