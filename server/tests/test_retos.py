"""Retos con puntos extra durante la partida (US-27, criterio 3)."""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models.evento import Evento
from app.models.partida import Partida
from app.models.usuario import Usuario
from app.realtime.arena import Arena, Reactor
from app.realtime.connection_manager import ConnectionManager
from app.realtime.eventos import (
    ACCION_REALIZADA,
    ESTADO_ACTUALIZADO,
    JUGADOR_PENALIZADO,
    PARTIDA_FINALIZADA,
    PARTIDA_INICIADA,
    RETO_COMPLETADO,
    EventoPartida,
)
from app.realtime.gestor_motores import GestorMotores
from app.realtime.motor_partida import CICLO_S, FINALIZADA, MotorPartida
from app.realtime.registro_eventos import RegistroEventos
from app.realtime.retos import (
    CATALOGO,
    ENERGIA_RACHA,
    POR_CLAVE,
    SEGUNDOS_SIN_RASGUNOS,
    VENTANA_RACHA_S,
    GestorRetos,
)
from app.repositories import PartidaRepository, UsuarioRepository

UN_SEGUNDO = round(1 / CICLO_S)

# --- ayudas -----------------------------------------------------------------------------------


class MotorFalso:
    """Lo mínimo del motor: el reloj, los puntos y los eventos publicados."""

    def __init__(self):
        self.transcurrido = 0.0
        self.puntos: dict[int, int] = {}
        self.publicados: list[tuple[str, dict]] = []

    def sumar_puntaje(self, jugador_id, puntos):
        self.puntos[jugador_id] = self.puntos.get(jugador_id, 0) + puntos

    def publicar(self, tipo, datos):
        self.publicados.append((tipo, datos))


def enviar(observador, *eventos):
    async def correr():
        for evento in eventos:
            await observador.al_evento(evento)

    asyncio.run(correr())


def inicio(*jugadores):
    return EventoPartida(PARTIDA_INICIADA, 1, {"jugadores": list(jugadores)})


def extraccion(jugador_id, energia=10):
    datos = {"jugador_id": jugador_id, "accion": "reactor", "puntos": energia}
    return EventoPartida(ACCION_REALIZADA, 1, datos)


def estado(*jugadores):
    lista = [{"jugador_id": j} for j in jugadores]
    return EventoPartida(ESTADO_ACTUALIZADO, 1, {"jugadores": lista})


def golpe(jugador_id):
    datos = {"jugador_id": jugador_id, "guardian_id": 1, "puntos": -5, "estado": "aturdido"}
    return EventoPartida(JUGADOR_PENALIZADO, 1, datos)


def extraer_a_los(motor, retos, jugador_id, *segundos):
    for segundo in segundos:
        motor.transcurrido = segundo
        enviar(retos, extraccion(jugador_id))


# --- catálogo ---------------------------------------------------------------------------------


def test_el_catalogo_trae_los_tres_retos_sin_repetir():
    claves = [reto.clave for reto in CATALOGO]
    assert claves == ["racha_nuclear", "primera_chispa", "sin_rasgunos"]
    assert all(reto.puntos > 0 for reto in CATALOGO)


# --- reglas con un motor falso ----------------------------------------------------------------


def test_antes_de_iniciar_no_se_cumple_ningun_reto():
    motor = MotorFalso()
    retos = GestorRetos(motor)

    extraer_a_los(motor, retos, 1, 0, 0.5, 1, 1.5, 2)
    motor.transcurrido = SEGUNDOS_SIN_RASGUNOS + 1
    enviar(retos, estado(1))

    assert motor.puntos == {}
    assert motor.publicados == []


def test_primera_chispa_es_solo_para_el_primero_que_extrae():
    motor = MotorFalso()
    retos = GestorRetos(motor)
    enviar(retos, inicio(1, 2))

    extraer_a_los(motor, retos, 2, 1)
    extraer_a_los(motor, retos, 1, 2)

    assert retos.cumplidos(2) == {"primera_chispa"}
    assert retos.cumplidos(1) == set()
    assert motor.puntos == {2: POR_CLAVE["primera_chispa"].puntos}


def test_racha_nuclear_con_50_de_energia_en_15_segundos():
    motor = MotorFalso()
    retos = GestorRetos(motor)
    enviar(retos, inicio(1))

    extraer_a_los(motor, retos, 1, 0, 3, 6, 9)  # 40 de energía
    assert "racha_nuclear" not in retos.cumplidos(1)
    extraer_a_los(motor, retos, 1, VENTANA_RACHA_S)  # la quinta, justo a los 15 s: 50

    assert "racha_nuclear" in retos.cumplidos(1)
    assert motor.puntos[1] == POR_CLAVE["primera_chispa"].puntos + POR_CLAVE["racha_nuclear"].puntos


def test_racha_nuclear_no_cuenta_lo_que_quedo_fuera_de_los_15_segundos():
    motor = MotorFalso()
    retos = GestorRetos(motor)
    enviar(retos, inicio(1))

    # 50 de energía en total, pero la primera extracción queda 15,5 s antes de la última
    extraer_a_los(motor, retos, 1, 0, 6, 9, 12, 15.5)

    assert "racha_nuclear" not in retos.cumplidos(1)
    assert ENERGIA_RACHA == 50


def test_sin_rasgunos_a_los_60_segundos_sin_golpes():
    motor = MotorFalso()
    retos = GestorRetos(motor)
    enviar(retos, inicio(1))

    motor.transcurrido = SEGUNDOS_SIN_RASGUNOS - 1
    enviar(retos, estado(1))
    assert "sin_rasgunos" not in retos.cumplidos(1)
    motor.transcurrido = SEGUNDOS_SIN_RASGUNOS
    enviar(retos, estado(1))

    assert retos.cumplidos(1) == {"sin_rasgunos"}
    assert motor.puntos == {1: POR_CLAVE["sin_rasgunos"].puntos}


def test_un_golpe_de_guardian_reinicia_la_cuenta_de_sin_rasgunos():
    motor = MotorFalso()
    retos = GestorRetos(motor)
    enviar(retos, inicio(1))

    motor.transcurrido = 30
    enviar(retos, golpe(1))
    motor.transcurrido = SEGUNDOS_SIN_RASGUNOS
    enviar(retos, estado(1))
    assert "sin_rasgunos" not in retos.cumplidos(1)  # solo 30 s desde el golpe

    motor.transcurrido = 30 + SEGUNDOS_SIN_RASGUNOS
    enviar(retos, estado(1))
    assert "sin_rasgunos" in retos.cumplidos(1)


def test_cada_reto_se_cumple_una_sola_vez_por_partida():
    motor = MotorFalso()
    retos = GestorRetos(motor)
    enviar(retos, inicio(1))

    extraer_a_los(motor, retos, 1, *[i * 0.5 for i in range(20)])  # 200 de energía en 10 s
    for segundo in (60, 61, 120):
        motor.transcurrido = segundo
        enviar(retos, estado(1))

    esperado = sum(reto.puntos for reto in CATALOGO)
    assert motor.puntos == {1: esperado}
    assert [datos["reto"] for _, datos in motor.publicados] == [
        "primera_chispa",
        "racha_nuclear",
        "sin_rasgunos",
    ]


def test_publica_reto_completado_con_sus_datos():
    motor = MotorFalso()
    retos = GestorRetos(motor)
    enviar(retos, inicio(7))

    extraer_a_los(motor, retos, 7, 1)

    tipo, datos = motor.publicados[0]
    assert tipo == RETO_COMPLETADO
    assert datos == {
        "jugador_id": 7,
        "reto": "primera_chispa",
        "nombre": "Primera chispa",
        "puntos": 10,
    }


def test_terminada_la_partida_ya_no_se_cumplen_retos():
    motor = MotorFalso()
    retos = GestorRetos(motor)
    enviar(retos, inicio(1), EventoPartida(PARTIDA_FINALIZADA, 1, {"puntajes": {}}))

    extraer_a_los(motor, retos, 1, 1)
    motor.transcurrido = SEGUNDOS_SIN_RASGUNOS * 2
    enviar(retos, estado(1))

    assert motor.puntos == {}


def test_al_iniciar_otra_vez_se_olvida_lo_anterior():
    motor = MotorFalso()
    retos = GestorRetos(motor)
    enviar(retos, inicio(1))
    extraer_a_los(motor, retos, 1, 1)

    enviar(retos, inicio(1))

    assert retos.cumplidos(1) == set()


# --- con el motor real ------------------------------------------------------------------------


class Grabador:
    def __init__(self):
        self.eventos = []

    async def al_evento(self, evento):
        self.eventos.append(evento)


def motor_sobre_el_reactor():
    arena = Arena(reactor=Reactor(480, 270, 40), puntos_inicio=((480, 270), (100, 100)))
    motor = MotorPartida(1, arena)
    motor.suscribir(GestorRetos(motor))
    grabador = Grabador()
    motor.suscribir(grabador)
    motor.agregar_jugador(1, "ana")
    return motor, grabador


def puntaje(motor, jugador_id=1):
    return next(j["puntaje"] for j in motor.estado()["jugadores"] if j["jugador_id"] == jugador_id)


def test_con_el_motor_real_los_retos_suman_puntos_en_la_partida():
    motor, grabador = motor_sobre_el_reactor()

    async def jugar():
        for _ in range(3):  # práctica antes de iniciar: no cuenta
            motor.aplicar_entrada(1, "accion", "presionado")
            for _ in range(UN_SEGUNDO // 2):
                await motor.tick()
        motor.iniciar_partida(300, 500)
        await motor.tick()
        for _ in range(5):  # 5 extracciones de 10 en unos 2,5 s
            motor.aplicar_entrada(1, "accion", "presionado")
            for _ in range(UN_SEGUNDO // 2):
                await motor.tick()
        assert puntaje(motor) == 50 + 10 + 25  # energía + primera chispa + racha nuclear
        for _ in range(round(SEGUNDOS_SIN_RASGUNOS) * UN_SEGUNDO):
            await motor.tick()

    asyncio.run(jugar())

    assert puntaje(motor) == 50 + 10 + 25 + 30
    retos = [e.datos["reto"] for e in grabador.eventos if e.tipo == RETO_COMPLETADO]
    assert retos == ["primera_chispa", "racha_nuclear", "sin_rasgunos"]


def test_los_puntos_de_los_retos_cuentan_para_ganar():
    """Con objetivo de 20: 10 de energía + 10 de "primera chispa" terminan la partida."""
    motor, grabador = motor_sobre_el_reactor()

    async def jugar():
        motor.iniciar_partida(300, 20)
        await motor.tick()
        motor.aplicar_entrada(1, "accion", "presionado")
        for _ in range(3):
            await motor.tick()

    asyncio.run(jugar())

    assert motor.estado_partida == FINALIZADA
    fin = next(e for e in grabador.eventos if e.tipo == PARTIDA_FINALIZADA)
    assert fin.datos["motivo"] == "puntaje"
    assert fin.datos["puntajes"] == {1: 20}


def test_el_gestor_suscribe_los_retos_a_cada_partida():
    gestor = GestorMotores(ConnectionManager())

    async def revisar():
        motor = gestor.obtener(99)
        try:
            return any(isinstance(o, GestorRetos) for o in motor._observadores)
        finally:
            await motor.detener()
            gestor.limpiar()

    assert asyncio.run(revisar())


# --- en la base de datos ----------------------------------------------------------------------


@pytest.fixture
def fabrica(db_session):
    return sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)


def test_los_retos_cumplidos_quedan_en_la_tabla_eventos(db_session, fabrica):
    ana = UsuarioRepository(db_session).crear(
        Usuario(nombre_usuario="ana", correo="ana@mail.com", contrasena_hash="hash")
    )
    partida = PartidaRepository(db_session).crear(Partida())
    datos = {
        "jugador_id": ana.id,
        "reto": "primera_chispa",
        "nombre": "Primera chispa",
        "puntos": 10,
    }

    enviar(RegistroEventos(fabrica), EventoPartida(RETO_COMPLETADO, partida.id, datos))

    db_session.expire_all()
    guardados = list(db_session.scalars(select(Evento).where(Evento.partida_id == partida.id)))
    assert [(e.tipo, e.jugador_id, e.datos) for e in guardados] == [
        (RETO_COMPLETADO, ana.id, datos)
    ]
