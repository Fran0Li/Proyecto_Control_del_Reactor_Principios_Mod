from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.security import crear_token_acceso
from app.db.session import get_session
from app.main import app
from app.models.usuario import Usuario
from app.realtime.connection_manager import manager
from app.repositories import UsuarioRepository


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def canales_limpios():
    manager._canales.clear()
    yield
    manager._canales.clear()


@pytest.fixture()
def partida_de_ana(client, db_session):
    """Crea a Ana y una partida suya; devuelve (partida_id, ana)."""
    ana = UsuarioRepository(db_session).crear(
        Usuario(nombre_usuario="ana", correo="ana@mail.com", contrasena_hash="hash")
    )
    respuesta = client.post("/partidas", json={"creador_id": ana.id})
    return respuesta.json()["id"], ana


def conectarse_sin_exito(client, url):
    with pytest.raises(WebSocketDisconnect) as error, client.websocket_connect(url):
        pass
    return error.value.code


def test_con_el_token_de_la_sesion_entra_al_canal(client, partida_de_ana):
    partida, ana = partida_de_ana
    token = crear_token_acceso(ana.id, ana.version_sesion)

    with client.websocket_connect(f"/ws/partidas/{partida}?token={token}") as canal:
        mensaje = canal.receive_json()
        while mensaje["tipo"] == "estado":
            mensaje = canal.receive_json()

    assert mensaje["tipo"] == "jugador_conectado"
    assert mensaje["jugador_id"] == ana.id


def test_sin_token_se_rechaza(client, partida_de_ana):
    partida, _ = partida_de_ana

    assert conectarse_sin_exito(client, f"/ws/partidas/{partida}") == 1008
    assert manager.conectados(partida) == []


def test_con_un_token_inventado_se_rechaza(client, partida_de_ana):
    partida, _ = partida_de_ana

    assert conectarse_sin_exito(client, f"/ws/partidas/{partida}?token=inventado") == 1008


def test_con_un_token_vencido_se_rechaza(client, partida_de_ana):
    partida, ana = partida_de_ana
    vencido = jwt.encode(
        {"sub": str(ana.id), "ver": 0, "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret,
        "HS256",
    )

    assert conectarse_sin_exito(client, f"/ws/partidas/{partida}?token={vencido}") == 1008


def test_con_el_token_de_una_sesion_cerrada_se_rechaza(client, db_session, partida_de_ana):
    partida, ana = partida_de_ana
    token = crear_token_acceso(ana.id, ana.version_sesion)
    ana.version_sesion += 1  # como cuando cambia la contraseña (US-05)
    db_session.commit()

    assert conectarse_sin_exito(client, f"/ws/partidas/{partida}?token={token}") == 1008


def test_ya_no_se_puede_entrar_poniendo_el_jugador_en_la_url(client, partida_de_ana):
    partida, ana = partida_de_ana

    url = f"/ws/partidas/{partida}?jugador_id={ana.id}"
    assert conectarse_sin_exito(client, url) == 1008
