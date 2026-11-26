"""Eventos que el motor de partida avisa a sus observadores (patrón Observer, ADR 0003)."""

from dataclasses import dataclass, field

ESTADO_ACTUALIZADO = "estado_actualizado"
PARTIDA_INICIADA = "partida_iniciada"  # datos: tiempo_limite, puntaje_objetivo, jugadores
ACCION_REALIZADA = "accion_realizada"  # datos: jugador_id, accion, puntos
JUGADOR_PENALIZADO = "jugador_penalizado"  # datos: jugador_id, guardian_id, puntos, estado
RETO_COMPLETADO = "reto_completado"  # US-27, datos: jugador_id, reto, nombre, puntos
# US-16: un evento especial empezó o terminó (puntos dobles, invasión)
EVENTO_ESPECIAL_INICIADO = "evento_especial_iniciado"  # datos: evento, nombre, duracion_s
EVENTO_ESPECIAL_FINALIZADO = "evento_especial_finalizado"  # datos: evento, nombre

# Contrato del fin de partida (US-17). Lo emite el motor una sola vez, cuando la partida termina
# por tiempo o por puntaje objetivo. Lo escuchan los logros (US-27) y lo puede escuchar el ranking
# (US-19).
#   datos: puntajes  -> {jugador_id: puntaje final} de los jugadores que terminaron la partida
#          ganador_id -> id del primer lugar, o None si hubo empate en el primer lugar
#          posiciones -> [{jugador_id, nombre, puntaje, posicion}] de mayor a menor puntaje
#          motivo     -> "tiempo", "puntaje" o "administrador"
#          duracion_s -> segundos que duró la partida
PARTIDA_FINALIZADA = "partida_finalizada"


@dataclass(frozen=True)
class EventoPartida:
    tipo: str
    partida_id: int
    datos: dict = field(default_factory=dict)