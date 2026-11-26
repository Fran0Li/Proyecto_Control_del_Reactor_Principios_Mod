"""Observador que marca la partida como finalizada y guarda puntaje y puesto de cada jugador."""

import asyncio

from app.realtime.evaluador_logros import FabricaSesiones
from app.realtime.eventos import PARTIDA_FINALIZADA, EventoPartida
from app.repositories import PartidaRepository


class CierrePartida:
    def __init__(self, fabrica_sesiones: FabricaSesiones) -> None:
        self._fabrica = fabrica_sesiones

    async def al_evento(self, evento: EventoPartida) -> None:
        if evento.tipo == PARTIDA_FINALIZADA:
            await asyncio.to_thread(self._cerrar, evento.partida_id, evento.datos)

    def _cerrar(self, partida_id: int, datos: dict) -> None:
        posiciones = {
            int(p["jugador_id"]): (int(p["puntaje"]), int(p["posicion"]))
            for p in datos.get("posiciones", [])
        }
        with self._fabrica() as sesion:
            repo = PartidaRepository(sesion)
            partida = repo.obtener_por_id(partida_id)
            if partida is not None:
                repo.guardar_resultado(partida, posiciones)
