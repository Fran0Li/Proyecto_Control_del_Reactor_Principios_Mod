"""Pruebas de src.api_client con la red simulada (sin servidor)."""

import asyncio

import pytest

from src import api_client
from src.red import ErrorDeRed, Respuesta


def con_respuesta(monkeypatch, respuesta=None, error=None):
    llamadas = []

    async def falsa(metodo, url, cuerpo=None, timeout=5.0):
        llamadas.append((metodo, url, cuerpo))
        if error:
            raise error
        return respuesta

    monkeypatch.setattr(api_client, "solicitar", falsa)
    return llamadas


def test_registro_exitoso_envia_los_datos(monkeypatch):
    llamadas = con_respuesta(monkeypatch, Respuesta(201, {"id": 7}))
    datos = asyncio.run(api_client.registrar_usuario("luis", "l@mail.com", "Secreta123"))
    assert datos == {"id": 7}
    metodo, url, cuerpo = llamadas[0]
    assert metodo == "POST" and url.endswith("/auth/registro")
    assert cuerpo == {"nombre_usuario": "luis", "correo": "l@mail.com", "contrasena": "Secreta123"}


def test_error_con_detalle_texto(monkeypatch):
    con_respuesta(monkeypatch, Respuesta(409, {"detail": "El correo ya está registrado"}))
    with pytest.raises(api_client.ApiError, match="El correo ya está registrado"):
        asyncio.run(api_client.registrar_usuario("luis", "l@mail.com", "Secreta123"))


def test_error_422_de_fastapi(monkeypatch):
    detalle = [{"msg": "Value error, La contraseña es muy corta"}]
    con_respuesta(monkeypatch, Respuesta(422, {"detail": detalle}))
    with pytest.raises(api_client.ApiError, match="^La contraseña es muy corta$"):
        asyncio.run(api_client.crear_partida(1))


def test_error_sin_json(monkeypatch):
    con_respuesta(monkeypatch, Respuesta(500, None))
    with pytest.raises(api_client.ApiError, match="Error 500"):
        asyncio.run(api_client.crear_partida(1))


def test_sin_conexion(monkeypatch):
    con_respuesta(monkeypatch, error=ErrorDeRed("connection refused"))
    with pytest.raises(api_client.ApiError, match="Sin conexión"):
        asyncio.run(api_client.crear_partida(1, "laboratorio"))


@pytest.mark.parametrize(
    ("respuesta", "error", "texto"),
    [
        (Respuesta(200, {"status": "ok"}), None, "Servidor: conectado"),
        (Respuesta(503, None), None, "Servidor: error"),
        (None, ErrorDeRed("x"), "Servidor: sin conexión"),
    ],
)
def test_estado_servidor(monkeypatch, respuesta, error, texto):
    con_respuesta(monkeypatch, respuesta, error)
    assert asyncio.run(api_client.estado_servidor()) == texto
