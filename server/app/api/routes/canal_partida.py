"""Canal en tiempo real de una partida (WebSocket, US-08 y US-25)."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.api.dependencias import SessionDep, usuario_desde_token
from app.core.security import TokenInvalidoError
from app.realtime.connection_manager import manager
from app.realtime.entradas import EntradaInvalida, FiltroEntradas, interpretar_entrada
from app.realtime.gestor_motores import gestor_motores
from app.realtime.motor_partida import MotorPartida
from app.repositories import PartidaRepository
from app.services.partida_service import PartidaService

router = APIRouter()


def _evento(tipo: str, partida_id: int, jugador_id: int) -> dict:
    return {
        "tipo": tipo,
        "jugador_id": jugador_id,
        "conectados": manager.conectados(partida_id),
    }


async def _responder_error(websocket: WebSocket, codigo: str, detalle: str) -> None:
    await websocket.send_json({"tipo": "error", "codigo": codigo, "detalle": detalle})


async def _procesar_mensaje(
    websocket: WebSocket,
    motor: MotorPartida,
    jugador_id: int,
    filtro: FiltroEntradas,
    texto: str,
) -> None:
    try:
        mensaje = json.loads(texto)
    except ValueError:
        await _responder_error(websocket, "json_invalido", "el mensaje no es JSON")
        return
    if not isinstance(mensaje, dict):
        await _responder_error(websocket, "json_invalido", "el mensaje debe ser un objeto JSON")
        return
    if mensaje.get("tipo") != "entrada":
        return  # otros tipos (por ejemplo "dispositivo") se atienden en el Sprint 3
    try:
        entrada = interpretar_entrada(mensaje)
    except EntradaInvalida as error:
        await _responder_error(websocket, "entrada_invalida", str(error))
        return
    if filtro.admite(entrada):
        motor.aplicar_entrada(jugador_id, entrada.control, entrada.estado)


@router.websocket("/ws/partidas/{partida_id}")
async def canal_partida(
    websocket: WebSocket,
    partida_id: int,
    db: SessionDep,
    token: str = "",
) -> None:
    # el jugador sale del token de la sesión (?token=<JWT>), así nadie se hace pasar por otro
    try:
        jugador_id = usuario_desde_token(db, token).id
    except TokenInvalidoError:
        db.close()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    servicio = PartidaService(PartidaRepository(db))
    autorizado = servicio.es_participante(partida_id, jugador_id)
    db.close()  # no retener la conexión a la base mientras dure el WebSocket
    if not autorizado:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.conectar(partida_id, jugador_id, websocket)
    motor = gestor_motores.obtener(partida_id)
    motor.agregar_jugador(jugador_id)
    await manager.difundir(
        partida_id, _evento("jugador_conectado", partida_id, jugador_id)
    )
    filtro = FiltroEntradas()  # el número de secuencia es por conexión
    try:
        while True:
            texto = await websocket.receive_text()
            await _procesar_mensaje(websocket, motor, jugador_id, filtro, texto)
    except WebSocketDisconnect:
        pass
    finally:
        if manager.desconectar(partida_id, jugador_id, websocket):
            motor.quitar_jugador(jugador_id)
            await manager.difundir(
                partida_id, _evento("jugador_desconectado", partida_id, jugador_id)
            )
            await gestor_motores.liberar_si_esta_vacio(partida_id)