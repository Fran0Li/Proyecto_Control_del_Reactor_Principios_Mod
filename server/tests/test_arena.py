"""Pruebas del modelo de la arena y de cómo lo usa el motor: datos simples, sin red ni base."""

import asyncio

from app.realtime.arena import (
    ALTO_ARENA,
    ANCHO_ARENA,
    PUNTOS_DE_INICIO,
    RADIO_JUGADOR,
    Arena,
    Celda,
    Obstaculo,
    Reactor,
    arena_basica,
)
from app.realtime.eventos import ESTADO_ACTUALIZADO
from app.realtime.motor_partida import MotorPartida


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


def arena_chica():
    """Una arena de 200 x 100 con un solo punto de inicio."""
    return Arena(reactor=Reactor(100, 50, 10), ancho=200, alto=100, puntos_inicio=((50, 50),))


# el modelo 


def test_la_arena_basica_tiene_el_reactor_al_centro_y_nada_mas():
    arena = arena_basica()
    assert (arena.reactor.x, arena.reactor.y) == (ANCHO_ARENA / 2, ALTO_ARENA / 2)
    assert arena.obstaculos == []
    assert arena.celdas == []
    assert arena.puntos_inicio == PUNTOS_DE_INICIO


def test_el_diccionario_de_la_arena_trae_los_campos_del_contrato():
    datos = arena_basica().a_dict()
    assert set(datos) == {"ancho", "alto", "radio", "reactor", "obstaculos", "celdas"}
    assert datos["ancho"] == ANCHO_ARENA
    assert datos["alto"] == ALTO_ARENA
    assert datos["radio"] == RADIO_JUGADOR
    assert datos["reactor"] == {"x": 480, "y": 270, "radio": 40}


def test_el_diccionario_incluye_obstaculos_y_celdas():
    arena = Arena(
        reactor=Reactor(480, 270, 40),
        obstaculos=[Obstaculo(300, 200, 80, 20, "trampa")],
        celdas=[Celda(id=1, x=200, y=400, valor=10)],
    )
    datos = arena.a_dict()
    assert datos["obstaculos"] == [{"x": 300, "y": 200, "ancho": 80, "alto": 20, "tipo": "trampa"}]
    assert datos["celdas"] == [{"id": 1, "x": 200, "y": 400, "valor": 10}]


def test_un_obstaculo_es_barrera_si_no_se_indica_el_tipo():
    assert Obstaculo(0, 0, 10, 10).tipo == "barrera"


def test_dos_arenas_no_comparten_sus_listas():
    una, otra = arena_basica(), arena_basica()
    una.celdas.append(Celda(1, 0, 0, 5))
    assert otra.celdas == []


# el motor usa la arena 


def test_el_estado_del_motor_trae_el_reactor_los_obstaculos_y_las_celdas():
    arena = Arena(
        reactor=Reactor(480, 270, 40),
        obstaculos=[Obstaculo(300, 200, 80, 20)],
        celdas=[Celda(1, 200, 400, 10)],
    )
    estado = MotorPartida(1, arena).estado()
    assert estado["arena"] == arena.a_dict()
    assert estado["arena"]["reactor"] == {"x": 480, "y": 270, "radio": 40}


def test_sin_indicar_la_arena_el_motor_usa_la_basica():
    assert MotorPartida(1).estado()["arena"] == arena_basica().a_dict()


def test_los_jugadores_aparecen_en_los_puntos_de_inicio_de_su_arena():
    motor = MotorPartida(1, arena_chica())
    motor.agregar_jugador(1)
    assert (motor.estado()["jugadores"][0]["x"], motor.estado()["jugadores"][0]["y"]) == (50, 50)


def test_el_motor_respeta_el_tamano_de_su_arena():
    motor = MotorPartida(1, arena_chica())
    motor.agregar_jugador(1)
    motor.aplicar_entrada(1, "derecha", "presionado")
    avanzar(motor, 60)  # 3 s: de sobra para llegar a la pared
    assert motor.estado()["jugadores"][0]["x"] == 200 - RADIO_JUGADOR


# el puntaje


def test_el_jugador_empieza_con_cero_puntos():
    motor = MotorPartida(1)
    motor.agregar_jugador(1)
    assert motor.estado()["jugadores"][0]["puntaje"] == 0


def test_sumar_puntaje_se_ve_en_el_estado_y_avisa_a_los_observadores():
    motor = MotorPartida(1)
    observador = ObservadorFalso()
    motor.suscribir(observador)
    motor.agregar_jugador(1)
    avanzar(motor, 1)
    observador.eventos.clear()

    motor.sumar_puntaje(1, 10)
    avanzar(motor, 1)

    assert motor.estado()["jugadores"][0]["puntaje"] == 10
    assert [e.tipo for e in observador.eventos] == [ESTADO_ACTUALIZADO]
    assert observador.eventos[0].datos["jugadores"][0]["puntaje"] == 10


def test_el_puntaje_puede_bajar():
    motor = MotorPartida(1)
    motor.agregar_jugador(1)
    motor.sumar_puntaje(1, 10)
    motor.sumar_puntaje(1, -4)
    assert motor.estado()["jugadores"][0]["puntaje"] == 6


def test_sumar_a_un_jugador_que_no_esta_o_sumar_cero_no_hace_nada():
    motor = MotorPartida(1)
    observador = ObservadorFalso()
    motor.suscribir(observador)
    motor.agregar_jugador(1)
    avanzar(motor, 1)
    observador.eventos.clear()

    motor.sumar_puntaje(99, 10)
    motor.sumar_puntaje(1, 0)
    avanzar(motor, 1)

    assert observador.eventos == []
    assert motor.estado()["jugadores"][0]["puntaje"] == 0


def test_quien_vuelve_a_entrar_conserva_su_puntaje():
    motor = MotorPartida(1)
    motor.agregar_jugador(1)
    motor.sumar_puntaje(1, 25)
    motor.agregar_jugador(1)  # reconexión
    assert motor.estado()["jugadores"][0]["puntaje"] == 25