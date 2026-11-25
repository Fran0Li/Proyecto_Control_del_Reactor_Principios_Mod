"""Botones y campos responden al dedo (iPhone y Android) sin presionarse dos veces."""

import os

import pygame
import pytest

from src.screens.componentes import Boton, CampoTexto, punto_presionado

ANCHO, ALTO = 960, 640


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    yield
    pygame.quit()


def dedo(x, y):
    return pygame.event.Event(pygame.FINGERDOWN, x=x / ANCHO, y=y / ALTO, finger_id=0)


def clic(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1)


def boton():
    return Boton(pygame.Rect(400, 300, 200, 50), "Entrar")


def test_el_dedo_presiona_el_boton_aunque_no_llegue_clic_de_mouse():
    """Así pasa en el iPhone: Safari solo manda el evento del dedo."""
    assert boton().fue_presionado(dedo(500, 325))


def test_el_dedo_fuera_del_boton_no_lo_presiona():
    assert not boton().fue_presionado(dedo(100, 100))


def test_con_el_clic_que_android_inventa_despues_del_dedo_no_se_presiona_dos_veces():
    b = boton()
    presiones = [b.fue_presionado(dedo(500, 325)), b.fue_presionado(clic(500, 325))]

    assert presiones == [True, False]


def test_en_la_compu_el_clic_sigue_funcionando():
    assert boton().fue_presionado(clic(500, 325))
    assert not boton().fue_presionado(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(500, 325), button=3)
    )


def test_el_dedo_activa_el_campo_de_texto_y_desactiva_los_otros():
    usuario = CampoTexto(pygame.Rect(300, 200, 360, 42), "Usuario")
    clave = CampoTexto(pygame.Rect(300, 280, 360, 42), "Contraseña", oculto=True)
    usuario.activo = True

    evento = dedo(400, 300)
    usuario.handle_event(evento)
    clave.handle_event(evento)

    assert clave.activo and not usuario.activo


def test_otros_eventos_no_son_presiones():
    assert punto_presionado(pygame.event.Event(pygame.MOUSEMOTION, pos=(1, 1))) is None
    assert punto_presionado(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)) is None
