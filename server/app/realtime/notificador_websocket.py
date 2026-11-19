"""Observador que envía lo que pasa en la partida a los clientes conectados por WebSocket."""

from app.realtime.connection_manager import ConnectionManager
from app.realtime.eventos import (
    ESTADO_ACTUALIZADO,
    PARTIDA_FINALIZADA,
    PARTIDA_INICIADA,
    EventoPartida,
)


class NotificadorWebSocket:
    def __init__(self, canales: ConnectionManager) -> None:
        self._canales = canales

    async def al_evento(self, evento: EventoPartida) -> None:
        if evento.tipo == ESTADO_ACTUALIZADO:
            await self._canales.difundir(evento.partida_id, {"tipo": "estado", **evento.datos})
        elif evento.tipo in (PARTIDA_INICIADA, PARTIDA_FINALIZADA):
            # el cliente cambia de pantalla con estos: a la arena y a la ceremonia (US-17)
            await self._canales.difundir(evento.partida_id, {"tipo": evento.tipo, **evento.datos})
