"""Logros (US-27): catálogo, evaluación al terminar la partida, sin duplicados, y el endpoint.

El fin de partida (US-17) todavía no existe en el motor, así que aquí se emite el evento
`partida_finalizada` a mano, con el mismo contrato que va a usar el motor (app/realtime/eventos.py).
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import crear_token_acceso
from app.db.session import get_session
from app.main import app
from app.models.partida import Partida
from app.models.usuario import Usuario
from app.realtime.connection_manager import ConnectionManager
from app.realtime.evaluador_logros import EvaluadorLogros
from app.realtime.eventos import (
    ACCION_REALIZADA,
    ESTADO_ACTUALIZADO,
    PARTIDA_FINALIZADA,
    EventoPartida,
)
from app.realtime.gestor_motores import GestorMotores
from app.realtime.logros import (
    CATALOGO,
    ENERGIA_PARA_LOGRO,
    EstadisticasJugador,
    nuevos_logros,
)
from app.repositories import LogroRepository, PartidaRepository, UsuarioRepository

# --- ayudas -----------------------------------------------------------------------------------


@pytest.fixture()
def fabrica(db_session):
    """Sesiones nuevas sobre la misma base de la prueba, como las que usa el servidor."""
    return sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)


def crear_usuario(db_session, nombre):
    return UsuarioRepository(db_session).crear(
        Usuario(nombre_usuario=nombre, correo=f"{nombre}@mail.com", contrasena_hash="hash")
    )


def crear_partida(db_session):
    return PartidaRepository(db_session).crear(Partida()).id


def extraccion(partida_id, jugador_id, puntos=10, accion="reactor"):
    return EventoPartida(
        ACCION_REALIZADA,
        partida_id,
        {"jugador_id": jugador_id, "accion": accion, "puntos": puntos},
    )


def fin(partida_id, puntajes, ganador_id):
    return EventoPartida(
        PARTIDA_FINALIZADA, partida_id, {"puntajes": puntajes, "ganador_id": ganador_id}
    )


def enviar(evaluador, *eventos):
    async def correr():
        for evento in eventos:
            await evaluador.al_evento(evento)

    asyncio.run(correr())


def claves(db_session, jugador_id):
    return LogroRepository(db_session).claves_obtenidas(jugador_id)


# --- catálogo ---------------------------------------------------------------------------------


def test_las_claves_del_catalogo_no_se_repiten():
    todas = [logro.clave for logro in CATALOGO]
    assert len(todas) == len(set(todas))


def test_el_catalogo_trae_los_ejemplos_de_la_historia():
    todas = {logro.clave for logro in CATALOGO}
    assert {"primera_victoria", "energia_300"} <= todas


def test_nuevos_logros_no_repite_los_que_ya_tenia():
    estadisticas = EstadisticasJugador(1, energia_reactor=ENERGIA_PARA_LOGRO, gano=True)
    nuevos = {logro.clave for logro in nuevos_logros(estadisticas, {"primera_victoria"})}
    assert "primera_victoria" not in nuevos
    assert "energia_300" in nuevos


def test_la_energia_cuenta_desde_el_limite_exacto():
    justo = EstadisticasJugador(1, energia_reactor=ENERGIA_PARA_LOGRO)
    casi = EstadisticasJugador(1, energia_reactor=ENERGIA_PARA_LOGRO - 1)
    assert "energia_300" in {logro.clave for logro in nuevos_logros(justo, set())}
    assert "energia_300" not in {logro.clave for logro in nuevos_logros(casi, set())}


# --- evaluador --------------------------------------------------------------------------------


def test_al_terminar_guarda_los_logros_de_cada_jugador(db_session, fabrica):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    partida = crear_partida(db_session)
    evaluador = EvaluadorLogros(fabrica)

    extracciones = [extraccion(partida, ana.id) for _ in range(ENERGIA_PARA_LOGRO // 10)]
    enviar(evaluador, *extracciones, fin(partida, {ana.id: 300, beto.id: 40}, ana.id))

    assert claves(db_session, ana.id) == {"primera_partida", "primera_victoria", "energia_300"}
    assert claves(db_session, beto.id) == {"primera_partida"}


def test_solo_cuenta_la_energia_del_reactor(db_session, fabrica):
    ana = crear_usuario(db_session, "ana")
    partida = crear_partida(db_session)
    evaluador = EvaluadorLogros(fabrica)

    otras = [extraccion(partida, ana.id, accion="terminal") for _ in range(40)]
    enviar(evaluador, *otras, fin(partida, {ana.id: 400}, None))

    assert evaluador.estadisticas(ana.id).energia_reactor == 0
    assert "energia_300" not in claves(db_session, ana.id)


def test_ignora_los_eventos_que_no_le_interesan(db_session, fabrica):
    ana = crear_usuario(db_session, "ana")
    partida = crear_partida(db_session)
    evaluador = EvaluadorLogros(fabrica)

    enviar(evaluador, EventoPartida(ESTADO_ACTUALIZADO, partida, {"jugadores": []}))

    assert evaluador.estadisticas(ana.id).extracciones == 0
    assert claves(db_session, ana.id) == set()  # sin fin de partida no se guarda nada


def test_con_empate_nadie_gana_la_primera_victoria(db_session, fabrica):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    partida = crear_partida(db_session)

    enviar(EvaluadorLogros(fabrica), fin(partida, {ana.id: 50, beto.id: 50}, None))

    assert "primera_victoria" not in claves(db_session, ana.id)
    assert "primera_victoria" not in claves(db_session, beto.id)


def test_no_duplica_logros_de_una_partida_a_otra(db_session, fabrica):
    ana = crear_usuario(db_session, "ana")
    primera, segunda = crear_partida(db_session), crear_partida(db_session)

    enviar(EvaluadorLogros(fabrica), fin(primera, {ana.id: 10}, None))
    enviar(EvaluadorLogros(fabrica), fin(segunda, {ana.id: 90}, ana.id))

    filas = LogroRepository(db_session).de_jugador(ana.id)
    assert [fila.logro for fila in filas] == ["primera_partida", "primera_victoria"]
    assert [fila.partida_id for fila in filas] == [primera, segunda]


def test_una_partida_se_evalua_una_sola_vez(db_session, fabrica):
    ana = crear_usuario(db_session, "ana")
    partida = crear_partida(db_session)
    evaluador = EvaluadorLogros(fabrica)

    enviar(evaluador, fin(partida, {ana.id: 10}, None))
    # si el evento llegara repetido, no debe evaluar con datos distintos
    enviar(evaluador, fin(partida, {ana.id: 99}, ana.id))

    assert claves(db_session, ana.id) == {"primera_partida"}


def test_acepta_ids_como_texto(db_session, fabrica):
    """Si el fin de partida arma los puntajes desde JSON, las claves llegan como texto."""
    ana = crear_usuario(db_session, "ana")
    partida = crear_partida(db_session)

    enviar(EvaluadorLogros(fabrica), fin(partida, {str(ana.id): 10}, str(ana.id)))

    assert "primera_victoria" in claves(db_session, ana.id)


def test_el_gestor_suscribe_los_logros_a_cada_partida(db_session, fabrica):
    """Cuando el motor emita el fin de partida (US-17), los logros se guardan sin más cambios."""
    ana = crear_usuario(db_session, "ana")
    partida = crear_partida(db_session)
    gestor = GestorMotores(ConnectionManager(), fabrica)

    async def escenario():
        motor = gestor.obtener(partida)
        motor.agregar_jugador(ana.id)
        await motor._notificar(fin(partida, {ana.id: 10}, ana.id))
        await motor.detener()

    asyncio.run(escenario())

    assert claves(db_session, ana.id) == {"primera_partida", "primera_victoria"}


# --- endpoint ---------------------------------------------------------------------------------


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def cabecera(usuario):
    return {"Authorization": f"Bearer {crear_token_acceso(usuario.id, usuario.version_sesion)}"}


def test_sin_sesion_no_se_ven_los_logros(client):
    assert client.get("/logros").status_code == 401


def test_muestra_el_catalogo_con_los_obtenidos(client, db_session):
    ana = crear_usuario(db_session, "ana")
    partida = crear_partida(db_session)
    LogroRepository(db_session).agregar(ana.id, ["primera_partida"], partida)

    respuesta = client.get("/logros", headers=cabecera(ana))

    assert respuesta.status_code == 200
    logros = {logro["clave"]: logro for logro in respuesta.json()}
    assert set(logros) == {logro.clave for logro in CATALOGO}
    assert logros["primera_partida"]["obtenido"] is True
    assert logros["primera_partida"]["partida_id"] == partida
    assert logros["primera_victoria"]["obtenido"] is False
    assert logros["primera_victoria"]["obtenido_en"] is None


def test_cada_jugador_ve_solo_sus_logros(client, db_session):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    LogroRepository(db_session).agregar(ana.id, ["primera_victoria"], None)

    respuesta = client.get("/logros", headers=cabecera(beto))

    logros = {logro["clave"]: logro for logro in respuesta.json()}
    assert logros["primera_victoria"]["obtenido"] is False
