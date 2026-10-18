"""Canal en tiempo real de una partida (WebSocket, US-08).

Usa la conexión de `src.red`, que tiene una implementación para escritorio y otra para el
navegador (ADR 0002). Los mensajes llegan a una cola y la pantalla los lee con `leer_mensajes()`
en cada cuadro, sin bloquear.
"""

from collections.abc import Callable

from src.config import SERVER_URL
from src.red import Conexion, crear_conexion


def url_del_canal(partida_id: int, jugador_id: int) -> str:
    base = SERVER_URL.replace("http", "ws", 1)  # http -> ws, https -> wss
    # Provisional: el jugador va en la URL hasta que exista el login con JWT (el contrato
    # prevé `?token=`).
    return f"{base}/ws/partidas/{partida_id}?jugador_id={jugador_id}"


class CanalPartida:
    def __init__(
        self,
        partida_id: int,
        jugador_id: int,
        fabrica: Callable[[str], Conexion] = crear_conexion,
    ) -> None:
        self._conexion = fabrica(url_del_canal(partida_id, jugador_id))

    @property
    def estado(self) -> str:
        return self._conexion.estado

    @property
    def conectado(self) -> bool:
        return self.estado == "abierta"

    async def conectar(self) -> None:
        await self._conexion.conectar()

    def enviar(self, mensaje: dict) -> None:
        self._conexion.enviar(mensaje)

    def leer_mensajes(self) -> list[dict]:
        return self._conexion.recibir()

    def cerrar(self) -> None:
        self._conexion.cerrar()