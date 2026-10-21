import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.dependencias import get_enviador
from app.core.security import ScryptPasswordHasher, generar_codigo, hash_token
from app.core.tiempo import ahora_utc
from app.db.session import get_session
from app.main import app
from app.repositories import TokenRepository, UsuarioRepository
from app.services.registro_service import RegistroService


class EnviadorFalso:
    def __init__(self):
        self.enviados = []

    def enviar(self, destino, asunto, cuerpo):
        self.enviados.append((destino, asunto, cuerpo))

    def ultimo_codigo(self):
        return re.search(r"Tu código es: (\w+)", self.enviados[-1][2]).group(1)


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


def crear_usuario(db_session, nombre="luis", correo="luis@mail.com"):
    repo = UsuarioRepository(db_session)
    usuario = RegistroService(repo, ScryptPasswordHasher(n=2**10)).registrar(
        nombre, correo, "Secreta123"
    )
    usuario.correo_verificado = True
    return repo.guardar(usuario)


def pedir_codigo(client, enviador, correo="luis@mail.com"):
    client.post("/auth/recuperar", json={"correo": correo})
    return enviador.ultimo_codigo()


def restablecer(client, codigo, contrasena="Nueva12345", correo="luis@mail.com"):
    datos = {"correo": correo, "codigo": codigo, "contrasena": contrasena}
    return client.post("/auth/restablecer", json=datos)


def login(client, contrasena):
    return client.post("/auth/login", json={"usuario": "luis", "contrasena": contrasena})


def test_pedir_recuperacion_manda_un_codigo_al_correo(client, enviador, db_session):
    crear_usuario(db_session)

    respuesta = client.post("/auth/recuperar", json={"correo": "LUIS@mail.com"})

    assert respuesta.status_code == 202
    destino, _, _ = enviador.enviados[0]
    assert destino == "luis@mail.com"
    assert len(enviador.ultimo_codigo()) == 8


def test_correo_que_no_existe_responde_igual_y_no_manda_nada(client, enviador):
    respuesta = client.post("/auth/recuperar", json={"correo": "nadie@mail.com"})

    assert respuesta.status_code == 202
    assert enviador.enviados == []


def test_con_el_codigo_se_cambia_la_contrasena(client, enviador, db_session):
    crear_usuario(db_session)
    codigo = pedir_codigo(client, enviador)

    respuesta = restablecer(client, codigo)

    assert respuesta.status_code == 200
    assert login(client, "Nueva12345").status_code == 200
    assert login(client, "Secreta123").status_code == 401


def test_el_codigo_sirve_en_minusculas(client, enviador, db_session):
    crear_usuario(db_session)
    codigo = pedir_codigo(client, enviador)

    assert restablecer(client, f" {codigo.lower()} ").status_code == 200


def test_el_codigo_solo_sirve_una_vez(client, enviador, db_session):
    crear_usuario(db_session)
    codigo = pedir_codigo(client, enviador)
    restablecer(client, codigo)

    respuesta = restablecer(client, codigo, contrasena="Otra12345")

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El código no es válido"


def test_un_codigo_vencido_no_sirve(client, enviador, db_session):
    crear_usuario(db_session)
    codigo = pedir_codigo(client, enviador)
    registro = TokenRepository(db_session).buscar(hash_token(codigo), "recuperacion")
    registro.expira_en = ahora_utc() - timedelta(minutes=1)
    db_session.commit()

    respuesta = restablecer(client, codigo)

    assert respuesta.status_code == 400
    assert "venció" in respuesta.json()["detail"]


def test_el_codigo_de_otra_cuenta_no_sirve(client, enviador, db_session):
    crear_usuario(db_session)
    crear_usuario(db_session, "ana", "ana@mail.com")
    codigo_de_ana = pedir_codigo(client, enviador, "ana@mail.com")

    respuesta = restablecer(client, codigo_de_ana, correo="luis@mail.com")

    assert respuesta.status_code == 400
    assert login(client, "Secreta123").status_code == 200


def test_pedir_otro_codigo_anula_el_anterior(client, enviador, db_session):
    crear_usuario(db_session)
    anterior = pedir_codigo(client, enviador)
    nuevo = pedir_codigo(client, enviador)

    assert restablecer(client, anterior).status_code == 400
    assert restablecer(client, nuevo).status_code == 200


def test_la_contrasena_nueva_debe_cumplir_las_reglas(client, enviador, db_session):
    crear_usuario(db_session)
    codigo = pedir_codigo(client, enviador)

    assert restablecer(client, codigo, contrasena="sololetras").status_code == 422
    assert restablecer(client, codigo, contrasena="Corta1").status_code == 422


def test_cambiar_la_contrasena_cierra_las_sesiones_abiertas(client, enviador, db_session):
    crear_usuario(db_session)
    token = login(client, "Secreta123").json()["access_token"]
    cabecera = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/yo", headers=cabecera).status_code == 200

    restablecer(client, pedir_codigo(client, enviador))

    assert client.get("/auth/yo", headers=cabecera).status_code == 401


def test_cambiar_la_contrasena_desbloquea_la_cuenta(client, enviador, db_session):
    usuario = crear_usuario(db_session)
    usuario.bloqueado_hasta = ahora_utc() + timedelta(minutes=10)
    db_session.commit()

    restablecer(client, pedir_codigo(client, enviador))

    assert login(client, "Nueva12345").status_code == 200


def test_el_codigo_no_tiene_letras_que_se_confunden():
    codigos = "".join(generar_codigo() for _ in range(200))

    assert not set(codigos) & set("O0I1")
