from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.api.routes.auth_google import get_proveedor_google
from app.core.security import ScryptPasswordHasher, leer_token_acceso
from app.db.session import get_session
from app.main import app
from app.repositories import UsuarioRepository
from app.services.google_oauth import GoogleError, PerfilGoogle, ProveedorGoogle
from app.services.registro_service import RegistroService
from app.services.sesiones_google import sesiones_google

SESION = "sesion-de-prueba-123456"
PERFIL = PerfilGoogle(google_id="g-111", correo="luis.serrano@gmail.com", correo_verificado=True)


class ProveedorFalso:
    configurado = True

    def __init__(self):
        self.perfil = PERFIL
        self.error = None

    def url_autorizacion(self, estado):
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={estado}"

    def obtener_perfil(self, codigo):
        if self.error:
            raise self.error
        return self.perfil


@pytest.fixture(autouse=True)
def sin_resultados_guardados():
    sesiones_google._resultados.clear()


@pytest.fixture()
def proveedor():
    return ProveedorFalso()


@pytest.fixture()
def client(db_session, proveedor):
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_proveedor_google] = lambda: proveedor
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def entrar_con_google(client):
    """Simula que Google devuelve al jugador al callback y el juego pide el resultado."""
    client.get("/auth/google/callback", params={"state": SESION, "code": "codigo-de-google"})
    return client.get("/auth/google/resultado", params={"sesion": SESION})


def crear_cuenta_local(db_session, correo="luis.serrano@gmail.com", verificada=True):
    repo = UsuarioRepository(db_session)
    usuario = RegistroService(repo, ScryptPasswordHasher(n=2**10)).registrar(
        "luis", correo, "Secreta123"
    )
    usuario.correo_verificado = verificada
    return repo.guardar(usuario)


def login_con_contrasena(client):
    return client.post("/auth/login", json={"usuario": "luis", "contrasena": "Secreta123"})


def test_iniciar_manda_a_google_con_la_sesion(client):
    respuesta = client.get(
        "/auth/google/iniciar", params={"sesion": SESION}, follow_redirects=False
    )

    assert respuesta.status_code == 307
    assert respuesta.headers["location"].startswith("https://accounts.google.com/")
    assert SESION in respuesta.headers["location"]


def test_iniciar_sin_credenciales_configuradas_avisa(client, proveedor):
    proveedor.configurado = False

    respuesta = client.get("/auth/google/iniciar", params={"sesion": SESION})

    assert respuesta.status_code == 503


def test_sesion_con_formato_raro_se_rechaza(client):
    respuesta = client.get("/auth/google/resultado", params={"sesion": "corta"})

    assert respuesta.status_code == 422


def test_primera_vez_crea_la_cuenta_verificada(client, db_session):
    respuesta = entrar_con_google(client)

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["usuario"]["nombre_usuario"] == "luisserrano"
    assert datos["usuario"]["correo"] == "luis.serrano@gmail.com"
    assert leer_token_acceso(datos["access_token"])[0] == datos["usuario"]["id"]
    usuario = UsuarioRepository(db_session).obtener_por_google_id("g-111")
    assert usuario.correo_verificado
    assert usuario.contrasena_hash is None


def test_antes_de_terminar_en_el_navegador_el_resultado_esta_pendiente(client):
    respuesta = client.get("/auth/google/resultado", params={"sesion": SESION})

    assert respuesta.status_code == 202


def test_el_resultado_se_entrega_una_sola_vez(client):
    entrar_con_google(client)

    respuesta = client.get("/auth/google/resultado", params={"sesion": SESION})

    assert respuesta.status_code == 202


def test_la_segunda_vez_entra_a_la_misma_cuenta(client):
    primera = entrar_con_google(client).json()
    segunda = entrar_con_google(client).json()

    assert primera["usuario"]["id"] == segunda["usuario"]["id"]


def test_si_ya_existe_una_cuenta_con_ese_correo_se_vincula(client, db_session):
    local = crear_cuenta_local(db_session)

    datos = entrar_con_google(client).json()

    assert datos["usuario"]["id"] == local.id
    db_session.refresh(local)
    assert local.google_id == "g-111"
    # la contraseña de antes sigue sirviendo
    assert login_con_contrasena(client).status_code == 200


def test_cuenta_sin_verificar_con_ese_correo_pierde_la_contrasena(client, db_session):
    local = crear_cuenta_local(db_session, verificada=False)

    datos = entrar_con_google(client).json()

    assert datos["usuario"]["id"] == local.id
    db_session.refresh(local)
    assert local.correo_verificado
    assert login_con_contrasena(client).status_code == 401


def test_si_el_nombre_esta_ocupado_se_le_agrega_un_numero(client, db_session):
    repo = UsuarioRepository(db_session)
    RegistroService(repo, ScryptPasswordHasher(n=2**10)).registrar(
        "luisserrano", "otro@mail.com", "Secreta123"
    )

    datos = entrar_con_google(client).json()

    assert datos["usuario"]["nombre_usuario"] == "luisserrano2"


def test_correo_sin_verificar_en_google_no_entra(client, proveedor):
    proveedor.perfil = PerfilGoogle("g-222", "nuevo@gmail.com", correo_verificado=False)

    respuesta = entrar_con_google(client)

    assert respuesta.status_code == 400
    assert "verificado" in respuesta.json()["detail"]


def test_si_el_jugador_cancela_en_google(client):
    client.get("/auth/google/callback", params={"state": SESION, "error": "access_denied"})

    respuesta = client.get("/auth/google/resultado", params={"sesion": SESION})

    assert respuesta.status_code == 400
    assert "canceló" in respuesta.json()["detail"]


def test_si_google_falla(client, proveedor):
    proveedor.error = GoogleError("No se pudo completar el login con Google")

    respuesta = entrar_con_google(client)

    assert respuesta.status_code == 400


def test_cuenta_solo_de_google_no_entra_con_contrasena(client):
    entrar_con_google(client)

    respuesta = client.post(
        "/auth/login", json={"usuario": "luisserrano", "contrasena": "Secreta123"}
    )

    assert respuesta.status_code == 401


def test_url_de_autorizacion_de_google():
    callback = "http://localhost:8000/auth/google/callback"
    proveedor = ProveedorGoogle("id-cliente", "secreto", callback)

    url = urlparse(proveedor.url_autorizacion(SESION))
    parametros = parse_qs(url.query)

    assert url.netloc == "accounts.google.com"
    assert parametros["client_id"] == ["id-cliente"]
    assert parametros["state"] == [SESION]
    assert parametros["redirect_uri"] == [callback]
    assert proveedor.configurado
    assert not ProveedorGoogle("", "", "").configurado
