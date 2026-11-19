"""Observador que suma el resultado de cada partida al ranking global (US-17 y US-19)."""

import asyncio

from app.realtime.evaluador_logros import FabricaSesiones
from app.realtime.eventos import PARTIDA_FINALIZADA, EventoPartida
from app.repositories import RankingRepository


class ActualizadorRanking:
    def __init__(self, fabrica_sesiones: FabricaSesiones) -> None:
        self._fabrica = fabrica_sesiones

    async def al_evento(self, evento: EventoPartida) -> None:
        if evento.tipo == PARTIDA_FINALIZADA:
            await asyncio.to_thread(self._actualizar, evento.datos)

    def _actualizar(self, datos: dict) -> None:
        ganador = datos.get("ganador_id")
        with self._fabrica() as sesion:
            repo = RankingRepository(sesion)
            for jugador_id, puntaje in datos.get("puntajes", {}).items():
                gano = ganador is not None and int(jugador_id) == int(ganador)
                repo.sumar_partida(int(jugador_id), int(puntaje), gano)
