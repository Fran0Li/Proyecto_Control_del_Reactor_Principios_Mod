import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.dependencias import get_enviador
from app.core.security import hash_token
from app.core.tiempo import ahora_utc
from app.db.session import get_session
from app.main import app
from app.repositories import TokenRepository, UsuarioRepository
from app.services.correo import CorreoNoEnviadoError, EnviadorConsola, crear_enviador

DATOS = {"nombre_usuario": "luis", "correo": "luis@mail.com", "contrasena": "Secreta123"}


class EnviadorFalso:
    def __init__(self):
        self.enviados = []
        self.falla = False

    def enviar(self, destino, asunto, cuerpo):
        if self.falla:
            raise CorreoNoEnviadoError("sin conexión")
        self.enviados.append((destino, asunto, cuerpo))

    def ultimo_token(self):
        return re.search(r"token=([\w-]+)", self.enviados[-1][2]).group(1)


@pytest.fixture()
def enviador():
    return EnviadorFalso()


@pytest.fixture()
def client(db_session, enviador):
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_enviador] = lambda: enviador
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def registrar(client):
    return client.post("/auth/registro", json=DATOS)


def usuario(db_session):
    encontrado = UsuarioRepository(db_session).obtener_por_correo("luis@mail.com")
    db_session.refresh(encontrado)
    return encontrado


def test_al_registrarse_llega_un_correo_con_el_enlace(client, enviador):
    registrar(client)

    destino, asunto, cuerpo = enviador.enviados[0]
    assert destino == "luis@mail.com"
    assert "Verificá" in asunto
    assert "/auth/verificar?token=" in cuerpo


def test_abrir_el_enlace_verifica_la_cuenta(client, enviador, db_session):
    registrar(client)

    respuesta = client.get("/auth/verificar", params={"token": enviador.ultimo_token()})

    assert respuesta.status_code == 200
    assert "verificado" in respuesta.text
    assert usuario(db_session).correo_verificado


def test_despues_de_verificar_puede_iniciar_sesion(client, enviador):
    registrar(client)
    login = {"usuario": "luis", "contrasena": "Secreta123"}
    assert client.post("/auth/login", json=login).status_code == 403

    client.get("/auth/verificar", params={"token": enviador.ultimo_token()})

    assert client.post("/auth/login", json=login).status_code == 200


def test_el_enlace_solo_sirve_una_vez(client, enviador):
    registrar(client)
    token = enviador.ultimo_token()
    client.get("/auth/verificar", params={"token": token})

    respuesta = client.get("/auth/verificar", params={"token": token})

    assert respuesta.status_code == 400


def test_un_enlace_inventado_no_sirve(client, db_session):
    registrar(client)

    respuesta = client.get("/auth/verificar", params={"token": "inventado"})

    assert respuesta.status_code == 400
    assert not usuario(db_session).correo_verificado


def test_un_enlace_vencido_no_sirve(client, enviador, db_session):
    registrar(client)
    token = enviador.ultimo_token()
    registro = TokenRepository(db_session).buscar(hash_token(token), "verificacion")
    registro.expira_en = ahora_utc() - timedelta(minutes=1)
    db_session.commit()

    respuesta = client.get("/auth/verificar", params={"token": token})

    assert respuesta.status_code == 400
    assert "vencido" in respuesta.text
    assert not usuario(db_session).correo_verificado


def test_reenviar_manda_otro_enlace_y_el_anterior_deja_de_servir(client, enviador):
    registrar(client)
    anterior = enviador.ultimo_token()

    respuesta = client.post("/auth/reenviar-verificacion", json={"correo": "LUIS@mail.com"})

    assert respuesta.status_code == 202
    nuevo = enviador.ultimo_token()
    assert nuevo != anterior
    assert client.get("/auth/verificar", params={"token": anterior}).status_code == 400
    assert client.get("/auth/verificar", params={"token": nuevo}).status_code == 200


def test_reenviar_a_un_correo_que_no_existe_responde_igual_y_no_manda_nada(client, enviador):
    respuesta = client.post("/auth/reenviar-verificacion", json={"correo": "nadie@mail.com"})

    assert respuesta.status_code == 202
    assert enviador.enviados == []


def test_reenviar_a_una_cuenta_ya_verificada_no_manda_nada(client, enviador):
    registrar(client)
    client.get("/auth/verificar", params={"token": enviador.ultimo_token()})

    client.post("/auth/reenviar-verificacion", json={"correo": "luis@mail.com"})

    assert len(enviador.enviados) == 1


def test_si_falla_el_correo_la_cuenta_igual_se_crea(client, enviador, db_session):
    enviador.falla = True

    respuesta = registrar(client)

    assert respuesta.status_code == 201
    assert usuario(db_session) is not None


def test_si_falla_el_correo_al_reenviar_responde_503(client, enviador):
    registrar(client)
    enviador.falla = True

    respuesta = client.post("/auth/reenviar-verificacion", json={"correo": "luis@mail.com"})

    assert respuesta.status_code == 503


def test_sin_smtp_configurado_se_usa_la_consola(capsys):
    enviador = crear_enviador()
    assert isinstance(enviador, EnviadorConsola)

    enviador.enviar("luis@mail.com", "Hola", "cuerpo del correo")

    assert "luis@mail.com" in capsys.readouterr().out
