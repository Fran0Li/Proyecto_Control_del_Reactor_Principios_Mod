"""Pruebas de las celdas de energía (US-13): recoger, sumar puntos y reponer. Sin red ni base."""

import asyncio

from app.realtime.arena import Arena, Celda, Reactor
from app.realtime.celdas import RADIO_CELDA, REPOSICION_S, RecolectorCeldas
from app.realtime.eventos import ESTADO_ACTUALIZADO
from app.realtime.motor_partida import CICLO_S, MotorPartida

RADIO_JUGADOR = 20
ALCANCE = RADIO_JUGADOR + RADIO_CELDA
TICKS_DE_REPOSICION = int(REPOSICION_S / CICLO_S)


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


def arena_con(celdas, puntos_inicio=((50, 50),)):
    """Una arena de 400 x 200 con las celdas que se pidan."""
    return Arena(
        reactor=Reactor(200, 100, 10),
        ancho=400,
        alto=200,
        puntos_inicio=puntos_inicio,
        celdas=celdas,
    )


def puntaje(motor, jugador_id):
    jugador = next(j for j in motor.estado()["jugadores"] if j["jugador_id"] == jugador_id)
    return jugador["puntaje"]


def celdas_en_el_mapa(motor):
    return motor.estado()["arena"]["celdas"]


# el recolector solo


def test_tocar_una_celda_la_recoge():
    celda = Celda(1, 100, 100, 10)
    recolector = RecolectorCeldas([celda], RADIO_JUGADOR)

    assert recolector.recoger([(7, 100, 100)]) == [(7, celda)]
    assert recolector.disponibles() == []


def test_una_celda_lejos_no_se_recoge():
    recolector = RecolectorCeldas([Celda(1, 100, 100, 10)], RADIO_JUGADOR)

    assert recolector.recoger([(7, 100 + ALCANCE + 1, 100)]) == []
    assert len(recolector.disponibles()) == 1


def test_justo_en_el_borde_se_recoge():
    recolector = RecolectorCeldas([Celda(1, 100, 100, 10)], RADIO_JUGADOR)

    assert len(recolector.recoger([(7, 100 + ALCANCE, 100)])) == 1


def test_si_dos_jugadores_tocan_la_misma_celda_se_la_lleva_el_primero():
    celda = Celda(1, 100, 100, 10)
    recolector = RecolectorCeldas([celda], RADIO_JUGADOR)

    assert recolector.recoger([(3, 100, 100), (9, 100, 100)]) == [(3, celda)]


def test_un_jugador_puede_recoger_dos_celdas_a_la_vez():
    recolector = RecolectorCeldas([Celda(1, 100, 100, 10), Celda(2, 110, 100, 5)], RADIO_JUGADOR)

    assert [celda.id for _, celda in recolector.recoger([(7, 105, 100)])] == [1, 2]


def test_una_celda_recogida_no_se_puede_recoger_otra_vez():
    recolector = RecolectorCeldas([Celda(1, 100, 100, 10)], RADIO_JUGADOR)
    recolector.recoger([(7, 100, 100)])

    assert recolector.recoger([(7, 100, 100)]) == []


def test_una_celda_recogida_vuelve_cuando_pasa_el_tiempo_de_reposicion():
    recolector = RecolectorCeldas([Celda(1, 100, 100, 10)], RADIO_JUGADOR, reposicion_s=1.0)
    recolector.recoger([(7, 100, 100)])

    assert recolector.reponer(0.5) is False
    assert recolector.disponibles() == []
    assert recolector.reponer(0.5) is True
    assert len(recolector.disponibles()) == 1


def test_reponer_sin_celdas_recogidas_no_cambia_nada():
    recolector = RecolectorCeldas([Celda(1, 100, 100, 10)], RADIO_JUGADOR)

    assert recolector.reponer(5.0) is False
    assert len(recolector.disponibles()) == 1


def test_una_celda_repuesta_se_puede_volver_a_recoger():
    recolector = RecolectorCeldas([Celda(1, 100, 100, 10)], RADIO_JUGADOR, reposicion_s=1.0)
    recolector.recoger([(7, 100, 100)])
    recolector.reponer(1.0)

    assert len(recolector.recoger([(8, 100, 100)])) == 1


# el motor con celdas


def test_el_jugador_que_toca_una_celda_suma_sus_puntos():
    motor = MotorPartida(1, arena_con([Celda(1, 110, 50, 10)]))
    motor.agregar_jugador(7)
    motor.aplicar_entrada(7, "derecha", "presionado")

    avanzar(motor, 10)

    assert puntaje(motor, 7) == 10


def test_la_celda_recogida_desaparece_del_estado():
    motor = MotorPartida(1, arena_con([Celda(1, 110, 50, 10)]))
    motor.agregar_jugador(7)
    assert len(celdas_en_el_mapa(motor)) == 1
    motor.aplicar_entrada(7, "derecha", "presionado")

    avanzar(motor, 10)

    assert celdas_en_el_mapa(motor) == []


def test_la_celda_vuelve_al_estado_despues_de_la_reposicion():
    motor = MotorPartida(1, arena_con([Celda(1, 110, 50, 10)]))
    motor.agregar_jugador(7)
    motor.aplicar_entrada(7, "derecha", "presionado")
    avanzar(motor, 10)  # la recoge y sigue de largo hasta la pared

    avanzar(motor, TICKS_DE_REPOSICION)

    assert celdas_en_el_mapa(motor) == [{"id": 1, "x": 110, "y": 50, "valor": 10}]


def test_los_puntos_se_acumulan_con_varias_celdas():
    celdas = [Celda(1, 110, 50, 10), Celda(2, 200, 50, 5)]
    motor = MotorPartida(1, arena_con(celdas))
    motor.agregar_jugador(7)
    motor.aplicar_entrada(7, "derecha", "presionado")

    avanzar(motor, 40)  # 2 s: llega a las dos celdas

    assert puntaje(motor, 7) == 15


def test_cada_jugador_recoge_su_celda():
    celdas = [Celda(1, 60, 50, 10), Celda(2, 60, 150, 20)]
    motor = MotorPartida(1, arena_con(celdas, puntos_inicio=((50, 50), (50, 150))))
    motor.agregar_jugador(1)
    motor.agregar_jugador(2)

    avanzar(motor, 1)

    assert (puntaje(motor, 1), puntaje(motor, 2)) == (10, 20)


def test_recoger_una_celda_avisa_a_los_observadores():
    motor = MotorPartida(1, arena_con([Celda(1, 110, 50, 10)]))
    observador = ObservadorFalso()
    motor.suscribir(observador)
    motor.agregar_jugador(7)
    motor.aplicar_entrada(7, "derecha", "presionado")

    avanzar(motor, 10)

    ultimo = observador.eventos[-1]
    assert ultimo.tipo == ESTADO_ACTUALIZADO
    assert ultimo.datos["jugadores"][0]["puntaje"] == 10
    assert ultimo.datos["arena"]["celdas"] == []


def test_que_la_celda_vuelva_tambien_avisa_aunque_nadie_se_mueva():
    motor = MotorPartida(1, arena_con([Celda(1, 110, 50, 10)]))
    observador = ObservadorFalso()
    motor.suscribir(observador)
    motor.agregar_jugador(7)
    motor.aplicar_entrada(7, "derecha", "presionado")
    avanzar(motor, 100)  # recoge la celda y llega a la pared: ya no hay cambios
    avisos = len(observador.eventos)

    avanzar(motor, TICKS_DE_REPOSICION)

    assert len(observador.eventos) == avisos + 1
    assert observador.eventos[-1].datos["arena"]["celdas"] != []


def test_sin_celdas_en_la_arena_el_puntaje_no_cambia():
    motor = MotorPartida(1, arena_con([]))
    motor.agregar_jugador(7)
    motor.aplicar_entrada(7, "derecha", "presionado")

    avanzar(motor, 40)

    assert puntaje(motor, 7) == 0