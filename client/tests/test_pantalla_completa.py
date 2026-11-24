"""En el celular (Chrome de Android), un toque pone el juego en pantalla completa y horizontal."""

import sys
import types

import pygame
import pytest

from src import navegador


@pytest.fixture
def celular(monkeypatch):
    """Simula el `window` del navegador de un celular; guarda el JavaScript que se le pidió."""
    ejecutado = []
    ventana = types.SimpleNamespace(
        matchMedia=lambda consulta: types.SimpleNamespace(matches=True),
        eval=ejecutado.append,
    )
    monkeypatch.setattr(navegador, "EN_NAVEGADOR", True)
    monkeypatch.setitem(sys.modules, "platform", types.SimpleNamespace(window=ventana))
    return ejecutado


def test_en_la_compu_no_hace_nada():
    assert navegador.pantalla_completa() is False


def test_un_toque_en_el_celular_pide_pantalla_completa_y_horizontal(celular):
    navegador.al_tocar(pygame.event.Event(pygame.FINGERDOWN, x=0.5, y=0.5, finger_id=0))

    assert celular == [navegador.JS_PANTALLA_COMPLETA]
    assert "requestFullscreen" in celular[0] and 'lock("landscape")' in celular[0]


def test_el_clic_generado_por_el_toque_tambien_sirve(celular):
    navegador.al_tocar(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(10, 10), button=1))

    assert len(celular) == 1


def test_otros_eventos_no_piden_nada(celular):
    navegador.al_tocar(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
    navegador.al_tocar(pygame.event.Event(pygame.MOUSEMOTION, pos=(10, 10)))

    assert celular == []


def test_si_ya_esta_en_pantalla_completa_el_js_no_la_vuelve_a_pedir():
    # El propio JavaScript revisa document.fullscreenElement antes de pedirla
    assert navegador.JS_PANTALLA_COMPLETA.index("fullscreenElement") < (
        navegador.JS_PANTALLA_COMPLETA.index("requestFullscreen(")
    )


def test_si_el_navegador_no_deja_el_juego_sigue(monkeypatch, celular):
    def falla(codigo):
        raise RuntimeError("no permitido")

    monkeypatch.setattr(sys.modules["platform"].window, "eval", falla)

    assert navegador.pantalla_completa() is False
