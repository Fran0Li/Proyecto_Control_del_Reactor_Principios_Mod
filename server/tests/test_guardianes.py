"""Pruebas de los guardianes (US-15): estrategias de movimiento y penalización en el motor."""

import asyncio
from types import SimpleNamespace

import pytest

from app.realtime.arena import Arena, Reactor
from app.realtime.estados_jugador import ATURDIDO, DURACION_ATURDIDO_S, ESCUDADO, NORMAL
from app.realtime.eventos import ESTADO_ACTUALIZADO, JUGADOR_PENALIZADO
from app.realtime.guardianes import Guardian, Patrulla, Perseguir, RutaFija
from app.realtime.motor_partida import CICLO_S, PENALIZACION_PUNTOS, MotorPartida

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


def ticks_para(segundos):
    return round(segundos / CICLO_S)


def jugador_en(x, y):
    return SimpleNamespace(x=x, y=y)


def mover_guardian(guardian, segundos, objetivos=()):
    for _ in range(ticks_para(segundos)):
        guardian.mover(CICLO_S, list(objetivos))


def motor_con(guardianes, inicio=(100, 100)):
    arena = Arena(
        reactor=Reactor(900, 500, 10),
        ancho=1000,
        alto=600,
        puntos_inicio=(inicio,),
    )
    motor = MotorPartida(1, arena=arena, guardianes=guardianes)
    motor.agregar_jugador(1)
    return motor


def estado_del_jugador(motor):
    return motor.estado()["jugadores"][0]


class TestRutaFija:
    def test_avanza_hacia_el_primer_punto(self):
        guardian = Guardian(1, 0, 0, RutaFija([(100, 0)], velocidad=100))
        mover_guardian(guardian, 0.5)
        assert guardian.x == pytest.approx(50)
        assert guardian.y == pytest.approx(0)

    def test_no_se_pasa_del_punto(self):
        guardian = Guardian(1, 0, 0, RutaFija([(100, 0)], velocidad=100))
        guardian.mover(10.0, [])
        assert (guardian.x, guardian.y) == (100, 0)

    def test_recorre_el_circuito_y_vuelve_al_primer_punto(self):
        ruta = RutaFija([(100, 0), (100, 100), (0, 100)], velocidad=100)
        guardian = Guardian(1, 0, 0, ruta)
        visitados = []
        for _ in range(ticks_para(5)):
            guardian.mover(CICLO_S, [])
            visitados.append((round(guardian.x), round(guardian.y)))
        assert (100, 0) in visitados
        assert (100, 100) in visitados
        assert (0, 100) in visitados
        assert visitados[-1][0] > 0 or visitados[-1][1] != 100  # ya dio la vuelta

    def test_sin_puntos_falla(self):
        with pytest.raises(ValueError):
            RutaFija([])

    def test_mover_dice_si_se_movio(self):
        guardian = Guardian(1, 0, 0, RutaFija([(100, 0)], velocidad=100))
        assert guardian.mover(0.1, []) is True
        guardian.x, guardian.y = 100.0, 0.0
        assert guardian.mover(0.1, []) is False  # ya está en el punto


class TestPatrulla:
    def test_va_y_vuelve_sin_saltarse_el_camino(self):
        guardian = Guardian(1, 0, 0, Patrulla([(0, 0), (100, 0)], velocidad=100))
        xs = []
        for _ in range(ticks_para(2.5)):
            guardian.mover(CICLO_S, [])
            xs.append(guardian.x)
        assert max(xs) == pytest.approx(100)
        assert xs[-1] < 100  # ya se devolvió

    def test_con_tres_puntos_hace_ida_y_vuelta(self):
        guardian = Guardian(1, 0, 0, Patrulla([(0, 0), (100, 0), (100, 100)], velocidad=100))
        recorrido = []
        for _ in range(ticks_para(5)):
            guardian.mover(CICLO_S, [])
            recorrido.append((round(guardian.x), round(guardian.y)))
        assert (100, 100) in recorrido  # llegó al último
        assert recorrido[-1] != (100, 100)  # y se devolvió
        assert (100, 0) in recorrido[recorrido.index((100, 100)) :]  # pasa otra vez por el medio

    def test_un_solo_punto_no_falla(self):
        guardian = Guardian(1, 0, 0, Patrulla([(50, 0)], velocidad=100))
        mover_guardian(guardian, 2)
        assert (guardian.x, guardian.y) == (50, 0)

    def test_sin_puntos_falla(self):
        with pytest.raises(ValueError):
            Patrulla([])


class TestPerseguir:
    def test_va_hacia_el_jugador_que_esta_cerca(self):
        guardian = Guardian(1, 0, 0, Perseguir(radio_deteccion=200, velocidad=100))
        mover_guardian(guardian, 0.5, [jugador_en(100, 0)])
        assert guardian.x == pytest.approx(50)

    def test_ignora_al_jugador_que_esta_lejos(self):
        guardian = Guardian(1, 0, 0, Perseguir(radio_deteccion=100, velocidad=100))
        mover_guardian(guardian, 1, [jugador_en(500, 0)])
        assert (guardian.x, guardian.y) == (0, 0)

    def test_elige_al_mas_cercano(self):
        guardian = Guardian(1, 0, 0, Perseguir(radio_deteccion=300, velocidad=100))
        mover_guardian(guardian, 0.5, [jugador_en(0, 200), jugador_en(100, 0)])
        assert guardian.x > 0
        assert guardian.y == pytest.approx(0)

    def test_sin_jugadores_se_queda_quieto(self):
        guardian = Guardian(1, 10, 10, Perseguir())
        assert guardian.mover(CICLO_S, []) is False


class TestGuardian:
    def test_alcanza_cuando_los_circulos_se_tocan(self):
        guardian = Guardian(1, 100, 100, RutaFija([(100, 100)]), radio=18)
        assert guardian.alcanza(100 + 18 + RADIO, 100, RADIO)
        assert not guardian.alcanza(100 + 18 + RADIO + 1, 100, RADIO)

    def test_a_dict(self):
        guardian = Guardian(3, 100.4, 50.6, RutaFija([(0, 0)]), radio=18)
        assert guardian.a_dict() == {"id": 3, "x": 100, "y": 51, "radio": 18}


class TestPenalizacionEnElMotor:
    def test_el_jugador_empieza_normal(self):
        motor = motor_con([])
        assert estado_del_jugador(motor)["estado"] == NORMAL

    def test_el_estado_trae_la_lista_de_guardianes(self):
        motor = motor_con([Guardian(7, 500, 300, RutaFija([(500, 300)]))])
        assert motor.estado()["guardianes"] == [{"id": 7, "x": 500, "y": 300, "radio": 18}]

    def test_sin_guardianes_la_lista_va_vacia(self):
        assert motor_con([]).estado()["guardianes"] == []

    def test_un_guardian_lejos_no_penaliza(self):
        motor = motor_con([Guardian(1, 800, 500, RutaFija([(800, 500)]))])
        avanzar(motor, 10)
        assert estado_del_jugador(motor)["estado"] == NORMAL

    def test_el_guardian_que_alcanza_al_jugador_lo_aturde(self):
        motor = motor_con([Guardian(1, 100, 100, RutaFija([(100, 100)]))])
        avanzar(motor, 1)
        assert estado_del_jugador(motor)["estado"] == ATURDIDO

    def test_aturdido_no_se_puede_mover(self):
        motor = motor_con([Guardian(1, 100, 100, RutaFija([(100, 100)]))])
        avanzar(motor, 1)
        motor.aplicar_entrada(1, "derecha", "presionado")
        avanzar(motor, ticks_para(1))
        assert estado_del_jugador(motor)["x"] == 100

    def test_pierde_puntos_pero_no_baja_de_cero(self):
        motor = motor_con([Guardian(1, 100, 100, RutaFija([(100, 100)]))])
        motor.sumar_puntaje(1, 3)
        avanzar(motor, 1)
        assert estado_del_jugador(motor)["puntaje"] == 0

    def test_pierde_la_penalizacion_completa_si_tiene_puntos(self):
        motor = motor_con([Guardian(1, 100, 100, RutaFija([(100, 100)]))])
        motor.sumar_puntaje(1, 20)
        avanzar(motor, 1)
        assert estado_del_jugador(motor)["puntaje"] == 20 - PENALIZACION_PUNTOS

    def test_un_guardian_encima_no_lo_penaliza_varias_veces(self):
        motor = motor_con([Guardian(1, 100, 100, RutaFija([(100, 100)]))])
        motor.sumar_puntaje(1, 50)
        avanzar(motor, ticks_para(DURACION_ATURDIDO_S) - 2)  # sigue aturdido
        assert estado_del_jugador(motor)["puntaje"] == 50 - PENALIZACION_PUNTOS

    def test_despues_del_aturdimiento_queda_escudado_y_luego_normal(self):
        motor = motor_con([Guardian(1, 100, 100, RutaFija([(100, 100)]))])
        avanzar(motor, 1)
        avanzar(motor, ticks_para(DURACION_ATURDIDO_S) + 1)
        assert estado_del_jugador(motor)["estado"] == ESCUDADO

    def test_al_salir_del_escudo_un_guardian_encima_lo_vuelve_a_golpear(self):
        motor = motor_con([Guardian(1, 100, 100, RutaFija([(100, 100)]))])
        motor.sumar_puntaje(1, 50)
        avanzar(motor, ticks_para(DURACION_ATURDIDO_S + 2) + 5)
        assert estado_del_jugador(motor)["puntaje"] == 50 - 2 * PENALIZACION_PUNTOS

    def test_el_jugador_escudado_no_es_penalizado(self):
        motor = motor_con([])
        motor._jugadores[1].estado = motor._jugadores[1].estado.golpeado()  # aturdido
        motor._jugadores[1].estado = motor._jugadores[1].estado.actualizar(DURACION_ATURDIDO_S)
        motor._guardianes.append(Guardian(1, 100, 100, RutaFija([(100, 100)])))
        motor.sumar_puntaje(1, 10)
        avanzar(motor, 1)
        assert estado_del_jugador(motor)["puntaje"] == 10

    def test_un_guardian_que_patrulla_termina_alcanzando_al_jugador(self):
        guardian = Guardian(1, 300, 100, Patrulla([(300, 100), (100, 100)], velocidad=100))
        motor = motor_con([guardian])
        avanzar(motor, ticks_para(4))
        assert estado_del_jugador(motor)["estado"] == ATURDIDO

    def test_los_guardianes_se_mueven_y_avisan_a_los_clientes(self):
        guardian = Guardian(1, 500, 300, Patrulla([(500, 300), (700, 300)], velocidad=100))
        motor = motor_con([guardian])
        observador = ObservadorFalso()
        motor.suscribir(observador)
        avanzar(motor, ticks_para(1))
        estados = [e.datos for e in observador.eventos if e.tipo == ESTADO_ACTUALIZADO]
        assert estados[-1]["guardianes"][0]["x"] > 500

    def test_la_penalizacion_se_avisa_como_evento(self):
        motor = motor_con([Guardian(4, 100, 100, RutaFija([(100, 100)]))])
        motor.sumar_puntaje(1, 20)
        observador = ObservadorFalso()
        motor.suscribir(observador)
        avanzar(motor, 1)
        penalizaciones = [e for e in observador.eventos if e.tipo == JUGADOR_PENALIZADO]
        assert len(penalizaciones) == 1
        assert penalizaciones[0].datos == {
            "jugador_id": 1,
            "guardian_id": 4,
            "puntos": -PENALIZACION_PUNTOS,
            "estado": ATURDIDO,
        }

    def test_sin_guardianes_no_hay_cambios_ni_avisos(self):
        motor = motor_con([])
        observador = ObservadorFalso()
        motor.suscribir(observador)
        avanzar(motor, 1)
        enviados = len(observador.eventos)
        avanzar(motor, ticks_para(10))
        assert len(observador.eventos) == enviados