"""Administra los WebSockets conectados a cada partida."""

from contextlib import suppress

from fastapi import WebSocket, status


class ConnectionManager:
    def __init__(self) -> None:
        # partida_id -> {jugador_id -> websocket}
        self._canales: dict[int, dict[int, WebSocket]] = {}

    async def conectar(
        self, partida_id: int, jugador_id: int, websocket: WebSocket
    ) -> None:
        await websocket.accept()
        canal = self._canales.setdefault(partida_id, {})
        anterior = canal.get(jugador_id)
        canal[jugador_id] = websocket
        if anterior is not None:
            # Reconexión: la conexión vieja se cierra y la nueva la reemplaza.
            with suppress(Exception):
                await anterior.close(code=status.WS_1000_NORMAL_CLOSURE)

    def desconectar(
        self, partida_id: int, jugador_id: int, websocket: WebSocket
    ) -> bool:
        """Quita la conexión. Devuelve False si ya había sido reemplazada."""
        canal = self._canales.get(partida_id, {})
        if canal.get(jugador_id) is not websocket:
            return False
        del canal[jugador_id]
        if not canal:
            self._canales.pop(partida_id, None)
        return True

    def conectados(self, partida_id: int) -> list[int]:
        return sorted(self._canales.get(partida_id, {}))

    async def difundir(self, partida_id: int, mensaje: dict) -> None:
        """Envía un mensaje a todos los conectados de la partida."""
        canal = self._canales.get(partida_id, {})
        for jugador_id, websocket in list(canal.items()):
            try:
                await websocket.send_json(mensaje)
            except Exception:  # conexión caída: se descarta sin afectar a los demás
                self.desconectar(partida_id, jugador_id, websocket)


manager = ConnectionManager()