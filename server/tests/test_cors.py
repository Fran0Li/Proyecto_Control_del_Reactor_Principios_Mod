"""El navegador (cliente móvil con pygbag) puede llamar a la API desde otro origen."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ORIGEN_PYGBAG = "http://192.168.1.50:8001"


def test_preflight_de_post_desde_el_navegador():
    respuesta = client.options(
        "/auth/registro",
        headers={
            "Origin": ORIGEN_PYGBAG,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] in ("*", ORIGEN_PYGBAG)


def test_get_incluye_cabecera_cors():
    respuesta = client.get("/health", headers={"Origin": ORIGEN_PYGBAG})
    assert respuesta.status_code == 200
    assert "access-control-allow-origin" in respuesta.headers
