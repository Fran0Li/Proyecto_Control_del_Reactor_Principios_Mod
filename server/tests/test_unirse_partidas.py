"""Pruebas de US-08: listar partidas, unirse (RN-04 y cupos) y el canal en tiempo real."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.db.session import get_session
from app.main import app
from app.models.partida import EstadoPartida
from app.models.usuario import Usuario
from app.realtime.connection_manager import manager
from app.repositories import PartidaRepository, UsuarioRepository
from app.services.partida_factory import MAX_JUGADORES
from app.services.partida_service import (
    JugadorYaEnPartidaError,
    PartidaLlenaError,
    PartidaNoDisponibleError,
    PartidaNoEncontradaError,
    PartidaService,
)


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def canales_limpios():
    """Los canales viven en la memoria del servidor: cada prueba empieza sin conexiones."""
    manager._canales.clear()
    yield
    manager._canales.clear()


def crear_jugadores(db_session, cantidad):
    """Crea jugadores y devuelve sus ids (números, no objetos de la base)."""
    repo = UsuarioRepository(db_session)
    return [
        repo.crear(
            Usuario(nombre_usuario=f"jugador{i}", correo=f"j{i}@mail.com", contrasena_hash="hash")
        ).id
        for i in range(1, cantidad + 1)
    ]


def servicio(db_session):
    return PartidaService(PartidaRepository(db_session))


def crear_partida_por_api(client, creador_id):
    respuesta = client.post("/partidas", json={"creador_id": creador_id})
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def unirse_por_api(client, partida_id, jugador_id):
    return client.post(f"/partidas/{partida_id}/unirse", json={"jugador_id": jugador_id})


def llenar_partida(client, db_session):
    """Crea una partida con MAX_JUGADORES jugadores. Devuelve su id y el jugador que sobra."""
    ids = crear_jugadores(db_session, MAX_JUGADORES + 1)
    partida = crear_partida_por_api(client, ids[0])
    for jugador in ids[1:MAX_JUGADORES]:
        assert unirse_por_api(client, partida, jugador).status_code == 200
    return partida, ids[MAX_JUGADORES]


# servicio: listar y unirse 


def test_listar_disponibles_cuenta_los_jugadores_de_cada_partida(db_session):
    ana, beto, carla = crear_jugadores(db_session, 3)
    partidas = servicio(db_session)
    primera = partidas.crear_partida(ana)
    segunda = partidas.crear_partida(beto)
    partidas.unirse_a_partida(primera.id, carla)

    disponibles = {p.id: jugadores for p, jugadores in partidas.listar_disponibles()}

    assert disponibles == {primera.id: 2, segunda.id: 1}


def test_listar_disponibles_no_incluye_las_que_ya_empezaron(db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partidas = servicio(db_session)
    esperando = partidas.crear_partida(ana)
    en_curso = partidas.crear_partida(beto)
    PartidaRepository(db_session).cambiar_estado(en_curso, EstadoPartida.en_curso)

    ids = [p.id for p, _ in partidas.listar_disponibles()]

    assert ids == [esperando.id]


def test_unirse_agrega_al_jugador_y_devuelve_cuantos_hay(db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partidas = servicio(db_session)
    partida = partidas.crear_partida(ana)

    unida, jugadores = partidas.unirse_a_partida(partida.id, beto)

    assert unida.id == partida.id and jugadores == 2
    assert PartidaRepository(db_session).es_participante(partida.id, beto)


def test_unirse_a_una_partida_inexistente(db_session):
    (ana,) = crear_jugadores(db_session, 1)

    with pytest.raises(PartidaNoEncontradaError):
        servicio(db_session).unirse_a_partida(999, ana)


def test_unirse_a_una_partida_que_ya_empezo(db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partidas = servicio(db_session)
    partida = partidas.crear_partida(ana)
    PartidaRepository(db_session).cambiar_estado(partida, EstadoPartida.en_curso)

    with pytest.raises(PartidaNoDisponibleError):
        partidas.unirse_a_partida(partida.id, beto)


def test_unirse_rechaza_a_quien_ya_esta_en_otra_partida_rn04(db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partidas = servicio(db_session)
    partidas.crear_partida(ana)
    de_beto = partidas.crear_partida(beto)

    with pytest.raises(JugadorYaEnPartidaError):
        partidas.unirse_a_partida(de_beto.id, ana)


def test_unirse_a_la_misma_partida_dos_veces_tambien_se_rechaza(db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partidas = servicio(db_session)
    partida = partidas.crear_partida(ana)
    partidas.unirse_a_partida(partida.id, beto)

    with pytest.raises(JugadorYaEnPartidaError):
        partidas.unirse_a_partida(partida.id, beto)


def test_unirse_rechaza_cuando_la_partida_esta_llena(db_session):
    ids = crear_jugadores(db_session, MAX_JUGADORES + 1)
    partidas = servicio(db_session)
    partida = partidas.crear_partida(ids[0])
    for jugador in ids[1:MAX_JUGADORES]:
        partidas.unirse_a_partida(partida.id, jugador)

    with pytest.raises(PartidaLlenaError):
        partidas.unirse_a_partida(partida.id, ids[MAX_JUGADORES])

    assert PartidaRepository(db_session).contar_participantes(partida.id) == MAX_JUGADORES


def test_es_participante_distingue_a_quien_esta_dentro(db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partida = servicio(db_session).crear_partida(ana)
    repo = PartidaRepository(db_session)

    assert repo.es_participante(partida.id, ana)
    assert not repo.es_participante(partida.id, beto)
    assert not repo.es_participante(999, ana)


# endpoints: GET /partidas y POST /partidas/{id}/unirse 


def test_get_partidas_sin_partidas_devuelve_lista_vacia(client):
    respuesta = client.get("/partidas")

    assert respuesta.status_code == 200 and respuesta.json() == []


def test_get_partidas_lista_las_que_esperan_con_su_conteo(client, db_session):
    ana, beto, carla = crear_jugadores(db_session, 3)
    primera = crear_partida_por_api(client, ana)
    segunda = crear_partida_por_api(client, beto)
    unirse_por_api(client, primera, carla)

    respuesta = client.get("/partidas")

    assert respuesta.status_code == 200
    por_id = {p["id"]: p for p in respuesta.json()}
    assert por_id[primera]["jugadores"] == 2
    assert por_id[segunda]["jugadores"] == 1
    assert set(por_id[primera]) == {
        "id",
        "escenario",
        "jugadores",
        "tiempo_limite_segundos",
        "puntuacion_objetivo",
    }


def test_unirse_devuelve_la_partida_con_el_conteo_actualizado(client, db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partida = crear_partida_por_api(client, ana)

    respuesta = unirse_por_api(client, partida, beto)

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == partida and respuesta.json()["jugadores"] == 2


def test_unirse_a_partida_inexistente_da_404(client, db_session):
    (ana,) = crear_jugadores(db_session, 1)

    respuesta = unirse_por_api(client, 999, ana)

    assert respuesta.status_code == 404
    assert "no existe" in respuesta.json()["detail"]


def test_unirse_con_un_jugador_inexistente_da_404(client, db_session):
    (ana,) = crear_jugadores(db_session, 1)
    partida = crear_partida_por_api(client, ana)

    respuesta = unirse_por_api(client, partida, 999)

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Jugador no encontrado"


def test_unirse_a_una_partida_llena_da_409(client, db_session):
    partida, de_mas = llenar_partida(client, db_session)

    respuesta = unirse_por_api(client, partida, de_mas)

    assert respuesta.status_code == 409
    assert "llena" in respuesta.json()["detail"]


def test_unirse_estando_en_otra_partida_da_409_rn04(client, db_session):
    ana, beto = crear_jugadores(db_session, 2)
    crear_partida_por_api(client, ana)
    de_beto = crear_partida_por_api(client, beto)

    respuesta = unirse_por_api(client, de_beto, ana)

    assert respuesta.status_code == 409
    assert "ya está en una partida activa" in respuesta.json()["detail"]


def test_unirse_a_una_partida_en_curso_da_409(client, db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partida = crear_partida_por_api(client, ana)
    repo = PartidaRepository(db_session)
    repo.cambiar_estado(repo.obtener_por_id(partida), EstadoPartida.en_curso)

    respuesta = unirse_por_api(client, partida, beto)

    assert respuesta.status_code == 409
    assert "ya no acepta jugadores" in respuesta.json()["detail"]


def test_unirse_sin_indicar_el_jugador_da_422(client, db_session):
    (ana,) = crear_jugadores(db_session, 1)
    partida = crear_partida_por_api(client, ana)

    respuesta = client.post(f"/partidas/{partida}/unirse", json={})

    assert respuesta.status_code == 422


#canal en tiempo real: /ws/partidas/{id}


def url_del_canal(partida_id, jugador_id):
    return f"/ws/partidas/{partida_id}?jugador_id={jugador_id}"


def partida_de_dos(client, db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partida = crear_partida_por_api(client, ana)
    assert unirse_por_api(client, partida, beto).status_code == 200
    return partida, ana, beto

def siguiente_evento(canal):
    """Lee el siguiente aviso de entrada o salida; el estado de la arena (US-25) se ignora."""
    while True:
        mensaje = canal.receive_json()
        if mensaje["tipo"] != "estado":
            return mensaje


def test_canal_avisa_al_jugador_que_entra(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal_ana:
        assert siguiente_evento(canal_ana) == {
            "tipo": "jugador_conectado",
            "jugador_id": ana,
            "conectados": [ana],
        }


def test_canal_avisa_a_los_demas_cuando_alguien_entra_y_sale(client, db_session):
    partida, ana, beto = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal_ana:
        siguiente_evento(canal_ana)
        with client.websocket_connect(url_del_canal(partida, beto)) as canal_beto:
            entrada = {"tipo": "jugador_conectado", "jugador_id": beto, "conectados": [ana, beto]}
            assert siguiente_evento(canal_ana) == entrada
            assert siguiente_evento(canal_beto) == entrada
        assert siguiente_evento(canal_ana) == {
            "tipo": "jugador_desconectado",
            "jugador_id": beto,
            "conectados": [ana],
        }


def test_canal_rechaza_a_quien_no_esta_en_la_partida(client, db_session):
    ana, beto = crear_jugadores(db_session, 2)
    partida = crear_partida_por_api(client, ana)  # beto no se unió

    with pytest.raises(WebSocketDisconnect) as error, client.websocket_connect(
        url_del_canal(partida, beto)
    ):
        pass

    assert error.value.code == 1008
    assert manager.conectados(partida) == []


def test_canal_rechaza_una_partida_inexistente(client, db_session):
    (ana,) = crear_jugadores(db_session, 1)

    with pytest.raises(WebSocketDisconnect) as error, client.websocket_connect(
        url_del_canal(999, ana)
    ):
        pass

    assert error.value.code == 1008


def test_canal_rechaza_un_jugador_inexistente(client, db_session):
    (ana,) = crear_jugadores(db_session, 1)
    partida = crear_partida_por_api(client, ana)

    with pytest.raises(WebSocketDisconnect) as error, client.websocket_connect(
        url_del_canal(partida, 999)
    ):
        pass

    assert error.value.code == 1008


def test_canal_reconexion_cierra_la_conexion_anterior(client, db_session):
    partida, ana, _ = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as vieja:
        siguiente_evento(vieja)
        with client.websocket_connect(url_del_canal(partida, ana)) as nueva:
            assert siguiente_evento(nueva)["conectados"] == [ana]
            with pytest.raises(WebSocketDisconnect) as error:
                while True:  # puede haber avisos de estado antes del cierre
                    vieja.receive_json()
            assert error.value.code == 1000


def test_canal_no_deja_conexiones_abiertas_al_terminar(client, db_session):
    partida, ana, beto = partida_de_dos(client, db_session)

    with client.websocket_connect(url_del_canal(partida, ana)) as canal_ana:
        siguiente_evento(canal_ana)
        with client.websocket_connect(url_del_canal(partida, beto)):
            assert manager.conectados(partida) == [ana, beto]

    assert manager.conectados(partida) == []