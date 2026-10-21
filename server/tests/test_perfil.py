import pytest
from fastapi.testclient import TestClient

from app.core.security import ScryptPasswordHasher, crear_token_acceso
from app.db.session import get_session
from app.main import app
from app.models.partida import Partida
from app.models.ranking import RankingGlobal
from app.repositories import PartidaRepository, UsuarioRepository
from app.services.registro_service import RegistroService


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def crear_usuario(db_session, nombre="luis", correo="luis@mail.com"):
    repo = UsuarioRepository(db_session)
    usuario = RegistroService(repo, ScryptPasswordHasher(n=2**10)).registrar(
        nombre, correo, "Secreta123"
    )
    usuario.correo_verificado = True
    return repo.guardar(usuario)


def cabecera(usuario):
    return {"Authorization": f"Bearer {crear_token_acceso(usuario.id, usuario.version_sesion)}"}


def editar(client, usuario, **cambios):
    return client.patch("/perfil", json=cambios, headers=cabecera(usuario))


def test_sin_sesion_no_se_puede_ver_el_perfil(client):
    assert client.get("/perfil").status_code == 401


def test_perfil_de_un_jugador_nuevo(client, db_session):
    usuario = crear_usuario(db_session)

    respuesta = client.get("/perfil", headers=cabecera(usuario))

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["nombre_usuario"] == "luis"
    assert datos["correo"] == "luis@mail.com"
    assert datos["avatar"] == "azul"
    assert datos["descripcion"] == ""
    assert not datos["con_google"]
    assert (datos["partidas_jugadas"], datos["victorias"], datos["puntos_totales"]) == (0, 0, 0)


def test_el_perfil_muestra_las_estadisticas(client, db_session):
    usuario = crear_usuario(db_session)
    partidas = PartidaRepository(db_session)
    for _ in range(3):
        partidas.agregar_participante(partidas.crear(Partida()).id, usuario.id)
    db_session.add(RankingGlobal(jugador_id=usuario.id, puntos_totales=850, victorias=2))
    db_session.commit()

    datos = client.get("/perfil", headers=cabecera(usuario)).json()

    assert datos["partidas_jugadas"] == 3
    assert datos["victorias"] == 2
    assert datos["puntos_totales"] == 850


def test_editar_descripcion_y_avatar(client, db_session):
    usuario = crear_usuario(db_session)

    respuesta = editar(client, usuario, descripcion="  Me gusta ganar  ", avatar="verde")

    assert respuesta.status_code == 200
    assert respuesta.json()["descripcion"] == "Me gusta ganar"
    assert respuesta.json()["avatar"] == "verde"
    assert client.get("/perfil", headers=cabecera(usuario)).json()["avatar"] == "verde"


def test_cambiar_el_nombre_de_usuario(client, db_session):
    usuario = crear_usuario(db_session)

    respuesta = editar(client, usuario, nombre_usuario="luis_07")

    assert respuesta.json()["nombre_usuario"] == "luis_07"
    login = {"usuario": "luis_07", "contrasena": "Secreta123"}
    assert client.post("/auth/login", json=login).status_code == 200


def test_no_se_puede_usar_un_nombre_ocupado(client, db_session):
    usuario = crear_usuario(db_session)
    crear_usuario(db_session, "ana", "ana@mail.com")

    respuesta = editar(client, usuario, nombre_usuario="ana")

    assert respuesta.status_code == 409
    db_session.refresh(usuario)
    assert usuario.nombre_usuario == "luis"


def test_dejar_el_mismo_nombre_no_da_error(client, db_session):
    usuario = crear_usuario(db_session)

    assert editar(client, usuario, nombre_usuario="luis").status_code == 200


def test_sin_cambios_no_pasa_nada(client, db_session):
    usuario = crear_usuario(db_session)

    respuesta = editar(client, usuario)

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre_usuario"] == "luis"


@pytest.mark.parametrize(
    "cambios",
    [
        {"avatar": "dorado"},
        {"descripcion": "x" * 201},
        {"nombre_usuario": "lu"},
        {"nombre_usuario": "con espacio"},
    ],
)
def test_datos_invalidos_devuelven_422(client, db_session, cambios):
    usuario = crear_usuario(db_session)

    assert editar(client, usuario, **cambios).status_code == 422
