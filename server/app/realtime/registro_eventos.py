"""Observador que guarda en la tabla `eventos` lo importante de cada partida (US-17).

No guarda `estado_actualizado` (llega cada 50 ms y no aporta al historial): solo el inicio, las
acciones, las penalizaciones, los retos cumplidos (US-27) y el final. Con esto el historial y la
ceremonia pueden contar, por ejemplo, cuántas veces extrajo energía cada jugador.
"""

import asyncio

from app.realtime.evaluador_logros import FabricaSesiones
from app.realtime.eventos import (
    ACCION_REALIZADA,
    JUGADOR_PENALIZADO,
    PARTIDA_FINALIZADA,
    PARTIDA_INICIADA,
    RETO_COMPLETADO,
    EventoPartida,
)
from app.repositories import EventoRepository

TIPOS_GUARDADOS = (
    PARTIDA_INICIADA,
    ACCION_REALIZADA,
    JUGADOR_PENALIZADO,
    RETO_COMPLETADO,  # US-27
    PARTIDA_FINALIZADA,
)


class RegistroEventos:
    def __init__(self, fabrica_sesiones: FabricaSesiones) -> None:
        self._fabrica = fabrica_sesiones

    async def al_evento(self, evento: EventoPartida) -> None:
        if evento.tipo in TIPOS_GUARDADOS:
            # la base es sincrónica: se escribe en otro hilo para no frenar el motor (ADR 0006)
            await asyncio.to_thread(self._guardar, evento)

    def _guardar(self, evento: EventoPartida) -> None:
        jugador_id = evento.datos.get("jugador_id")
        with self._fabrica() as sesion:
            EventoRepository(sesion).agregar(
                evento.partida_id,
                evento.tipo,
                int(jugador_id) if jugador_id is not None else None,
                _a_json(evento.datos),
            )


def _a_json(datos: dict) -> dict:
    """JSON solo acepta claves de texto (los puntajes vienen como {jugador_id: puntaje})."""
    return {
        clave: {str(k): v for k, v in valor.items()} if isinstance(valor, dict) else valor
        for clave, valor in datos.items()
    }
