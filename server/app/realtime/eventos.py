"""Eventos que el motor de partida avisa a sus observadores (patrón Observer, ADR 0003)."""

from dataclasses import dataclass, field

ESTADO_ACTUALIZADO = "estado_actualizado"
ACCION_REALIZADA = "accion_realizada"  # datos: jugador_id, accion, puntos


@dataclass(frozen=True)
class EventoPartida:
    tipo: str
    partida_id: int
    datos: dict = field(default_factory=dict)