"""Pruebas de la URL del backend que usa la versión web del cliente."""

from src.config import url_backend_web
from src.realtime_client import url_del_canal


def test_en_la_nube_usa_el_mismo_origen_con_api():
    url = url_backend_web(
        "https:", "reactor.eastus.cloudapp.azure.com", "reactor.eastus.cloudapp.azure.com"
    )
    assert url == "https://reactor.eastus.cloudapp.azure.com/api"


def test_en_la_nube_respeta_un_puerto_distinto_de_443():
    assert (
        url_backend_web("https:", "midominio.com:8443", "midominio.com")
        == "https://midominio.com:8443/api"
    )


def test_en_la_red_local_usa_el_puerto_8000():
    assert (
        url_backend_web("http:", "192.168.1.50:8001", "192.168.1.50") == "http://192.168.1.50:8000"
    )


def test_el_websocket_en_la_nube_queda_en_wss_bajo_api(monkeypatch):
    monkeypatch.setattr("src.realtime_client.SERVER_URL", "https://reactor.example.com/api")
    assert url_del_canal(3, "abc") == "wss://reactor.example.com/api/ws/partidas/3?token=abc"
