"""Pruebas del motor de partida: movimiento, límites del mapa y observadores (sin WebSocket)."""

import asyncio
import math

import pytest

from app.realtime import motor_partida
from app.realtime.eventos import ESTADO_ACTUALIZADO
from app.realtime.motor_partida import (
    ALTO_ARENA,
    ANCHO_ARENA,
    PUNTOS_DE_INICIO,
    RADIO_JUGADOR,
    VELOCIDAD,
    MotorPartida,
)

UN_SEGUNDO = 20  # ticks de 50 ms


class ObservadorFalso:
    def __init__(self):
        self.eventos = []

    async def al_evento(self, evento):
        self.eventos.append(evento)


class ObservadorQueFalla:
    async def al_evento(self, evento):
        raise RuntimeError("falló a propósito")


def avanzar(motor, ticks):
    async def correr():
        for _ in range(ticks):
            await motor.tick()

    asyncio.run(correr())


def posicion(motor, jugador_id):
    jugador = next(j for j in motor.estado()["jugadores"] if j["jugador_id"] == jugador_id)
    return jugador["x"], jugador["y"]


def motor_con_un_jugador():
    motor = MotorPartida(partida_id=1)
    motor.agregar_jugador(7)
    return motor


#  movimiento 


def test_los_jugadores_nuevos_aparecen_en_sus_puntos_de_inicio():
    motor = MotorPartida(1)
    motor.agregar_jugador(10)
    motor.agregar_jugador(11)

    assert posicion(motor, 10) == PUNTOS_DE_INICIO[0]
    assert posicion(motor, 11) == PUNTOS_DE_INICIO[1]


def test_una_direccion_presionada_mueve_al_jugador_a_la_velocidad_del_motor():
    motor = motor_con_un_jugador()
    x0, y0 = posicion(motor, 7)
    motor.aplicar_entrada(7, "derecha", "presionado")

    avanzar(motor, UN_SEGUNDO)

    assert posicion(motor, 7) == (x0 + VELOCIDAD, y0)


@pytest.mark.parametrize(
    ("control", "dx", "dy"),
    [("arriba", 0, -1), ("abajo", 0, 1), ("izquierda", -1, 0), ("derecha", 1, 0)],
)
def test_cada_direccion_mueve_hacia_su_lado(control, dx, dy):
    motor = motor_con_un_jugador()
    x0, y0 = posicion(motor, 7)
    motor.aplicar_entrada(7, control, "presionado")

    avanzar(motor, UN_SEGUNDO // 2)  # medio segundo: cabe en las cuatro direcciones

    assert posicion(motor, 7) == (x0 + dx * VELOCIDAD / 2, y0 + dy * VELOCIDAD / 2)


def test_soltar_el_control_detiene_al_jugador():
    motor = motor_con_un_jugador()
    motor.aplicar_entrada(7, "derecha", "presionado")
    avanzar(motor, 5)
    motor.aplicar_entrada(7, "derecha", "liberado")
    detenido = posicion(motor, 7)

    avanzar(motor, UN_SEGUNDO)

    assert posicion(motor, 7) == detenido


def test_direcciones_opuestas_se_cancelan():
    motor = motor_con_un_jugador()
    inicio = posicion(motor, 7)
    motor.aplicar_entrada(7, "izquierda", "presionado")
    motor.aplicar_entrada(7, "derecha", "presionado")

    avanzar(motor, UN_SEGUNDO)

    assert posicion(motor, 7) == inicio


def test_en_diagonal_avanza_la_misma_distancia_que_en_recta():
    motor = motor_con_un_jugador()
    x0, y0 = posicion(motor, 7)
    motor.aplicar_entrada(7, "derecha", "presionado")
    motor.aplicar_entrada(7, "abajo", "presionado")

    avanzar(motor, UN_SEGUNDO)

    x, y = posicion(motor, 7)
    assert x > x0 and y > y0
    assert math.hypot(x - x0, y - y0) == pytest.approx(VELOCIDAD, abs=1.5)


def test_la_accion_no_mueve_al_jugador_en_este_sprint():
    motor = motor_con_un_jugador()
    inicio = posicion(motor, 7)
    motor.aplicar_entrada(7, "accion", "presionado")

    avanzar(motor, UN_SEGUNDO)

    assert posicion(motor, 7) == inicio


def test_las_entradas_de_un_jugador_que_no_esta_se_ignoran():
    motor = motor_con_un_jugador()
    motor.aplicar_entrada(999, "derecha", "presionado")  # no debe fallar

    assert motor.controles_presionados(999) == frozenset()


#  colisión con los límites del mapa 


@pytest.mark.parametrize(
    ("control", "eje", "limite"),
    [
        ("izquierda", 0, RADIO_JUGADOR),
        ("derecha", 0, ANCHO_ARENA - RADIO_JUGADOR),
        ("arriba", 1, RADIO_JUGADOR),
        ("abajo", 1, ALTO_ARENA - RADIO_JUGADOR),
    ],
)
def test_el_jugador_no_atraviesa_los_limites_de_la_arena(control, eje, limite):
    motor = motor_con_un_jugador()
    motor.aplicar_entrada(7, control, "presionado")

    avanzar(motor, 20 * UN_SEGUNDO)  # mucho más de lo necesario para llegar a la pared

    assert posicion(motor, 7)[eje] == limite


def test_contra_la_pared_se_desliza_por_el_otro_eje():
    motor = motor_con_un_jugador()
    motor.aplicar_entrada(7, "izquierda", "presionado")
    avanzar(motor, 20 * UN_SEGUNDO)  # pegado a la pared izquierda
    _, y0 = posicion(motor, 7)
    motor.aplicar_entrada(7, "abajo", "presionado")  # izquierda + abajo

    avanzar(motor, UN_SEGUNDO)

    x, y = posicion(motor, 7)
    assert x == RADIO_JUGADOR and y > y0


# jugadores que entran y salen 


def test_quien_vuelve_a_entrar_conserva_su_posicion_y_suelta_los_controles():
    motor = motor_con_un_jugador()
    motor.aplicar_entrada(7, "derecha", "presionado")
    avanzar(motor, UN_SEGUNDO)
    donde_estaba = posicion(motor, 7)

    motor.agregar_jugador(7)  # reconexión

    assert posicion(motor, 7) == donde_estaba
    assert motor.controles_presionados(7) == frozenset()


def test_quitar_a_un_jugador_lo_saca_del_estado():
    motor = MotorPartida(1)
    motor.agregar_jugador(1)
    motor.agregar_jugador(2)

    motor.quitar_jugador(1)

    assert [j["jugador_id"] for j in motor.estado()["jugadores"]] == [2]
    assert motor.hay_jugadores
    motor.quitar_jugador(2)
    assert not motor.hay_jugadores


# observadores


def test_avisa_el_estado_cuando_algo_cambia():
    motor = motor_con_un_jugador()
    observador = ObservadorFalso()
    motor.suscribir(observador)

    avanzar(motor, 1)

    (evento,) = observador.eventos
    assert evento.tipo == ESTADO_ACTUALIZADO and evento.partida_id == 1
    assert evento.datos["jugadores"] == [{"jugador_id": 7, "x": 240, "y": 135}]


def test_no_avisa_si_nada_cambio():
    motor = motor_con_un_jugador()
    observador = ObservadorFalso()
    motor.suscribir(observador)

    avanzar(motor, 10)  # el único aviso es por el jugador que entró

    assert len(observador.eventos) == 1


def test_avisa_en_cada_tick_mientras_el_jugador_se_mueve():
    motor = motor_con_un_jugador()
    observador = ObservadorFalso()
    motor.suscribir(observador)
    motor.aplicar_entrada(7, "derecha", "presionado")

    avanzar(motor, 10)

    assert len(observador.eventos) == 10


def test_en_la_pared_deja_de_avisar():
    motor = motor_con_un_jugador()
    observador = ObservadorFalso()
    motor.suscribir(observador)
    motor.aplicar_entrada(7, "izquierda", "presionado")
    avanzar(motor, 20 * UN_SEGUNDO)
    avisos = len(observador.eventos)

    avanzar(motor, 10)  # sigue presionado, pero ya no puede avanzar

    assert len(observador.eventos) == avisos


def test_un_observador_que_falla_no_detiene_a_los_demas():
    motor = motor_con_un_jugador()
    bueno = ObservadorFalso()
    motor.suscribir(ObservadorQueFalla())
    motor.suscribir(bueno)

    avanzar(motor, 1)

    assert len(bueno.eventos) == 1


def test_desuscribir_deja_de_avisar():
    motor = motor_con_un_jugador()
    observador = ObservadorFalso()
    motor.suscribir(observador)
    motor.desuscribir(observador)

    avanzar(motor, 1)

    assert observador.eventos == []


def test_el_estado_trae_la_arena_y_los_jugadores_ordenados():
    motor = MotorPartida(1)
    motor.agregar_jugador(9)
    motor.agregar_jugador(3)

    estado = motor.estado()

    assert [j["jugador_id"] for j in estado["jugadores"]] == [3, 9]
    assert estado["arena"] == {
        "ancho": ANCHO_ARENA,
        "alto": ALTO_ARENA,
        "radio": RADIO_JUGADOR,
    }


# ciclo


def test_el_ciclo_ejecuta_ticks_solo_hasta_que_se_detiene(monkeypatch):
    monkeypatch.setattr(motor_partida, "CICLO_S", 0.01)
    motor = motor_con_un_jugador()
    observador = ObservadorFalso()
    motor.suscribir(observador)
    motor.aplicar_entrada(7, "derecha", "presionado")

    async def escenario():
        motor.iniciar()
        motor.iniciar()  # no debe arrancar un segundo ciclo
        await asyncio.sleep(0.3)
        await motor.detener()
        avisos = len(observador.eventos)
        await asyncio.sleep(0.1)
        await motor.detener()  # detener dos veces no debe fallar
        return avisos, len(observador.eventos)

    al_detener, despues = asyncio.run(escenario())
    assert al_detener >= 5
    assert despues == al_detener