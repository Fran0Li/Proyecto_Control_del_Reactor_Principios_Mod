import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app

DATOS_VALIDOS = {
    "nombre_usuario": "luis",
    "correo": "luis@mail.com",
    "contrasena": "Secreta123",
}


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def registrar(client, **cambios):
    return client.post("/auth/registro", json={**DATOS_VALIDOS, **cambios})


def test_registro_exitoso_devuelve_201_y_cuenta_sin_verificar(client):
    respuesta = registrar(client)

    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["nombre_usuario"] == "luis"
    assert datos["correo"] == "luis@mail.com"
    assert datos["correo_verificado"] is False


def test_la_respuesta_no_expone_la_contrasena(client):
    datos = registrar(client).json()

    assert "contrasena" not in datos
    assert "contrasena_hash" not in datos


def test_correo_duplicado_devuelve_409(client):
    registrar(client)

    respuesta = registrar(client, nombre_usuario="otro")

    assert respuesta.status_code == 409
    assert "correo" in respuesta.json()["detail"]


def test_nombre_de_usuario_duplicado_devuelve_409(client):
    registrar(client)

    respuesta = registrar(client, correo="otro@mail.com")

    assert respuesta.status_code == 409
    assert "usuario" in respuesta.json()["detail"]


@pytest.mark.parametrize(
    "cambios",
    [
        {"correo": "sin-arroba.com"},
        {"correo": "luis@mail"},
        {"contrasena": "Corta1"},
        {"contrasena": "sololetras"},
        {"contrasena": "12345678"},
        {"nombre_usuario": "lu"},
        {"nombre_usuario": "con espacios"},
    ],
)
def test_datos_invalidos_devuelven_422(client, cambios):
    respuesta = registrar(client, **cambios)

    assert respuesta.status_code == 422
