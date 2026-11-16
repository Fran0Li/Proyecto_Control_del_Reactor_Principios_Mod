"""Pruebas de los obstáculos (US-14): barrera, trampa y puerta. Sin red ni base de datos."""

import asyncio

import pytest

from app.realtime.arena import Arena, Obstaculo, Reactor
from app.realtime.eventos import ESTADO_ACTUALIZADO
from app.realtime.motor_partida import CICLO_S, VELOCIDAD, MotorPartida
from app.realtime.obstaculos import (
    FACTOR_TRAMPA,
    PUERTA_ABIERTA_S,
    PUERTA_CERRADA_S,
    GestorObstaculos,
    toca,
)

RADIO = 20


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


def motor_con(obstaculos, inicio=(50, 100)):
    arena = Arena(
        reactor=Reactor(400, 400, 10),
        ancho=400,
        alto=200,
        puntos_inicio=(inicio,),
        obstaculos=obstaculos,
    )
    motor = MotorPartida(1, arena=arena)
    motor.agregar_jugador(1)
    return motor


def posicion(motor):
    jugador = motor.estado()["jugadores"][0]
    return jugador["x"], jugador["y"]


def ticks_para(segundos):
    return round(segundos / CICLO_S)


class TestToca:
    def test_dentro_del_rectangulo(self):
        assert toca(150, 100, RADIO, Obstaculo(100, 50, 100, 100))

    def test_lejos_no_toca(self):
        assert not toca(10, 10, RADIO, Obstaculo(100, 50, 100, 100))

    def test_rozar_el_borde_no_cuenta(self):
        assert not toca(80, 100, RADIO, Obstaculo(100, 50, 100, 100))

    def test_meterse_un_poco_si_cuenta(self):
        assert toca(81, 100, RADIO, Obstaculo(100, 50, 100, 100))

    def test_cerca_de_una_esquina_usa_la_distancia_real(self):
        esquina = Obstaculo(100, 100, 50, 50)
        assert not toca(85, 85, RADIO, esquina)  # a unos 21 px de la esquina
        assert toca(90, 90, RADIO, esquina)


class TestBarrera:
    def test_bloquea_el_paso(self):
        motor = motor_con([Obstaculo(150, 0, 20, 200, "barrera")])
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(3))
        x, y = posicion(motor)
        assert x <= 150 - RADIO
        assert y == 100

    def test_no_se_mete_dentro_de_la_barrera(self):
        motor = motor_con([Obstaculo(150, 0, 20, 200, "barrera")])
        motor.aplicar_entrada(1, "derecha", "presionado")
        for _ in range(ticks_para(3)):
            avanzar(motor, 1)
            assert posicion(motor)[0] <= 150 - RADIO + 1  # +1 por el redondeo del estado

    def test_se_desliza_por_el_lado_libre_en_diagonal(self):
        motor = motor_con([Obstaculo(150, 0, 20, 200, "barrera")])
        motor.aplicar_entrada(1, "derecha", "presionado")
        motor.aplicar_entrada(1, "abajo", "presionado")
        avanzar(motor, ticks_para(0.8))
        x, y = posicion(motor)
        assert x <= 150 - RADIO + 1
        assert y > 100  # sigue bajando pegado a la barrera

    def test_puede_rodear_la_barrera(self):
        motor = motor_con([Obstaculo(150, 0, 20, 120, "barrera")], inicio=(50, 150))
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(2))
        assert posicion(motor)[0] > 170 + RADIO

    def test_en_el_estado_se_ve_como_barrera(self):
        motor = motor_con([Obstaculo(150, 0, 20, 200, "barrera")])
        obstaculo = motor.estado()["arena"]["obstaculos"][0]
        assert obstaculo["tipo"] == "barrera"
        assert "abierta" not in obstaculo


class TestTrampa:
    def test_no_bloquea_el_paso(self):
        motor = motor_con([Obstaculo(150, 0, 60, 200, "trampa")])
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(3))
        assert posicion(motor)[0] > 210 + RADIO

    def test_frena_al_jugador(self):
        libre = motor_con([])
        trampa = motor_con([Obstaculo(0, 0, 400, 200, "trampa")])
        for motor in (libre, trampa):
            motor.aplicar_entrada(1, "derecha", "presionado")
            avanzar(motor, ticks_para(1))
        recorrido_libre = posicion(libre)[0] - 50
        recorrido_trampa = posicion(trampa)[0] - 50
        assert recorrido_trampa == pytest.approx(recorrido_libre * FACTOR_TRAMPA, abs=2)

    def test_al_salir_de_la_trampa_recupera_la_velocidad(self):
        motor = motor_con([Obstaculo(0, 0, 100, 200, "trampa")])
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(2))
        x_antes = posicion(motor)[0]
        avanzar(motor, ticks_para(1))
        assert posicion(motor)[0] - x_antes == pytest.approx(VELOCIDAD, abs=2)

    def test_factor_de_velocidad(self):
        gestor = GestorObstaculos([Obstaculo(100, 100, 50, 50, "trampa")], RADIO)
        assert gestor.factor_velocidad(125, 125) == FACTOR_TRAMPA
        assert gestor.factor_velocidad(10, 10) == 1.0


class TestPuerta:
    def test_empieza_cerrada_y_bloquea(self):
        motor = motor_con([Obstaculo(150, 0, 20, 200, "puerta")])
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(2))
        assert posicion(motor)[0] <= 150 - RADIO + 1

    def test_abierta_deja_pasar(self):
        motor = motor_con([Obstaculo(150, 0, 20, 200, "puerta")])
        avanzar(motor, ticks_para(PUERTA_CERRADA_S) + 1)  # ya se abrió
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(2))
        assert posicion(motor)[0] > 170 + RADIO

    def test_el_estado_dice_si_esta_abierta(self):
        motor = motor_con([Obstaculo(150, 0, 20, 200, "puerta")])
        assert motor.estado()["arena"]["obstaculos"][0]["abierta"] is False
        avanzar(motor, ticks_para(PUERTA_CERRADA_S) + 1)
        assert motor.estado()["arena"]["obstaculos"][0]["abierta"] is True

    def test_se_cierra_otra_vez(self):
        gestor = GestorObstaculos([Obstaculo(0, 0, 10, 10, "puerta")], RADIO)
        gestor.actualizar(PUERTA_CERRADA_S + 0.1)
        assert gestor.puertas_abiertas
        gestor.actualizar(PUERTA_ABIERTA_S)
        assert not gestor.puertas_abiertas

    def test_actualizar_avisa_solo_cuando_cambia(self):
        gestor = GestorObstaculos([Obstaculo(0, 0, 10, 10, "puerta")], RADIO)
        assert gestor.actualizar(1.0) is False
        assert gestor.actualizar(PUERTA_CERRADA_S) is True  # cruzó el límite
        assert gestor.actualizar(0.5) is False

    def test_si_se_cierra_encima_el_jugador_puede_salir(self):
        gestor = GestorObstaculos([Obstaculo(100, 0, 40, 200, "puerta")], RADIO)
        assert gestor.mover(120, 100, 121, 100) == (121, 100)  # adentro: se deja mover

    def test_el_cambio_de_puerta_se_notifica_a_los_clientes(self):
        motor = motor_con([Obstaculo(150, 0, 20, 200, "puerta")])
        observador = ObservadorFalso()
        motor.suscribir(observador)
        avanzar(motor, ticks_para(PUERTA_CERRADA_S) + 2)
        estados = [e.datos for e in observador.eventos if e.tipo == ESTADO_ACTUALIZADO]
        assert estados, "tendría que haber avisado el cambio de la puerta"
        assert estados[-1]["arena"]["obstaculos"][0]["abierta"] is True


class TestSinObstaculos:
    def test_la_arena_basica_no_cambia(self):
        motor = MotorPartida(1)
        motor.agregar_jugador(1)
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, 10)
        assert posicion(motor)[0] == pytest.approx(240 + VELOCIDAD * 10 * CICLO_S, abs=1)
        assert motor.estado()["arena"]["obstaculos"] == []