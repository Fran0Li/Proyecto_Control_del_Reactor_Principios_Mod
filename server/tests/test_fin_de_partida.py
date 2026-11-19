"""Inicio, reloj y fin de la partida en el motor (US-17 y US-22), sin WebSocket ni base."""

import asyncio

from app.realtime.arena import PUNTOS_DE_INICIO
from app.realtime.eventos import ESTADO_ACTUALIZADO, PARTIDA_FINALIZADA, PARTIDA_INICIADA
from app.realtime.motor_partida import EN_CURSO, ESPERANDO, FINALIZADA, MotorPartida
from app.realtime.reglas_victoria import POR_ADMINISTRADOR, POR_PUNTAJE, POR_TIEMPO

UN_SEGUNDO = 20  # ticks de 50 ms


class ObservadorFalso:
    def __init__(self):
        self.eventos = []

    async def al_evento(self, evento):
        self.eventos.append(evento)

    def de_tipo(self, tipo):
        return [e for e in self.eventos if e.tipo == tipo]


def avanzar(motor, ticks):
    async def correr():
        for _ in range(ticks):
            await motor.tick()

    asyncio.run(correr())


def motor_de_dos(observador=None):
    motor = MotorPartida(1)
    motor.agregar_jugador(10, "ana")
    motor.agregar_jugador(11, "beto")
    if observador is not None:
        motor.suscribir(observador)
    return motor


def jugador(motor, jugador_id):
    return next(j for j in motor.estado()["jugadores"] if j["jugador_id"] == jugador_id)


def test_la_partida_empieza_esperando_y_sin_reloj():
    motor = motor_de_dos()

    assert motor.estado_partida == ESPERANDO
    assert motor.estado()["partida"] == {"estado": "esperando"}


def test_al_iniciar_todos_vuelven_al_inicio_con_cero_puntos():
    motor = motor_de_dos()
    motor.aplicar_entrada(10, "derecha", "presionado")
    avanzar(motor, UN_SEGUNDO)
    motor.sumar_puntaje(10, 40)

    assert motor.iniciar_partida(300, 500)

    ana = jugador(motor, 10)
    assert (ana["x"], ana["y"]) == PUNTOS_DE_INICIO[0]
    assert ana["puntaje"] == 0
    assert motor.estado_partida == EN_CURSO


def test_al_iniciar_avisa_partida_iniciada_con_las_reglas():
    observador = ObservadorFalso()
    motor = motor_de_dos(observador)

    motor.iniciar_partida(300, 500)
    avanzar(motor, 1)

    (evento,) = observador.de_tipo(PARTIDA_INICIADA)
    assert evento.datos == {"tiempo_limite": 300, "puntaje_objetivo": 500, "jugadores": [10, 11]}


def test_no_se_puede_iniciar_dos_veces():
    motor = motor_de_dos()
    motor.iniciar_partida(300, 500)

    assert not motor.iniciar_partida(300, 500)


def test_el_reloj_baja_y_se_avisa_una_vez_por_segundo():
    observador = ObservadorFalso()
    motor = motor_de_dos(observador)
    motor.iniciar_partida(300, 500)
    avanzar(motor, 1)
    observador.eventos.clear()

    avanzar(motor, 2 * UN_SEGUNDO)  # nadie se mueve: solo cambia el reloj

    assert len(observador.de_tipo(ESTADO_ACTUALIZADO)) == 2
    assert motor.estado()["partida"]["tiempo_restante"] == 298


def test_el_estado_trae_el_reloj_y_las_reglas():
    motor = motor_de_dos()
    motor.iniciar_partida(300, 500)
    avanzar(motor, 10 * UN_SEGUNDO)

    assert motor.estado()["partida"] == {
        "estado": "en_curso",
        "tiempo_limite": 300,
        "puntaje_objetivo": 500,
        "tiempo_restante": 290,
    }


def test_termina_cuando_se_acaba_el_tiempo():
    observador = ObservadorFalso()
    motor = motor_de_dos(observador)
    motor.iniciar_partida(2, 500)
    motor.sumar_puntaje(11, 30)

    avanzar(motor, 2 * UN_SEGUNDO)

    assert motor.estado_partida == FINALIZADA
    (fin,) = observador.de_tipo(PARTIDA_FINALIZADA)
    assert fin.datos["motivo"] == POR_TIEMPO
    assert fin.datos["ganador_id"] == 11
    assert fin.datos["puntajes"] == {11: 30, 10: 0}
    assert fin.datos["duracion_s"] == 2
    assert fin.datos["posiciones"] == [
        {"jugador_id": 11, "nombre": "beto", "puntaje": 30, "posicion": 1},
        {"jugador_id": 10, "nombre": "ana", "puntaje": 0, "posicion": 2},
    ]


def test_termina_al_llegar_a_la_puntuacion_objetivo():
    observador = ObservadorFalso()
    motor = motor_de_dos(observador)
    motor.iniciar_partida(300, 100)

    motor.sumar_puntaje(10, 100)
    avanzar(motor, 1)

    (fin,) = observador.de_tipo(PARTIDA_FINALIZADA)
    assert fin.datos["motivo"] == POR_PUNTAJE
    assert fin.datos["ganador_id"] == 10


def test_con_empate_arriba_no_hay_ganador():
    observador = ObservadorFalso()
    motor = motor_de_dos(observador)
    motor.iniciar_partida(1, 500)

    avanzar(motor, UN_SEGUNDO)

    (fin,) = observador.de_tipo(PARTIDA_FINALIZADA)
    assert fin.datos["ganador_id"] is None
    assert [p["posicion"] for p in fin.datos["posiciones"]] == [1, 1]


def test_antes_de_iniciar_no_termina_aunque_pase_el_tiempo():
    observador = ObservadorFalso()
    motor = motor_de_dos(observador)
    motor.sumar_puntaje(10, 1000)

    avanzar(motor, 3 * UN_SEGUNDO)

    assert motor.estado_partida == ESPERANDO
    assert observador.de_tipo(PARTIDA_FINALIZADA) == []


def test_termina_una_sola_vez():
    observador = ObservadorFalso()
    motor = motor_de_dos(observador)
    motor.iniciar_partida(1, 500)

    avanzar(motor, 3 * UN_SEGUNDO)

    assert len(observador.de_tipo(PARTIDA_FINALIZADA)) == 1
    assert not motor.terminar(POR_TIEMPO)


def test_terminada_la_arena_se_queda_quieta():
    motor = motor_de_dos()
    motor.iniciar_partida(1, 500)
    avanzar(motor, UN_SEGUNDO)
    antes = jugador(motor, 10)

    motor.aplicar_entrada(10, "derecha", "presionado")
    avanzar(motor, UN_SEGUNDO)

    assert jugador(motor, 10) == antes
    assert motor.estado()["partida"]["tiempo_restante"] == 0


def test_quien_se_va_en_plena_partida_cuenta_en_el_resultado():
    observador = ObservadorFalso()
    motor = motor_de_dos(observador)
    motor.iniciar_partida(1, 500)
    motor.sumar_puntaje(11, 50)

    motor.quitar_jugador(11)
    avanzar(motor, UN_SEGUNDO)

    (fin,) = observador.de_tipo(PARTIDA_FINALIZADA)
    assert fin.datos["ganador_id"] == 11


def test_el_que_se_fue_puede_volver_con_sus_puntos():
    motor = motor_de_dos()
    motor.iniciar_partida(300, 500)
    motor.sumar_puntaje(11, 50)

    motor.quitar_jugador(11)
    motor.quitar_jugador(10)
    assert not motor.hay_jugadores
    motor.agregar_jugador(11, "beto")

    assert motor.hay_jugadores
    assert jugador(motor, 11)["puntaje"] == 50


def test_un_administrador_puede_cerrarla_antes():
    observador = ObservadorFalso()
    motor = motor_de_dos(observador)
    motor.iniciar_partida(300, 500)

    assert motor.terminar(POR_ADMINISTRADOR)
    avanzar(motor, 1)

    (fin,) = observador.de_tipo(PARTIDA_FINALIZADA)
    assert fin.datos["motivo"] == POR_ADMINISTRADOR


def test_no_se_puede_terminar_una_partida_que_no_empezo():
    assert not motor_de_dos().terminar(POR_TIEMPO)
