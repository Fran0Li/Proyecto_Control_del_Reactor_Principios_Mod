"""Conexión en tiempo real del cliente con el canal de una partida (WebSocket)."""

import json
import queue
import threading

import websocket

from src.config import SERVER_URL


class CanalPartida:
    """Se conecta al canal de una partida sin bloquear el bucle de Pygame.

    La conexión vive en un hilo aparte. Los mensajes que llegan se guardan en
    una cola y el juego los lee con `leer_mensajes()` en cada cuadro.
    """

    def __init__(self, partida_id: int, jugador_id: int) -> None:
        base = SERVER_URL.replace("http", "ws", 1)
        self.url = f"{base}/ws/partidas/{partida_id}?jugador_id={jugador_id}"
        self.conectado = False
        self._mensajes: queue.Queue[dict] = queue.Queue()
        self._ws = websocket.WebSocketApp(
            self.url,
            on_open=self._al_abrir,
            on_message=self._al_recibir,
            on_close=self._al_cerrar,
        )

    def conectar(self) -> None:
        hilo = threading.Thread(target=self._ws.run_forever, daemon=True)
        hilo.start()

    def enviar(self, mensaje: dict) -> None:
        if self.conectado:
            self._ws.send(json.dumps(mensaje))

    def leer_mensajes(self) -> list[dict]:
        mensajes = []
        while not self._mensajes.empty():
            mensajes.append(self._mensajes.get_nowait())
        return mensajes

    def cerrar(self) -> None:
        self._ws.close()

    def _al_abrir(self, _ws) -> None:
        self.conectado = True

    def _al_recibir(self, _ws, texto: str) -> None:
        self._mensajes.put(json.loads(texto))

    def _al_cerrar(self, _ws, _codigo, _motivo) -> None:
        self.conectado = False