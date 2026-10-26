"""Prueba la red de escritorio contra un servidor HTTP local de verdad."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.red import ErrorDeRed, solicitar


class Manejador(BaseHTTPRequestHandler):
    def _responder(self, estado, cuerpo):
        datos = json.dumps(cuerpo).encode()
        self.send_response(estado)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):  # noqa: N802 - nombre fijo de http.server
        self._responder(200, {"status": "ok"})

    def do_POST(self):  # noqa: N802
        largo = int(self.headers.get("Content-Length", 0))
        recibido = json.loads(self.rfile.read(largo))
        self._responder(201, {"eco": recibido})

    def log_message(self, *args):
        pass


@pytest.fixture()
def servidor():
    httpd = HTTPServer(("127.0.0.1", 0), Manejador)
    hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_get_y_post(servidor):
    r = asyncio.run(solicitar("GET", f"{servidor}/health"))
    assert r.ok and r.datos == {"status": "ok"}

    r = asyncio.run(solicitar("POST", f"{servidor}/partidas", {"creador_id": 1}))
    assert r.estado == 201 and r.datos == {"eco": {"creador_id": 1}}


def test_no_congela_el_ciclo_mientras_espera(servidor):
    """Mientras se espera la respuesta, otras tareas (los frames) siguen corriendo."""

    async def escenario():
        frames = 0

        async def dibujar():
            nonlocal frames
            while True:
                frames += 1
                await asyncio.sleep(0)

        tarea = asyncio.create_task(dibujar())
        await solicitar("GET", f"{servidor}/health")
        tarea.cancel()
        return frames

    assert asyncio.run(escenario()) > 0


def test_servidor_caido_lanza_error_de_red():
    with pytest.raises(ErrorDeRed):
        asyncio.run(solicitar("GET", "http://127.0.0.1:9/health", timeout=1))
