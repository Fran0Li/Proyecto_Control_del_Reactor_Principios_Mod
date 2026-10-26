"""Observador que envía el estado de la partida a los clientes conectados por WebSocket."""

from app.realtime.connection_manager import ConnectionManager
from app.realtime.eventos import ESTADO_ACTUALIZADO, EventoPartida


class NotificadorWebSocket:
    def __init__(self, canales: ConnectionManager) -> None:
        self._canales = canales

    async def al_evento(self, evento: EventoPartida) -> None:
        if evento.tipo == ESTADO_ACTUALIZADO:
            await self._canales.difundir(evento.partida_id, {"tipo": "estado", **evento.datos})