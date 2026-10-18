"""Pruebas del canal de la partida (src.realtime_client) con una conexión simulada."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from src import realtime_client
from src.realtime_client import CanalPartida, url_del_canal
from src.red import Conexion

RAIZ_CLIENTE = Path(__file__).resolve().parents[1]


class ConexionFalsa(Conexion):
    def __init__(self, url):
        self.url = url
        self.entrantes = []
        self.enviados = []

    async def conectar(self):
        self.estado = "abierta"

    def enviar(self, mensaje):
        self.enviados.append(mensaje)

    def recibir(self):
        mensajes, self.entrantes = self.entrantes, []
        return mensajes

    def cerrar(self):
        self.estado = "cerrada"


def test_url_del_canal_usa_ws_con_http(monkeypatch):
    monkeypatch.setattr(realtime_client, "SERVER_URL", "http://localhost:8000")
    assert url_del_canal(3, 7) == "ws://localhost:8000/ws/partidas/3?jugador_id=7"


def test_url_del_canal_usa_wss_con_https(monkeypatch):
    monkeypatch.setattr(realtime_client, "SERVER_URL", "https://juego.ejemplo.com")
    assert url_del_canal(3, 7) == "wss://juego.ejemplo.com/ws/partidas/3?jugador_id=7"


def test_el_canal_pide_la_conexion_con_la_url_correcta():
    creadas = []

    def fabrica(url):
        conexion = ConexionFalsa(url)
        creadas.append(conexion)
        return conexion

    CanalPartida(3, 7, fabrica=fabrica)
    assert creadas[0].url.endswith("/ws/partidas/3?jugador_id=7")


def test_el_canal_refleja_el_estado_de_la_conexion():
    canal = CanalPartida(1, 1, fabrica=ConexionFalsa)
    assert not canal.conectado and canal.estado == "desconectada"
    asyncio.run(canal.conectar())
    assert canal.conectado
    canal.cerrar()
    assert not canal.conectado and canal.estado == "cerrada"


def test_el_canal_entrega_los_mensajes_y_envia_los_del_juego():
    canal = CanalPartida(1, 1, fabrica=ConexionFalsa)
    canal._conexion.entrantes = [{"tipo": "jugador_conectado", "conectados": [1, 2]}]
    assert canal.leer_mensajes() == [{"tipo": "jugador_conectado", "conectados": [1, 2]}]
    assert canal.leer_mensajes() == []  # ya se entregaron
    canal.enviar({"tipo": "entrada"})
    assert canal._conexion.enviados == [{"tipo": "entrada"}]


def test_cargar_las_pantallas_no_importa_librerias_de_escritorio():
    """pygbag no debe intentar instalar `requests` ni `websockets` (ADR 0002, regla 5)."""
    codigo = (
        "import sys\n"
        "import src.screens.lobby, src.screens.buscar_partida, src.realtime_client\n"
        "print(','.join(m for m in ('requests', 'websockets', 'serial') if m in sys.modules))\n"
    )
    entorno = {
        **os.environ,
        "SDL_VIDEODRIVER": "dummy",
        "SDL_AUDIODRIVER": "dummy",
        "PYGAME_HIDE_SUPPORT_PROMPT": "1",  # sin el mensaje de bienvenida de pygame
    }
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        capture_output=True,
        text=True,
        cwd=RAIZ_CLIENTE,
        env=entorno,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == ""