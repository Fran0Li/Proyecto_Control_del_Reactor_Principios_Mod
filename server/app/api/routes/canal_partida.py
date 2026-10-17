"""Canal en tiempo real de una partida (WebSocket, US-08)."""

from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.realtime.connection_manager import manager
from app.repositories import PartidaRepository
from app.services.partida_service import PartidaService

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


def _evento(tipo: str, partida_id: int, jugador_id: int) -> dict:
    return {
        "tipo": tipo,
        "jugador_id": jugador_id,
        "conectados": manager.conectados(partida_id),
    }


@router.websocket("/ws/partidas/{partida_id}")
async def canal_partida(
    websocket: WebSocket,
    partida_id: int,
    jugador_id: int,
    db: SessionDep,
) -> None:
    servicio = PartidaService(PartidaRepository(db))
    autorizado = servicio.es_participante(partida_id, jugador_id)
    db.close()  # no retener la conexión a la base mientras dure el WebSocket
    if not autorizado:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.conectar(partida_id, jugador_id, websocket)
    await manager.difundir(
        partida_id, _evento("jugador_conectado", partida_id, jugador_id)
    )
    try:
        while True:
            # Por ahora solo mantiene el canal abierto. US-25 recibirá aquí
            # los comandos de movimiento.
            await websocket.receive_text()
    except WebSocketDisconnect:
        if manager.desconectar(partida_id, jugador_id, websocket):
            await manager.difundir(
                partida_id, _evento("jugador_desconectado", partida_id, jugador_id)
            )