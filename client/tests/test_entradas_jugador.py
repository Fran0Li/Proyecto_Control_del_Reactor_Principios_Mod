"""Pruebas de las entradas del jugador: teclado, táctil y envío al servidor (US-25, AB#40)."""

import pygame
import pytest

from src.entrada import ControlesJugador, EntradaSerial, Tactil, Teclado, crear_fuentes
from src.entrada.base import FuenteEntrada


def tecla(tipo, key):
    return pygame.event.Event(tipo, key=key)


def abajo(key):
    return tecla(pygame.KEYDOWN, key)


def arriba(key):
    return tecla(pygame.KEYUP, key)


# ---- Teclado -------------------------------------------------------------------------------


def test_teclado_mapea_flechas_wasd_y_espacio():
    teclado = Teclado()
    for key in (pygame.K_UP, pygame.K_a, pygame.K_SPACE):
        teclado.procesar(abajo(key))
    assert teclado.obtener() == [
        ("arriba", "presionado"),
        ("izquierda", "presionado"),
        ("accion", "presionado"),
    ]


def test_teclado_ignora_teclas_fuera_del_contrato():
    teclado = Teclado()
    teclado.procesar(abajo(pygame.K_q))
    teclado.procesar(arriba(pygame.K_q))
    assert teclado.obtener() == []


def test_teclado_no_repite_presionado_con_repeticion_de_teclas():
    teclado = Teclado()
    for _ in range(3):
        teclado.procesar(abajo(pygame.K_RIGHT))
    teclado.procesar(arriba(pygame.K_RIGHT))
    assert teclado.obtener() == [("derecha", "presionado"), ("derecha", "liberado")]


def test_teclado_dos_teclas_del_mismo_control_sueltan_al_final():
    teclado = Teclado()
    teclado.procesar(abajo(pygame.K_UP))
    teclado.procesar(abajo(pygame.K_w))
    teclado.procesar(arriba(pygame.K_UP))
    assert teclado.obtener() == [("arriba", "presionado")]
    teclado.procesar(arriba(pygame.K_w))
    assert teclado.obtener() == [("arriba", "liberado")]


def test_teclado_suelta_todo_al_perder_el_foco():
    teclado = Teclado()
    teclado.procesar(abajo(pygame.K_LEFT))
    teclado.procesar(abajo(pygame.K_SPACE))
    teclado.obtener()
    teclado.procesar(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    assert sorted(teclado.obtener()) == [("accion", "liberado"), ("izquierda", "liberado")]


# ---- Táctil --------------------------------------------------------------------------------


def clic(tipo, pos):
    return pygame.event.Event(tipo, pos=pos, button=1)


def dedo(tipo, finger_id, x, y, tactil):
    # los eventos de dedo vienen normalizados de 0 a 1
    return pygame.event.Event(
        tipo, finger_id=finger_id, x=x / tactil.ancho, y=y / tactil.alto, touch_id=0
    )


def test_tactil_presiona_y_suelta_con_el_mouse():
    tactil = Tactil(960, 640)
    centro = tactil.botones["derecha"].center
    tactil.procesar(clic(pygame.MOUSEBUTTONDOWN, centro))
    tactil.procesar(clic(pygame.MOUSEBUTTONUP, centro))
    assert tactil.obtener() == [("derecha", "presionado"), ("derecha", "liberado")]


def test_tactil_dos_dedos_a_la_vez():
    tactil = Tactil(960, 640)
    tactil.procesar(dedo(pygame.FINGERDOWN, 1, *tactil.botones["arriba"].center, tactil))
    tactil.procesar(dedo(pygame.FINGERDOWN, 2, *tactil.botones["accion"].center, tactil))
    tactil.procesar(dedo(pygame.FINGERUP, 1, 0, 0, tactil))
    assert tactil.obtener() == [
        ("arriba", "presionado"),
        ("accion", "presionado"),
        ("arriba", "liberado"),
    ]


def test_tactil_arrastrar_el_dedo_cambia_de_boton():
    tactil = Tactil(960, 640)
    tactil.procesar(dedo(pygame.FINGERDOWN, 1, *tactil.botones["izquierda"].center, tactil))
    tactil.procesar(dedo(pygame.FINGERMOTION, 1, *tactil.botones["abajo"].center, tactil))
    assert tactil.obtener() == [
        ("izquierda", "presionado"),
        ("abajo", "presionado"),
        ("izquierda", "liberado"),
    ]


def test_tactil_ignora_el_mouse_sintetico_despues_de_un_toque():
    tactil = Tactil(960, 640)
    centro = tactil.botones["arriba"].center
    tactil.procesar(dedo(pygame.FINGERDOWN, 1, *centro, tactil))
    tactil.procesar(clic(pygame.MOUSEBUTTONDOWN, centro))  # el navegador lo genera del toque
    tactil.procesar(dedo(pygame.FINGERUP, 1, *centro, tactil))
    tactil.procesar(clic(pygame.MOUSEBUTTONUP, centro))
    assert tactil.obtener() == [("arriba", "presionado"), ("arriba", "liberado")]


def test_tactil_toque_fuera_de_los_botones_no_genera_nada():
    tactil = Tactil(960, 640)
    tactil.procesar(clic(pygame.MOUSEBUTTONDOWN, (480, 100)))
    assert tactil.obtener() == []


# ---- Envío al servidor ---------------------------------------------------------------------


class FuenteFalsa(FuenteEntrada):
    def __init__(self, origen, entradas=(), avisos=()):
        super().__init__()
        self.origen = origen
        self._pendientes = list(entradas)
        self._avisos = list(avisos)
        self.revisada = 0
        self.cerrada = False

    def revisar(self):
        self.revisada += 1

    def obtener_avisos(self):
        avisos, self._avisos = self._avisos, []
        return avisos

    def cerrar(self):
        self.cerrada = True


def test_controles_envian_el_mensaje_del_contrato_con_seq_creciente():
    enviados = []
    teclado = FuenteFalsa("teclado", [("arriba", "presionado"), ("arriba", "liberado")])
    serial = FuenteFalsa("hardware", [("accion", "presionado")])
    controles = ControlesJugador([teclado, serial], enviados.append)

    assert controles.actualizar() == 3
    assert enviados == [
        {"tipo": "entrada", "control": "arriba", "estado": "presionado", "origen": "teclado",
         "seq": 1},
        {"tipo": "entrada", "control": "arriba", "estado": "liberado", "origen": "teclado",
         "seq": 2},
        {"tipo": "entrada", "control": "accion", "estado": "presionado", "origen": "hardware",
         "seq": 3},
    ]  # fmt: skip
    assert controles.ultimo_origen == "hardware"


def test_controles_revisan_cada_fuente_una_vez_por_cuadro_y_sin_entradas_no_envian():
    enviados = []
    fuente = FuenteFalsa("teclado")
    controles = ControlesJugador([fuente], enviados.append)
    controles.actualizar()
    controles.actualizar()
    assert fuente.revisada == 2
    assert enviados == []


def test_controles_reenvian_los_avisos_del_dispositivo():
    aviso = {"tipo": "dispositivo", "estado": "conectado", "id": "CR-PAD-01"}
    enviados = []
    controles = ControlesJugador([FuenteFalsa("hardware", avisos=[aviso])], enviados.append)
    controles.actualizar()
    assert enviados == [aviso]


def test_controles_pasan_los_eventos_a_todas_las_fuentes_y_las_cierran():
    enviados = []
    teclado = Teclado()
    otra = FuenteFalsa("simulador")
    controles = ControlesJugador([teclado, otra], enviados.append)
    controles.procesar(abajo(pygame.K_d))
    controles.actualizar()
    assert enviados[0]["control"] == "derecha"
    assert enviados[0]["origen"] == "teclado"
    controles.cerrar()
    assert otra.cerrada


def test_mismo_mensaje_desde_teclado_y_desde_el_control_fisico():
    """Contrato: para el servidor no hay diferencia de fuente salvo el campo `origen`."""
    desde_teclado, desde_control = [], []
    con_teclado = ControlesJugador([Teclado()], desde_teclado.append)
    con_teclado.procesar(abajo(pygame.K_LEFT))
    con_teclado.actualizar()
    ControlesJugador(
        [FuenteFalsa("hardware", [("izquierda", "presionado")])], desde_control.append
    ).actualizar()

    def sin_origen(mensajes):
        return [{k: v for k, v in m.items() if k != "origen"} for m in mensajes]

    assert sin_origen(desde_teclado) == sin_origen(desde_control)
    assert desde_teclado[0]["origen"] == "teclado"
    assert desde_control[0]["origen"] == "hardware"


# ---- Fuentes según la plataforma -----------------------------------------------------------


def test_en_escritorio_sin_puerto_solo_teclado():
    fuentes = crear_fuentes(960, 640, puerto_control=None, en_navegador=False)
    assert [type(f) for f in fuentes] == [Teclado]


def test_en_escritorio_con_puerto_agrega_el_control_fisico():
    fuentes = crear_fuentes(960, 640, "socket://localhost:7777", en_navegador=False)
    assert [type(f) for f in fuentes] == [Teclado, EntradaSerial]
    assert fuentes[1].origen == "simulador"


@pytest.mark.parametrize("puerto", [None, "COM3"])
def test_en_el_navegador_teclado_y_tactil_sin_serial(puerto):
    fuentes = crear_fuentes(960, 640, puerto, en_navegador=True)
    assert [type(f) for f in fuentes] == [Teclado, Tactil]


def test_control_fisico_para_mostrar_su_estado():
    con = ControlesJugador(crear_fuentes(960, 640, "COM3", en_navegador=False), lambda _m: None)
    sin = ControlesJugador(crear_fuentes(960, 640, None, en_navegador=False), lambda _m: None)
    assert isinstance(con.control_fisico(), EntradaSerial)
    assert sin.control_fisico() is None
