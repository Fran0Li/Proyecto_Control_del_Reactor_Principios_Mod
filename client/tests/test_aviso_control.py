"""Aviso en la arena cuando el control físico se desconecta o se reconecta (US-26)."""

import os

import pygame
import pytest

from src.entrada import ControlesJugador
from src.entrada.serial_entrada import REINTENTO_S, SIN_DATOS_S, EntradaSerial
from src.screens.arena import ArenaScreen
from src.screens.aviso_control import (
    COLOR_ALERTA,
    CONECTADO,
    DESCONECTADO,
    DURACION_CONECTADO_S,
    ESPERANDO,
    AvisoControl,
)


class Reloj:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class PuertoFalso:
    def __init__(self):
        self.pendiente = b""
        self.fallar = False

    def enviar(self, texto):
        self.pendiente += texto.encode()

    def read(self, _n):
        if self.fallar:
            raise OSError("cable desconectado")
        datos, self.pendiente = self.pendiente, b""
        return datos

    def close(self):
        pass


@pytest.fixture()
def reloj():
    return Reloj()


#  lógica del aviso


def test_sin_control_fisico_no_hay_aviso(reloj):
    aviso = AvisoControl(reloj)
    aviso.observar(None)
    assert aviso.mensaje() is None


def test_mientras_espera_al_control_avisa_que_se_puede_usar_el_teclado(reloj):
    aviso = AvisoControl(reloj)
    aviso.observar("desconectado")
    assert aviso.mensaje() == (ESPERANDO, "alerta")
    aviso.observar("abierto")  # puerto abierto, todavía sin datos
    assert aviso.mensaje() == (ESPERANDO, "alerta")


def test_al_conectar_confirma_unos_segundos_y_luego_desaparece(reloj):
    aviso = AvisoControl(reloj)
    aviso.observar("abierto")
    aviso.observar("conectado")
    assert aviso.mensaje() == (CONECTADO, "ok")

    reloj.t += DURACION_CONECTADO_S
    aviso.observar("conectado")
    assert aviso.mensaje() is None


def test_si_se_desconecta_despues_de_conectar_lo_dice_y_no_desaparece(reloj):
    aviso = AvisoControl(reloj)
    aviso.observar("conectado")
    aviso.observar("desconectado")
    assert aviso.mensaje() == (DESCONECTADO, "alerta")

    reloj.t += 60
    aviso.observar("desconectado")
    assert aviso.mensaje() == (DESCONECTADO, "alerta")


def test_al_reconectar_vuelve_a_confirmar(reloj):
    aviso = AvisoControl(reloj)
    aviso.observar("conectado")
    reloj.t += 10
    aviso.observar("desconectado")
    aviso.observar("conectado")
    assert aviso.mensaje() == (CONECTADO, "ok")


#  de punta a punta con el adaptador Serial (puerto y reloj falsos)


def test_el_jugador_ve_la_desconexion_y_la_reconexion_del_control(reloj):
    puertos = []

    def abrir(_nombre):
        puertos.append(PuertoFalso())
        return puertos[-1]

    enviados = []
    serial = EntradaSerial("COM3", abrir=abrir, reloj=reloj)
    controles = ControlesJugador([serial], enviados.append)
    aviso = AvisoControl(reloj)

    def cuadro():
        controles.actualizar()
        aviso.observar(controles.control_fisico().estado)
        return aviso.mensaje()

    assert cuadro() == (ESPERANDO, "alerta")  # abre el puerto, el Arduino todavía no habla

    puertos[0].enviar("HELLO CR-PAD-01 1.0\n")
    assert cuadro() == (CONECTADO, "ok")

    reloj.t += SIN_DATOS_S + 0.1  # 3 s sin HB
    assert cuadro() == (DESCONECTADO, "alerta")
    assert {"tipo": "dispositivo", "estado": "desconectado", "id": "CR-PAD-01"} in enviados

    reloj.t += REINTENTO_S  # el cliente vuelve a abrir el puerto solo
    cuadro()
    puertos[-1].enviar("HB\n")
    assert cuadro() == (CONECTADO, "ok")


def test_con_el_cable_desconectado_avisa_de_inmediato(reloj):
    puerto = PuertoFalso()
    serial = EntradaSerial("COM3", abrir=lambda _n: puerto, reloj=reloj)
    controles = ControlesJugador([serial], lambda _m: None)
    aviso = AvisoControl(reloj)

    def cuadro():
        controles.actualizar()
        aviso.observar(serial.estado)
        return aviso.mensaje()

    cuadro()
    puerto.enviar("HELLO CR-PAD-01 1.0\n")
    assert cuadro() == (CONECTADO, "ok")

    puerto.fallar = True  # sin esperar los 3 s
    assert cuadro() == (DESCONECTADO, "alerta")


#  en la pantalla de la arena


@pytest.fixture()
def pantalla():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    yield pygame.display.set_mode((960, 640))
    pygame.quit()


class PanelFalso:
    def __init__(self):
        self.canal = None
        self.estado = None


def test_la_arena_dibuja_el_aviso_arriba_al_centro(pantalla, reloj):
    arena = ArenaScreen(960, 640)
    arena.preparar(PanelFalso(), "lobby")
    serial = EntradaSerial("COM3", abrir=lambda _n: PuertoFalso(), reloj=reloj)
    arena.controles = ControlesJugador([serial], lambda _m: None)
    arena.aviso_control = AvisoControl(reloj)

    arena.update()
    arena.draw(pantalla)

    assert pantalla.get_at((480, 8))[:3] == COLOR_ALERTA


def test_sin_control_fisico_la_arena_no_muestra_aviso(pantalla):
    arena = ArenaScreen(960, 640)
    arena.preparar(PanelFalso(), "lobby")

    arena.update()
    arena.draw(pantalla)

    assert arena.aviso_control.mensaje() is None
