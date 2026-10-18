"""WebSocket del cliente: una implementación para escritorio y otra para el navegador (ADR 0002).

El resto del cliente solo usa la interfaz común (`conectar`, `enviar`, `recibir`, `cerrar`,
`estado`), así que no sabe en qué plataforma corre. Es la misma interfaz del prototipo
`prototipos/cliente-movil/red.py`.

Estados posibles de `estado`: "desconectada", "conectando", "abierta", "cerrada" y
"error: <motivo>" (solo en escritorio).
"""

import asyncio
import json
from collections import deque
from contextlib import suppress

from .http import EN_NAVEGADOR


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

    def cerrar(self) -> None:
        raise NotImplementedError


class ConexionEscritorio(Conexion):
    """PC: usa la librería `websockets` dentro de una tarea de asyncio."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._ws = None
        self._tarea: asyncio.Task | None = None
        self._envios: set[asyncio.Task] = set()  # evita que se descarten envíos en curso
        self._entrantes: deque[dict] = deque()

    async def conectar(self) -> None:
        self.estado = "conectando"
        self._tarea = asyncio.create_task(self._bucle())

    async def _bucle(self) -> None:
        import websockets  # solo existe en escritorio: pygbag no debe intentar instalarla

        try:
            async with websockets.connect(self.url) as ws:
                self._ws = ws
                self.estado = "abierta"
                async for texto in ws:
                    with suppress(ValueError):  # un mensaje que no es JSON se ignora
                        self._entrantes.append(json.loads(texto))
        except Exception as error:  # el servidor rechazó la conexión o se cayó
            self.estado = f"error: {error.__class__.__name__}"
        finally:
            self._ws = None
            if self.estado == "abierta":
                self.estado = "cerrada"

    def enviar(self, mensaje: dict) -> None:
        if self._ws is not None:
            envio = asyncio.create_task(self._ws.send(json.dumps(mensaje)))
            self._envios.add(envio)
            envio.add_done_callback(self._envios.discard)

    def recibir(self) -> list[dict]:
        mensajes = list(self._entrantes)
        self._entrantes.clear()
        return mensajes

    def cerrar(self) -> None:
        if self._tarea is not None:
            self._tarea.cancel()  # al salir de `async with` se cierra la conexión
        self.estado = "cerrada"


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
            "(function () {"
            "  if (window.__cr && window.__cr.ws) { window.__cr.ws.close(); }"
            "  const cr = {cola: [], estado: 'conectando'};"
            "  window.__cr = cr;"
            f"  cr.ws = new WebSocket({json.dumps(self.url)});"
            "  cr.ws.onopen = () => { cr.estado = 'abierta'; };"
            "  cr.ws.onclose = () => { cr.estado = 'cerrada'; };"
            "  cr.ws.onerror = () => { cr.estado = 'error'; };"
            "  cr.ws.onmessage = (e) => { cr.cola.push(e.data); };"
            "})()"
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

    def cerrar(self) -> None:
        self._window.eval("if (window.__cr && window.__cr.ws) { window.__cr.ws.close(); }")


def crear_conexion(url: str) -> Conexion:
    return ConexionNavegador(url) if EN_NAVEGADOR else ConexionEscritorio(url)