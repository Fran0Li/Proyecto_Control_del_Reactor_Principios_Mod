"""Conexión WebSocket con dos implementaciones: escritorio y navegador (pygbag).

El resto del cliente solo usa la interfaz común (conectar, enviar, recibir, estado), así que
no sabe en qué plataforma corre.
"""

import asyncio
import json
import sys
from collections import deque

EN_NAVEGADOR = sys.platform == "emscripten"


class Conexion:
    """Interfaz común."""

    estado: str = "desconectada"

    async def conectar(self) -> None:
        raise NotImplementedError

    def enviar(self, mensaje: dict) -> None:
        raise NotImplementedError

    def recibir(self) -> list[dict]:
        """Devuelve los mensajes que llegaron desde la última llamada (no bloquea)."""
        raise NotImplementedError


class ConexionEscritorio(Conexion):
    """PC: usa la librería websockets en una tarea de asyncio."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._ws = None
        self._entrantes: deque[dict] = deque()

    async def conectar(self) -> None:
        asyncio.create_task(self._bucle())

    async def _bucle(self) -> None:
        import websockets  # solo existe en escritorio

        self.estado = "conectando"
        try:
            async with websockets.connect(self.url) as ws:
                self._ws = ws
                self.estado = "abierta"
                async for texto in ws:
                    self._entrantes.append(json.loads(texto))
        except Exception as error:  # noqa: BLE001
            self.estado = f"error: {error.__class__.__name__}"
        finally:
            self._ws = None
            if self.estado == "abierta":
                self.estado = "cerrada"

    def enviar(self, mensaje: dict) -> None:
        if self._ws is not None:
            asyncio.create_task(self._ws.send(json.dumps(mensaje)))

    def recibir(self) -> list[dict]:
        mensajes = list(self._entrantes)
        self._entrantes.clear()
        return mensajes


class ConexionNavegador(Conexion):
    """Navegador: usa el WebSocket nativo de JavaScript.

    JavaScript guarda los mensajes en una cola y Python la vacía en cada frame. Así se evitan
    los callbacks de JS hacia Python, que son lo más frágil de pygbag.
    """

    def __init__(self, url: str) -> None:
        import platform  # en pygbag, "platform" da acceso a window

        self.url = url
        self._window = platform.window

    async def conectar(self) -> None:
        self._window.eval(
            "window.__cr = {cola: [], estado: 'conectando'};"
            f"window.__cr.ws = new WebSocket({json.dumps(self.url)});"
            "window.__cr.ws.onopen = () => { window.__cr.estado = 'abierta'; };"
            "window.__cr.ws.onclose = () => { window.__cr.estado = 'cerrada'; };"
            "window.__cr.ws.onerror = () => { window.__cr.estado = 'error'; };"
            "window.__cr.ws.onmessage = (e) => { window.__cr.cola.push(e.data); };"
        )

    @property
    def estado(self) -> str:  # type: ignore[override]
        return str(self._window.eval("window.__cr ? window.__cr.estado : 'desconectada'"))

    def enviar(self, mensaje: dict) -> None:
        texto = json.dumps(json.dumps(mensaje))  # doble: queda como literal de JS
        self._window.eval(
            "if (window.__cr && window.__cr.ws.readyState === 1)"
            f" {{ window.__cr.ws.send({texto}); }}"
        )

    def recibir(self) -> list[dict]:
        js = "JSON.stringify(window.__cr ? window.__cr.cola.splice(0) : [])"
        texto = str(self._window.eval(js))
        return [json.loads(m) for m in json.loads(texto)]


def url_del_servidor(puerto: int = 8002, ruta: str = "/ws/eco") -> str:
    """En el navegador usa el mismo host desde el que se cargó la página.

    Se puede cambiar con ?servidor=host:puerto en la URL.
    En escritorio usa la variable de entorno SERVIDOR o localhost.
    """
    if EN_NAVEGADOR:
        import platform

        ubicacion = platform.window.location
        busqueda = str(ubicacion.search)
        if "servidor=" in busqueda:
            destino = busqueda.split("servidor=", 1)[1].split("&", 1)[0]
        else:
            destino = f"{ubicacion.hostname}:{puerto}"
        esquema = "wss" if str(ubicacion.protocol) == "https:" else "ws"
        return f"{esquema}://{destino}{ruta}"
    import os

    return f"ws://{os.getenv('SERVIDOR', f'localhost:{puerto}')}{ruta}"


def crear_conexion(url: str) -> Conexion:
    return ConexionNavegador(url) if EN_NAVEGADOR else ConexionEscritorio(url)
