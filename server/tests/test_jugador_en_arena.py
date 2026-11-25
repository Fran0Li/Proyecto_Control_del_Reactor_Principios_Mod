"""Número de cada jugador (su esquina y su color) y acción del jugador aturdido (US-09, US-15)."""

from app.realtime.arena import PUNTOS_DE_INICIO, Arena, Reactor
from app.realtime.estados_jugador import Aturdido, Escudado
from app.realtime.motor_partida import MotorPartida
from app.realtime.reactor import ENERGIA_POR_EXTRACCION


def numero_de(motor, jugador_id):
    return next(
        j["numero"] for j in motor.estado()["jugadores"] if j["jugador_id"] == jugador_id
    )


def motor_con_reactor_en_el_inicio():
    """El primer punto de inicio queda encima del reactor, así el jugador 1 puede extraer."""
    x, y = PUNTOS_DE_INICIO[0]
    return MotorPartida(1, arena=Arena(reactor=Reactor(x=x, y=y, radio=40)))


def puntaje_de(motor, jugador_id):
    return next(
        j["puntaje"] for j in motor.estado()["jugadores"] if j["jugador_id"] == jugador_id
    )


class TestNumeroDelJugador:
    def test_los_jugadores_se_numeran_por_orden_de_llegada(self):
        motor = MotorPartida(1)
        for jugador_id in (50, 20, 30, 10):
            motor.agregar_jugador(jugador_id)
        assert [numero_de(motor, j) for j in (50, 20, 30, 10)] == [1, 2, 3, 4]

    def test_el_numero_no_depende_del_id(self):
        motor = MotorPartida(1)
        motor.agregar_jugador(99)
        assert numero_de(motor, 99) == 1

    def test_el_numero_coincide_con_la_esquina_de_inicio(self):
        motor = MotorPartida(1)
        for jugador_id in (1, 2, 3, 4):
            motor.agregar_jugador(jugador_id)
        for jugador in motor.estado()["jugadores"]:
            x, y = PUNTOS_DE_INICIO[jugador["numero"] - 1]
            assert (jugador["x"], jugador["y"]) == (x, y)

    def test_al_reconectarse_conserva_su_numero(self):
        motor = MotorPartida(1)
        motor.agregar_jugador(1)
        motor.agregar_jugador(2)
        motor.agregar_jugador(2)  # vuelve a conectarse
        assert numero_de(motor, 2) == 2

    def test_el_estado_trae_el_numero_de_cada_jugador(self):
        motor = MotorPartida(1)
        motor.agregar_jugador(7, "ana")
        (jugador,) = motor.estado()["jugadores"]
        assert jugador["numero"] == 1


class TestAccionDelJugadorAturdido:
    def test_un_jugador_normal_extrae_energia(self):
        motor = motor_con_reactor_en_el_inicio()
        motor.agregar_jugador(1)
        motor.aplicar_entrada(1, "accion", "presionado")
        assert puntaje_de(motor, 1) == ENERGIA_POR_EXTRACCION

    def test_un_jugador_aturdido_no_extrae_energia(self):
        motor = motor_con_reactor_en_el_inicio()
        motor.agregar_jugador(1)
        motor._jugadores[1].estado = Aturdido()
        motor.aplicar_entrada(1, "accion", "presionado")
        assert puntaje_de(motor, 1) == 0

    def test_el_boton_ignorado_no_gasta_la_energia_del_reactor(self):
        motor = motor_con_reactor_en_el_inicio()
        motor.agregar_jugador(1)
        energia = motor.estado()["reactor"]["energia"]
        motor._jugadores[1].estado = Aturdido()
        motor.aplicar_entrada(1, "accion", "presionado")
        assert motor.estado()["reactor"]["energia"] == energia

    def test_un_jugador_escudado_si_puede_extraer(self):
        motor = motor_con_reactor_en_el_inicio()
        motor.agregar_jugador(1)
        motor._jugadores[1].estado = Escudado()
        motor.aplicar_entrada(1, "accion", "presionado")
        assert puntaje_de(motor, 1) == ENERGIA_POR_EXTRACCION