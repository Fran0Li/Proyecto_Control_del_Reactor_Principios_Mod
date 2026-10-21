from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import (
    ScryptPasswordHasher,
    TokenInvalidoError,
    crear_token_acceso,
    leer_token_acceso,
)
from app.core.tiempo import ahora_utc
from app.db.session import get_session
from app.main import app
from app.repositories import UsuarioRepository
from app.services.login_service import MAX_INTENTOS
from app.services.registro_service import RegistroService


def crear_usuario(db_session, verificado=True):
    repo = UsuarioRepository(db_session)
    servicio = RegistroService(repo, ScryptPasswordHasher(n=2**10))
    usuario = servicio.registrar("luis", "luis@mail.com", "Secreta123")
    usuario.correo_verificado = verificado
    return repo.guardar(usuario)


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def login(client, usuario="luis", contrasena="Secreta123"):
    return client.post("/auth/login", json={"usuario": usuario, "contrasena": contrasena})


def test_login_con_nombre_de_usuario_devuelve_el_token(client, db_session):
    crear_usuario(db_session)

    respuesta = login(client)

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["token_type"] == "bearer"
    assert datos["usuario"]["nombre_usuario"] == "luis"
    assert leer_token_acceso(datos["access_token"]) == (datos["usuario"]["id"], 0)


def test_login_con_el_correo_en_mayusculas(client, db_session):
    crear_usuario(db_session)

    assert login(client, usuario="LUIS@Mail.com").status_code == 200


def test_contrasena_incorrecta_devuelve_401(client, db_session):
    crear_usuario(db_session)

    respuesta = login(client, contrasena="Otra12345")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario o contraseña incorrectos"


def test_usuario_que_no_existe_da_el_mismo_mensaje(client):
    respuesta = login(client, usuario="nadie")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario o contraseña incorrectos"


def test_correo_sin_verificar_no_puede_entrar(client, db_session):
    crear_usuario(db_session, verificado=False)

    respuesta = login(client)

    assert respuesta.status_code == 403
    assert "Verificá tu correo" in respuesta.json()["detail"]


def test_se_bloquea_despues_de_varios_intentos_fallidos(client, db_session):
    crear_usuario(db_session)

    for _ in range(MAX_INTENTOS - 1):
        assert login(client, contrasena="Mala12345").status_code == 401

    assert login(client, contrasena="Mala12345").status_code == 423
    # bloqueada, ni con la contraseña correcta entra
    respuesta = login(client)
    assert respuesta.status_code == 423
    assert "min" in respuesta.json()["detail"]


def test_cuando_vence_el_bloqueo_puede_entrar(client, db_session):
    usuario = crear_usuario(db_session)
    usuario.bloqueado_hasta = ahora_utc() - timedelta(minutes=1)
    UsuarioRepository(db_session).guardar(usuario)

    assert login(client).status_code == 200


def test_login_exitoso_reinicia_los_intentos(client, db_session):
    usuario = crear_usuario(db_session)
    login(client, contrasena="Mala12345")
    login(client, contrasena="Mala12345")

    login(client)

    db_session.refresh(usuario)
    assert usuario.intentos_fallidos == 0


def test_yo_devuelve_el_usuario_de_la_sesion(client, db_session):
    crear_usuario(db_session)
    token = login(client).json()["access_token"]

    respuesta = client.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre_usuario"] == "luis"


def test_yo_sin_token_devuelve_401(client):
    assert client.get("/auth/yo").status_code == 401


def test_yo_con_token_alterado_devuelve_401(client, db_session):
    crear_usuario(db_session)
    token = login(client).json()["access_token"]

    respuesta = client.get("/auth/yo", headers={"Authorization": f"Bearer {token}x"})

    assert respuesta.status_code == 401


def test_token_vencido_no_sirve():
    vencido = jwt.encode(
        {"sub": "1", "ver": 0, "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret,
        "HS256",
    )

    with pytest.raises(TokenInvalidoError):
        leer_token_acceso(vencido)


def test_crear_y_leer_token():
    assert leer_token_acceso(crear_token_acceso(7, 2)) == (7, 2)
