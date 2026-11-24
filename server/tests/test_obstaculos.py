"""Pruebas de los obstáculos (US-14): barrera, trampa, puerta y barrera móvil. Sin red ni base
de datos."""

import asyncio

import pytest

from app.realtime.arena import Arena, Obstaculo, Reactor
from app.realtime.eventos import ESTADO_ACTUALIZADO
from app.realtime.motor_partida import CICLO_S, VELOCIDAD, MotorPartida
from app.realtime.obstaculos import (
    BARRERA_MOVIL,
    FACTOR_TRAMPA,
    PUERTA_ABIERTA_S,
    PUERTA_CERRADA_S,
    VELOCIDAD_BARRERA_MOVIL,
    GestorObstaculos,
    posicion_en,
    sacar,
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


def barrera_movil(x=100, y=0, destino_x=200, destino_y=0, ancho=20, alto=60):
    return Obstaculo(x, y, ancho, alto, BARRERA_MOVIL, destino_x, destino_y)


class TestBarreraMovil:
    def test_empieza_en_su_punto_inicial(self):
        movil = barrera_movil()
        assert posicion_en(movil, 0, 30) == movil

    def test_avanza_hacia_el_destino_a_su_velocidad(self):
        movil = posicion_en(barrera_movil(), 2.0, 30)  # 2 s a 30 px/s: 60 px
        assert (movil.x, movil.y) == pytest.approx((160, 0))

    def test_en_el_destino_da_la_vuelta(self):
        tiempo_de_ida = 100 / 30
        en_destino = posicion_en(barrera_movil(), tiempo_de_ida, 30)
        assert (en_destino.x, en_destino.y) == pytest.approx((200, 0))
        de_vuelta = posicion_en(barrera_movil(), tiempo_de_ida + 1.0, 30)
        assert (de_vuelta.x, de_vuelta.y) == pytest.approx((170, 0))

    def test_completa_el_ciclo_y_vuelve_al_inicio(self):
        ciclo = 2 * 100 / 30
        movil = posicion_en(barrera_movil(), ciclo, 30)
        assert (movil.x, movil.y) == pytest.approx((100, 0))

    def test_nunca_sale_del_recorrido(self):
        for decima in range(0, 1000):
            movil = posicion_en(barrera_movil(), decima / 10, 30)
            assert 100 - 1e-6 <= movil.x <= 200 + 1e-6

    def test_puede_moverse_en_diagonal(self):
        movil = posicion_en(barrera_movil(0, 0, 30, 40), 1.0, 25)  # recorrido de 50 px
        assert (movil.x, movil.y) == pytest.approx((15, 20))

    def test_sin_destino_o_sin_recorrido_se_queda_quieta(self):
        sin_destino = Obstaculo(10, 10, 20, 20, BARRERA_MOVIL)
        sin_recorrido = barrera_movil(10, 10, 10, 10)
        assert posicion_en(sin_destino, 5, 30) == sin_destino
        assert posicion_en(sin_recorrido, 5, 30) == sin_recorrido

    def test_los_otros_obstaculos_no_se_mueven(self):
        for tipo in ("barrera", "trampa", "puerta"):
            fijo = Obstaculo(10, 10, 20, 20, tipo, 100, 100)
            assert posicion_en(fijo, 5, 30) == fijo

    def test_bloquea_el_paso_donde_esta_ahora(self):
        gestor = GestorObstaculos([barrera_movil(100, 0, 200, 0, alto=200)], RADIO)
        assert gestor.mover(60, 100, 90, 100) == (60, 100)  # la barrera está en x = 100..120
        gestor.actualizar(100 / VELOCIDAD_BARRERA_MOVIL)  # llega a x = 200..220
        assert gestor.mover(60, 100, 90, 100) == (90, 100)  # ya no está en el camino
        assert gestor.mover(160, 100, 190, 100) == (160, 100)  # ahora bloquea más adelante

    def test_actualizar_avisa_que_hubo_cambio_en_cada_ciclo(self):
        gestor = GestorObstaculos([barrera_movil()], RADIO)
        assert gestor.actualizar(CICLO_S) is True
        assert gestor.actualizar(CICLO_S) is True

    def test_el_estado_trae_la_posicion_actual(self):
        gestor = GestorObstaculos([barrera_movil()], RADIO)
        gestor.actualizar(2.0)
        dato = gestor.a_dicts()[0]
        assert dato["tipo"] == BARRERA_MOVIL
        assert dato["x"] == 160

    def test_el_motor_la_mueve_y_avisa_a_los_clientes(self):
        motor = motor_con([barrera_movil(100, 0, 200, 0, alto=200)])
        observador = ObservadorFalso()
        motor.suscribir(observador)
        inicio = motor.estado()["arena"]["obstaculos"][0]["x"]
        avanzar(motor, ticks_para(1.0))
        estados = [e.datos for e in observador.eventos if e.tipo == ESTADO_ACTUALIZADO]
        assert estados
        assert estados[-1]["arena"]["obstaculos"][0]["x"] > inicio

    def test_el_jugador_choca_con_ella_en_el_motor(self):
        # Barrera quieta frente al jugador (50, 100): no lo deja pasar
        motor = motor_con([barrera_movil(100, 0, 100, 1, alto=200)])
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(2.0))
        assert posicion(motor)[0] < 100 - RADIO + 1


class TestEmpujeDeLaBarreraMovil:
    """La barrera móvil nunca atraviesa al jugador: lo empuja o lo bloquea."""

    def test_sacar_deja_al_circulo_libre_por_el_lado_mas_cercano(self):
        barrera = Obstaculo(100, 0, 20, 200, "barrera")
        x, y = sacar(110, 100, RADIO, barrera)  # el centro quedó adentro, más cerca de la izquierda
        assert x == pytest.approx(100 - RADIO)
        assert not toca(x, y, RADIO - 0.001, barrera)

    def test_sacar_no_mueve_a_quien_no_toca(self):
        barrera = Obstaculo(100, 0, 20, 200, "barrera")
        assert sacar(10, 100, RADIO, barrera) == (10, 100)

    def test_sacar_desde_una_esquina_se_aleja_en_diagonal(self):
        barrera = Obstaculo(100, 100, 20, 20, "barrera")
        x, y = sacar(95, 95, RADIO, barrera)
        assert x < 95 and y < 95
        assert not toca(x, y, RADIO - 0.001, barrera)

    def test_empuja_a_un_jugador_quieto(self):
        gestor = GestorObstaculos([barrera_movil(100, 0, 200, 0, alto=200)], RADIO)
        x = 150.0  # la barrera sube desde x = 100 hasta pasar por donde está el jugador
        for _ in range(ticks_para(5.0)):
            gestor.actualizar(CICLO_S)
            x, _ = gestor.empujar(x, 100)
            assert not any(
                toca(x, 100, RADIO, o) for o in gestor._actuales if o.tipo == BARRERA_MOVIL
            )
        assert x > 150  # lo fue empujando hacia adelante

    def test_no_toca_a_los_que_ya_estan_libres(self):
        gestor = GestorObstaculos([barrera_movil(100, 0, 200, 0, alto=200)], RADIO)
        assert gestor.empujar(10, 100) == (10, 100)

    def test_las_puertas_y_barreras_fijas_no_empujan(self):
        fijas = [Obstaculo(90, 0, 40, 200, "barrera"), Obstaculo(90, 0, 40, 200, "puerta")]
        gestor = GestorObstaculos(fijas, RADIO)
        assert gestor.empujar(110, 100) == (110, 100)

    def test_en_el_motor_la_barrera_empuja_al_jugador_quieto(self):
        # el jugador espera en x = 150 y la barrera viene desde x = 100 hacia 400
        motor = motor_con([barrera_movil(100, 0, 380, 0, alto=200)], inicio=(150, 100))
        for _ in range(ticks_para(6.0)):
            avanzar(motor, 1)
            x, y = posicion(motor)
            barrera = motor.estado()["arena"]["obstaculos"][0]
            assert not toca(
                x,
                y,
                RADIO,
                Obstaculo(**{k: barrera[k] for k in ("x", "y", "ancho", "alto")}, tipo="barrera"),
            )
        assert posicion(motor)[0] > 150

    def test_en_el_motor_nunca_la_atraviesa_si_el_jugador_camina_hacia_ella(self):
        motor = motor_con([barrera_movil(300, 0, 100, 0, alto=200)], inicio=(50, 100))
        motor.aplicar_entrada(1, "derecha", "presionado")  # ella viene hacia él y él hacia ella
        for _ in range(ticks_para(8.0)):
            avanzar(motor, 1)
            x, _ = posicion(motor)
            barrera = motor.estado()["arena"]["obstaculos"][0]
            assert x + RADIO <= barrera["x"] + 0.02  # siempre del lado izquierdo de la barrera

    def test_el_jugador_puede_moverse_mientras_lo_empujan(self):
        motor = motor_con([barrera_movil(100, 0, 380, 0, alto=200)], inicio=(150, 100))
        motor.aplicar_entrada(1, "abajo", "presionado")
        avanzar(motor, ticks_para(1.0))
        assert posicion(motor)[1] > 100  # camina libremente en el otro eje