import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_session
from app.main import app as fastapi_app
from app.models.partida import EstadoPartida
from app.models.usuario import Usuario
from app.repositories import PartidaRepository, UsuarioRepository
from app.services.partida_factory import ESCENARIOS, PartidaFactory
from app.services.partida_service import JugadorYaEnPartidaError, PartidaService


def crear_usuario(db_session, nombre="ana", correo="ana@mail.com"):
    usuario = Usuario(nombre_usuario=nombre, correo=correo, contrasena_hash="hash")
    return UsuarioRepository(db_session).crear(usuario)


# --- Factory ---


def test_factory_crea_partida_en_esperando():
    partida = PartidaFactory().crear()

    assert partida.estado == EstadoPartida.esperando
    assert partida.tiempo_limite_segundos > 0
    assert partida.puntuacion_objetivo > 0


def test_factory_usa_el_escenario_indicado():
    partida = PartidaFactory().crear("laboratorio")

    assert partida.escenario == "laboratorio"


def test_factory_elige_un_escenario_del_catalogo_si_no_se_indica():
    partida = PartidaFactory().crear()

    assert partida.escenario in ESCENARIOS


def test_factory_rechaza_un_escenario_invalido():
    with pytest.raises(ValueError):
        PartidaFactory().crear("marte")


# --- Servicio ---


def test_servicio_crea_la_partida_y_agrega_al_creador(db_session):
    jugador = crear_usuario(db_session)
    servicio = PartidaService(PartidaRepository(db_session))

    partida = servicio.crear_partida(jugador.id)

    participaciones = PartidaRepository(db_session).listar_participaciones(partida.id)
    assert partida.id is not None
    assert [p.jugador_id for p in participaciones] == [jugador.id]


def test_servicio_rechaza_a_un_jugador_en_partida_activa_rn04(db_session):
    jugador = crear_usuario(db_session)
    servicio = PartidaService(PartidaRepository(db_session))
    servicio.crear_partida(jugador.id)

    with pytest.raises(JugadorYaEnPartidaError):
        servicio.crear_partida(jugador.id)


def test_servicio_permite_crear_otra_si_la_anterior_finalizo(db_session):
    jugador = crear_usuario(db_session)
    repo = PartidaRepository(db_session)
    servicio = PartidaService(repo)
    primera = servicio.crear_partida(jugador.id)
    repo.cambiar_estado(primera, EstadoPartida.finalizada)

    segunda = servicio.crear_partida(jugador.id)

    assert segunda.id != primera.id


# --- Endpoint ---


@pytest.fixture()
def api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sesiones = sessionmaker(bind=engine, expire_on_commit=False)

    def sesion_de_prueba():
        sesion = sesiones()
        try:
            yield sesion
        finally:
            sesion.close()

    fastapi_app.dependency_overrides[get_session] = sesion_de_prueba
    with sesiones() as sesion:
        crear_usuario(sesion)
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_post_partidas_crea_la_partida(api):
    respuesta = api.post("/partidas", json={"creador_id": 1})

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"] == 1
    assert cuerpo["estado"] == "esperando"
    assert cuerpo["escenario"] in ESCENARIOS


def test_post_partidas_con_escenario_indicado(api):
    datos = {"creador_id": 1, "escenario": "laboratorio"}
    respuesta = api.post("/partidas", json=datos)

    assert respuesta.status_code == 201
    assert respuesta.json()["escenario"] == "laboratorio"


def test_post_partidas_jugador_inexistente_da_404(api):
    respuesta = api.post("/partidas", json={"creador_id": 99})

    assert respuesta.status_code == 404


def test_post_partidas_jugador_en_partida_activa_da_409(api):
    api.post("/partidas", json={"creador_id": 1})

    respuesta = api.post("/partidas", json={"creador_id": 1})

    assert respuesta.status_code == 409


def test_post_partidas_escenario_invalido_da_422(api):
    respuesta = api.post("/partidas", json={"creador_id": 1, "escenario": "marte"})

    assert respuesta.status_code == 422