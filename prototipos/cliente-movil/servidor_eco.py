"""Servidor de PRUEBA para el prototipo de cliente móvil. No es el backend del juego.

Implementa lo mínimo del contrato de hardware (docs/contrato-api-hardware.md) para probar
el ciclo completo desde PC y celular: recibe mensajes "entrada", mueve a cada jugador en un
ciclo de 50 ms y difunde el estado a todos.

Ejecutar desde esta carpeta:
    uvicorn servidor_eco:app --host 0.0.0.0 --port 8002
"""

import asyncio
import itertools
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

ANCHO, ALTO = 960, 540
VELOCIDAD = 6  # píxeles por ciclo
CICLO_S = 0.05  # 50 ms, como en el contrato
DIRECCIONES = {"arriba": (0, -1), "abajo": (0, 1), "izquierda": (-1, 0), "derecha": (1, 0)}
CONTROLES = set(DIRECCIONES) | {"accion"}
ESTADOS = {"presionado", "liberado"}
COLORES = ["#4fc3f7", "#ffb74d", "#81c784", "#f06292", "#ba68c8", "#fff176"]

jugadores: dict[int, dict] = {}
conexiones: dict[int, WebSocket] = {}
_ids = itertools.count(1)


async def ciclo_de_partida() -> None:
    while True:
        await asyncio.sleep(CICLO_S)
        ahora = time.monotonic()
        for j in jugadores.values():
            dx = sum(DIRECCIONES[c][0] for c in j["presionados"])
            dy = sum(DIRECCIONES[c][1] for c in j["presionados"])
            j["x"] = max(20, min(ANCHO - 20, j["x"] + dx * VELOCIDAD))
            j["y"] = max(20, min(ALTO - 20, j["y"] + dy * VELOCIDAD))
        estado = json.dumps(
            {
                "tipo": "estado",
                "jugadores": [
                    {
                        "id": jid,
                        "x": j["x"],
                        "y": j["y"],
                        "color": j["color"],
                        "origen": j["origen"],
                        "accion": j["accion_hasta"] > ahora,
                    }
                    for jid, j in jugadores.items()
                ],
            }
        )
        for ws in list(conexiones.values()):
            try:
                await ws.send_text(estado)
            except Exception:  # noqa: BLE001 - un cliente caído no detiene el ciclo
                pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    tarea = asyncio.create_task(ciclo_de_partida())
    yield
    tarea.cancel()


app = FastAPI(title="Servidor eco del prototipo móvil", lifespan=lifespan)


@app.websocket("/ws/eco")
async def ws_eco(websocket: WebSocket) -> None:
    await websocket.accept()
    jid = next(_ids)
    jugadores[jid] = {
        "x": ANCHO // 2,
        "y": ALTO // 2,
        "presionados": set(),
        "color": COLORES[(jid - 1) % len(COLORES)],
        "origen": "?",
        "accion_hasta": 0.0,
    }
    conexiones[jid] = websocket
    await websocket.send_text(json.dumps({"tipo": "bienvenida", "id": jid}))
    try:
        while True:
            try:
                msg = json.loads(await websocket.receive_text())
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"tipo": "error", "codigo": "json_invalido"}))
                continue
            if msg.get("tipo") == "ping":
                await websocket.send_text(json.dumps({"tipo": "pong", "t": msg.get("t")}))
            elif msg.get("tipo") == "entrada":
                control, estado = msg.get("control"), msg.get("estado")
                if control not in CONTROLES or estado not in ESTADOS:
                    await websocket.send_text(
                        json.dumps({"tipo": "error", "codigo": "entrada_invalida"})
                    )
                    continue
                j = jugadores[jid]
                j["origen"] = msg.get("origen", "?")
                if control == "accion":
                    if estado == "presionado":
                        j["accion_hasta"] = time.monotonic() + 0.3
                elif estado == "presionado":
                    j["presionados"].add(control)
                else:
                    j["presionados"].discard(control)
    except WebSocketDisconnect:
        pass
    finally:
        jugadores.pop(jid, None)
        conexiones.pop(jid, None)
