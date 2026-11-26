"""GET /partidas/{id}/resultado: podio, estadísticas y récords para la ceremonia (US-18)."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_token_acceso
from app.db.session import get_session
from app.main import app
from app.models.partida import EstadoPartida, Partida
from app.models.usuario import Usuario
from app.realtime.eventos import ACCION_REALIZADA, JUGADOR_PENALIZADO, PARTIDA_FINALIZADA
from app.repositories import (
    EventoRepository,
    LogroRepository,
    PartidaRepository,
    UsuarioRepository,
)


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def crear_usuario(db_session, nombre):
    return UsuarioRepository(db_session).crear(
        Usuario(nombre_usuario=nombre, correo=f"{nombre}@mail.com", contrasena_hash="hash")
    )


def con_token(usuario):
    return {"Authorization": f"Bearer {crear_token_acceso(usuario.id)}"}


def partida_terminada(db_session, resultados, estado=EstadoPartida.finalizada):
    """`resultados`: lista de (usuario, puntaje, puesto)."""
    repo = PartidaRepository(db_session)
    partida = repo.crear(Partida(estado=EstadoPartida.en_curso))
    for usuario, _, _ in resultados:
        repo.agregar_participante(partida.id, usuario.id)
    if estado == EstadoPartida.finalizada:
        repo.guardar_resultado(partida, {u.id: (p, puesto) for u, p, puesto in resultados})
    return partida


@pytest.fixture()
def ana(db_session):
    return crear_usuario(db_session, "ana")


@pytest.fixture()
def beto(db_session):
    return crear_usuario(db_session, "beto")


def test_devuelve_el_podio_con_las_estadisticas_de_cada_jugador(client, db_session, ana, beto):
    partida = partida_terminada(db_session, [(ana, 120, 2), (beto, 300, 1)])
    eventos = EventoRepository(db_session)
    for _ in range(3):
        eventos.agregar(partida.id, ACCION_REALIZADA, beto.id, {"puntos": 25})
    eventos.agregar(partida.id, ACCION_REALIZADA, ana.id, {"puntos": 25})
    eventos.agregar(partida.id, JUGADOR_PENALIZADO, ana.id, {"puntos": 10})
    fin = {"motivo": "tiempo", "duracion_s": 300.0, "ganador_id": beto.id}
    eventos.agregar(partida.id, PARTIDA_FINALIZADA, None, fin)

    respuesta = client.get(f"/partidas/{partida.id}/resultado", headers=con_token(ana))

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["motivo"] == "tiempo" and datos["ganador_id"] == beto.id
    assert datos["duracion_s"] == 300.0
    primero, segundo = datos["jugadores"]
    assert (primero["nombre"], primero["puntaje"], primero["posicion"]) == ("beto", 300, 1)
    assert (primero["acciones"], primero["penalizaciones"]) == (3, 0)
    assert (segundo["nombre"], segundo["acciones"], segundo["penalizaciones"]) == ("ana", 1, 1)


def test_incluye_los_logros_que_se_desbloquearon_en_la_partida(client, db_session, ana, beto):
    partida = partida_terminada(db_session, [(ana, 300, 1), (beto, 0, 2)])
    LogroRepository(db_session).agregar(ana.id, ["primera_victoria"], partida.id)

    datos = client.get(f"/partidas/{partida.id}/resultado", headers=con_token(ana)).json()

    assert datos["jugadores"][0]["logros"] == [
        {"clave": "primera_victoria", "nombre": "Primera victoria"}
    ]
    assert datos["jugadores"][1]["logros"] == []


def test_marca_el_record_personal_solo_si_supera_sus_partidas_anteriores(
    client, db_session, ana, beto
):
    partida_terminada(db_session, [(ana, 200, 1), (beto, 150, 2)])
    nueva = partida_terminada(db_session, [(ana, 180, 2), (beto, 250, 1)])

    datos = client.get(f"/partidas/{nueva.id}/resultado", headers=con_token(ana)).json()

    record = {j["nombre"]: j["record_personal"] for j in datos["jugadores"]}
    assert record == {"beto": True, "ana": False}


def test_la_primera_partida_con_puntos_es_record_y_sin_puntos_no(client, db_session, ana, beto):
    partida = partida_terminada(db_session, [(ana, 40, 1), (beto, 0, 2)])

    datos = client.get(f"/partidas/{partida.id}/resultado", headers=con_token(ana)).json()

    assert [j["record_personal"] for j in datos["jugadores"]] == [True, False]


def test_una_partida_que_sigue_en_curso_da_409(client, db_session, ana, beto):
    partida = partida_terminada(db_session, [(ana, 0, 1)], estado=EstadoPartida.en_curso)

    respuesta = client.get(f"/partidas/{partida.id}/resultado", headers=con_token(ana))

    assert respuesta.status_code == 409


def test_una_partida_que_no_existe_da_404(client, ana):
    assert client.get("/partidas/9999/resultado", headers=con_token(ana)).status_code == 404


def test_sin_sesion_no_se_puede_ver(client, db_session, ana):
    partida = partida_terminada(db_session, [(ana, 10, 1)])

    assert client.get(f"/partidas/{partida.id}/resultado").status_code == 401
