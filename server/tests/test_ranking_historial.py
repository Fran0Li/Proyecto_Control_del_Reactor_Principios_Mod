"""GET /ranking (US-19) y GET /historial (US-20)."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_token_acceso
from app.db.session import get_session
from app.main import app
from app.models.partida import EstadoPartida, Partida
from app.models.usuario import Usuario
from app.repositories import (
    LogroRepository,
    PartidaRepository,
    RankingRepository,
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


def jugar(db_session, resultados, estado=EstadoPartida.finalizada):
    """Una partida con `resultados` = [(usuario, puntaje, puesto)], sumada al ranking."""
    repo = PartidaRepository(db_session)
    partida = repo.crear(Partida(estado=EstadoPartida.en_curso, escenario="laboratorio"))
    for usuario, _, _ in resultados:
        repo.agregar_participante(partida.id, usuario.id)
    if estado == EstadoPartida.finalizada:
        repo.guardar_resultado(partida, {u.id: (p, puesto) for u, p, puesto in resultados})
        for usuario, puntaje, puesto in resultados:
            RankingRepository(db_session).sumar_partida(usuario.id, puntaje, puesto == 1)
    return partida


# ranking global (US-19)


def test_el_ranking_ordena_por_puntos_y_luego_por_victorias(client, db_session):
    ana, beto, carla = (crear_usuario(db_session, n) for n in ("ana", "beto", "carla"))
    jugar(db_session, [(ana, 100, 1), (beto, 40, 2)])
    jugar(db_session, [(carla, 140, 1), (beto, 100, 2)])  # beto: 140 y 0 victorias

    datos = client.get("/ranking", headers=con_token(ana)).json()

    filas = [
        (fila["posicion"], fila["nombre"], fila["puntos_totales"], fila["victorias"])
        for fila in datos["top"]
    ]
    assert filas == [(1, "carla", 140, 1), (2, "beto", 140, 0), (3, "ana", 100, 1)]


def test_el_ranking_muestra_solo_los_diez_mejores_y_el_puesto_propio(client, db_session):
    jugadores = [crear_usuario(db_session, f"jugador{i}") for i in range(12)]
    for puntos, jugador in enumerate(jugadores, start=1):
        RankingRepository(db_session).sumar_partida(jugador.id, puntos * 10, gano=False)
    ultimo = jugadores[0]  # el de menos puntos

    datos = client.get("/ranking", headers=con_token(ultimo)).json()

    assert len(datos["top"]) == 10
    assert datos["top"][0]["nombre"] == "jugador11"
    assert datos["yo"]["posicion"] == 12 and datos["yo"]["puntos_totales"] == 10


def test_quien_nunca_jugo_no_tiene_puesto(client, db_session):
    nuevo = crear_usuario(db_session, "nuevo")

    datos = client.get("/ranking", headers=con_token(nuevo)).json()

    assert datos == {"top": [], "yo": None}


def test_el_ranking_cambia_al_terminar_otra_partida(client, db_session):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    jugar(db_session, [(ana, 100, 1), (beto, 50, 2)])
    antes = client.get("/ranking", headers=con_token(ana)).json()["top"][0]["nombre"]

    jugar(db_session, [(beto, 200, 1), (ana, 0, 2)])
    despues = client.get("/ranking", headers=con_token(ana)).json()["top"][0]["nombre"]

    assert (antes, despues) == ("ana", "beto")


# historial (US-20)


def test_el_historial_trae_las_partidas_terminadas_del_jugador(client, db_session):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    primera = jugar(db_session, [(ana, 120, 1), (beto, 80, 2)])
    segunda = jugar(db_session, [(ana, 60, 2), (beto, 90, 1)])
    jugar(db_session, [(ana, 0, 1)], estado=EstadoPartida.en_curso)  # sin terminar: no aparece

    datos = client.get("/historial", headers=con_token(ana)).json()

    assert [p["partida_id"] for p in datos["partidas"]] == [segunda.id, primera.id]
    reciente = datos["partidas"][0]
    assert (reciente["puntaje"], reciente["posicion"], reciente["gano"]) == (60, 2, False)
    assert reciente["jugadores"] == 2 and reciente["escenario"] == "laboratorio"
    assert reciente["fecha"] is not None


def test_el_historial_trae_las_estadisticas_acumuladas(client, db_session):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    partida = jugar(db_session, [(ana, 120, 1), (beto, 80, 2)])
    jugar(db_session, [(ana, 60, 2), (beto, 90, 1)])
    LogroRepository(db_session).agregar(ana.id, ["primera_partida", "primera_victoria"], partida.id)

    resumen = client.get("/historial", headers=con_token(ana)).json()["resumen"]

    assert resumen == {
        "partidas_jugadas": 2,
        "victorias": 1,
        "puntos_totales": 180,
        "mejor_puntaje": 120,
        "logros": 2,
    }


def test_cada_jugador_ve_solo_su_historial(client, db_session):
    ana, beto = crear_usuario(db_session, "ana"), crear_usuario(db_session, "beto")
    jugar(db_session, [(beto, 90, 1)])

    datos = client.get("/historial", headers=con_token(ana)).json()

    assert datos["partidas"] == []
    assert datos["resumen"]["partidas_jugadas"] == 0


def test_sin_sesion_no_hay_ranking_ni_historial(client):
    assert client.get("/ranking").status_code == 401
    assert client.get("/historial").status_code == 401
