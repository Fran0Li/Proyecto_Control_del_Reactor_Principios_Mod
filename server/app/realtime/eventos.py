"""Eventos que el motor de partida avisa a sus observadores (patrón Observer, ADR 0003)."""

from dataclasses import dataclass, field

ESTADO_ACTUALIZADO = "estado_actualizado"
ACCION_REALIZADA = "accion_realizada"  # datos: jugador_id, accion, puntos

# Contrato del fin de partida (US-17). Lo emite el motor una sola vez, cuando la partida termina
# por tiempo o por puntaje objetivo. Lo escuchan los logros (US-27) y lo puede escuchar el ranking
# (US-19).
#   datos: puntajes  -> {jugador_id: puntaje final} de los jugadores que terminaron la partida
#          ganador_id -> id del primer lugar, o None si hubo empate en el primer lugar
PARTIDA_FINALIZADA = "partida_finalizada"


@dataclass(frozen=True)
class EventoPartida:
    tipo: str
    partida_id: int
    datos: dict = field(default_factory=dict)