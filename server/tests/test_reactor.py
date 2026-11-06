"""Extraer energía del reactor con el botón de acción (US-11): la mecánica y su uso en el motor."""

import asyncio
from dataclasses import dataclass

import pytest

from app.realtime.acciones import ResultadoAccion
from app.realtime.arena import RADIO_JUGADOR, Arena, Reactor
from app.realtime.eventos import ACCION_REALIZADA, ESTADO_ACTUALIZADO
from app.realtime.motor_partida import CICLO_S, MotorPartida
from app.realtime.reactor import (
    CAPACIDAD,
    ENERGIA_POR_EXTRACCION,
    ESPERA_ENTRE_EXTRACCIONES_S,
    GENERACION_POR_SEGUNDO,
    ExtraccionReactor,
)

REACTOR = Reactor(x=480, y=270, radio=40)
ALCANCE = REACTOR.radio + RADIO_JUGADOR  # 60 px: el jugador toca el reactor


@dataclass
class Jugador:
    jugador_id: int
    x: float
    y: float


def en_el_reactor(jugador_id=1):
    return Jugador(jugador_id, REACTOR.x, REACTOR.y)


def mecanica(**opciones):
    return ExtraccionReactor(REACTOR, RADIO_JUGADOR, **opciones)


class ObservadorFalso:
    def __init__(self):
        self.eventos = []

    async def al_evento(self, evento):
        self.eventos.append(evento)


def avanzar(motor, ticks):
    async def correr():
        for _ in range(ticks):
            await motor.tick()

    asyncio.run(correr())


def motor_con_jugador_en_el_reactor(**opciones):
    """Un motor cuya arena pone el primer punto de inicio encima del reactor."""
    arena = Arena(reactor=REACTOR, puntos_inicio=((REACTOR.x, REACTOR.y), (100, 100)))
    acciones = [ExtraccionReactor(REACTOR, RADIO_JUGADOR, **opciones)] if opciones else None
    motor = MotorPartida(1, arena, acciones)
    motor.agregar_jugador(1)
    return motor


def puntaje(motor, jugador_id=1):
    return next(j["puntaje"] for j in motor.estado()["jugadores"] if j["jugador_id"] == jugador_id)


#  la mecánica sola


def test_el_reactor_empieza_lleno():
    assert mecanica().a_dict() == {"energia": CAPACIDAD, "capacidad": CAPACIDAD}


def test_extraer_tocando_el_reactor_da_energia_y_la_descuenta():
    reactor = mecanica()

    resultado = reactor.intentar(en_el_reactor(), tiempo=0.0)

    assert resultado == ResultadoAccion("reactor", ENERGIA_POR_EXTRACCION)
    assert reactor.energia == CAPACIDAD - ENERGIA_POR_EXTRACCION


@pytest.mark.parametrize("distancia, extrae", [(ALCANCE, True), (ALCANCE + 1, False)])
def test_solo_extrae_quien_esta_tocando_el_reactor(distancia, extrae):
    jugador = Jugador(1, REACTOR.x + distancia, REACTOR.y)

    resultado = mecanica().intentar(jugador, tiempo=0.0)

    assert (resultado is not None) == extrae


def test_hay_que_esperar_entre_una_extraccion_y_la_siguiente():
    reactor = mecanica()
    jugador = en_el_reactor()

    assert reactor.intentar(jugador, tiempo=0.0) is not None
    assert reactor.intentar(jugador, tiempo=ESPERA_ENTRE_EXTRACCIONES_S - 0.01) is None
    assert reactor.intentar(jugador, tiempo=ESPERA_ENTRE_EXTRACCIONES_S) is not None


def test_la_espera_es_de_cada_jugador():
    reactor = mecanica()

    assert reactor.intentar(en_el_reactor(1), tiempo=0.0) is not None
    assert reactor.intentar(en_el_reactor(2), tiempo=0.0) is not None


def test_con_poca_energia_se_extrae_lo_que_queda_y_vacio_no_da_nada():
    reactor = mecanica(capacidad=15, generacion_por_segundo=0)

    primera = reactor.intentar(en_el_reactor(1), tiempo=0.0)
    segunda = reactor.intentar(en_el_reactor(2), tiempo=0.0)
    tercera = reactor.intentar(en_el_reactor(3), tiempo=0.0)

    assert primera.puntos == 10
    assert segunda.puntos == 5
    assert tercera is None
    assert reactor.energia == 0


def test_el_reactor_se_recarga_con_el_tiempo_hasta_su_capacidad():
    reactor = mecanica(capacidad=20)
    reactor.intentar(en_el_reactor(1), tiempo=0.0)  # queda en 10
    reactor.intentar(en_el_reactor(2), tiempo=0.0)  # queda en 0

    reactor.actualizar(1.0)
    assert reactor.energia == GENERACION_POR_SEGUNDO

    reactor.actualizar(60.0)
    assert reactor.energia == 20


def test_actualizar_avisa_solo_cuando_cambia_la_energia_entera():
    reactor = mecanica(generacion_por_segundo=10)
    reactor.intentar(en_el_reactor(), tiempo=0.0)

    assert reactor.actualizar(0.05) is False  # +0.5: todavía no llega a una unidad
    assert reactor.actualizar(0.05) is True  # +1
    assert mecanica().actualizar(1.0) is False  # lleno: no cambia


#  en el motor de partida


def test_presionar_la_accion_en_el_reactor_suma_puntos():
    motor = motor_con_jugador_en_el_reactor()

    motor.aplicar_entrada(1, "accion", "presionado")

    assert puntaje(motor) == ENERGIA_POR_EXTRACCION
    assert motor.estado()["reactor"]["energia"] == CAPACIDAD - ENERGIA_POR_EXTRACCION


def test_soltar_la_accion_no_extrae():
    motor = motor_con_jugador_en_el_reactor()

    motor.aplicar_entrada(1, "accion", "liberado")

    assert puntaje(motor) == 0


def test_lejos_del_reactor_la_accion_no_da_puntos():
    motor = motor_con_jugador_en_el_reactor()
    motor.agregar_jugador(2)  # aparece en (100, 100), lejos del reactor

    motor.aplicar_entrada(2, "accion", "presionado")

    assert puntaje(motor, 2) == 0


def test_presionar_muy_seguido_no_da_mas_puntos():
    motor = motor_con_jugador_en_el_reactor()

    for _ in range(5):
        motor.aplicar_entrada(1, "accion", "presionado")
        motor.aplicar_entrada(1, "accion", "liberado")

    assert puntaje(motor) == ENERGIA_POR_EXTRACCION


def test_la_espera_corre_con_los_ticks_del_motor():
    motor = motor_con_jugador_en_el_reactor()
    ticks_de_espera = round(ESPERA_ENTRE_EXTRACCIONES_S / CICLO_S)

    motor.aplicar_entrada(1, "accion", "presionado")
    avanzar(motor, ticks_de_espera)
    motor.aplicar_entrada(1, "accion", "presionado")

    assert puntaje(motor) == 2 * ENERGIA_POR_EXTRACCION


def test_la_extraccion_avisa_la_accion_y_luego_el_estado():
    motor = motor_con_jugador_en_el_reactor()
    observador = ObservadorFalso()
    motor.suscribir(observador)
    avanzar(motor, 1)
    observador.eventos.clear()

    motor.aplicar_entrada(1, "accion", "presionado")
    avanzar(motor, 1)

    assert [e.tipo for e in observador.eventos] == [ACCION_REALIZADA, ESTADO_ACTUALIZADO]
    assert observador.eventos[0].datos == {
        "jugador_id": 1,
        "accion": "reactor",
        "puntos": ENERGIA_POR_EXTRACCION,
    }


def test_mientras_el_reactor_se_recarga_los_jugadores_lo_ven():
    motor = motor_con_jugador_en_el_reactor()
    observador = ObservadorFalso()
    motor.suscribir(observador)
    motor.aplicar_entrada(1, "accion", "presionado")
    avanzar(motor, 1)
    observador.eventos.clear()

    avanzar(motor, round(1 / CICLO_S))  # un segundo

    energias = [e.datos["reactor"]["energia"] for e in observador.eventos]
    assert energias == sorted(energias) and energias[-1] > CAPACIDAD - ENERGIA_POR_EXTRACCION


def test_el_motor_prueba_las_acciones_en_orden_y_usa_la_primera_que_aplica():
    class Terminal:
        clave = "terminal"

        def actualizar(self, dt):
            return False

        def intentar(self, jugador, tiempo):
            return ResultadoAccion("terminal", 3)

        def a_dict(self):
            return {}

    reactor = ExtraccionReactor(REACTOR, RADIO_JUGADOR)
    arena = Arena(reactor=REACTOR, puntos_inicio=((REACTOR.x, REACTOR.y),))
    motor = MotorPartida(1, arena, [Terminal(), reactor])
    motor.agregar_jugador(1)

    motor.aplicar_entrada(1, "accion", "presionado")

    assert puntaje(motor) == 3
    assert reactor.energia == CAPACIDAD  # el reactor no se tocó
    assert set(motor.estado()) >= {"terminal", "reactor"}
