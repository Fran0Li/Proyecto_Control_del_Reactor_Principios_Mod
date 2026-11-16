"""Catálogo de logros (US-27).

Un logro es una condición sobre lo que hizo un jugador en una partida. Se evalúan al terminar la
partida (evento `partida_finalizada`) y cada uno se gana una sola vez.

Agregar un logro es agregar una entrada a CATALOGO: el evaluador no cambia (abierto/cerrado, igual
que las acciones del contexto del ADR 0011). Si un logro necesita un dato que todavía no existe
(por ejemplo, "terminar sin ser alcanzado por un guardián", que depende de la US-15), primero se
agrega el dato a EstadisticasJugador desde el evento que lo produce.
"""

from collections.abc import Callable
from dataclasses import dataclass

ENERGIA_PARA_LOGRO = 300  # el ejemplo de los criterios de aceptación de la US-27


@dataclass
class EstadisticasJugador:
    """Lo que hizo un jugador durante una partida, juntado a partir de los eventos del motor."""

    jugador_id: int
    energia_reactor: int = 0  # puntos sacados del reactor (US-11)
    extracciones: int = 0
    puntaje_final: int = 0
    gano: bool = False


@dataclass(frozen=True)
class Logro:
    clave: str  # lo que se guarda en la base; no cambiarla una vez publicada
    nombre: str
    descripcion: str
    condicion: Callable[[EstadisticasJugador], bool]


CATALOGO: tuple[Logro, ...] = (
    Logro(
        "primera_partida",
        "Bautizo nuclear",
        "Terminá tu primera partida.",
        lambda e: True,
    ),
    Logro(
        "primera_victoria",
        "Primera victoria",
        "Ganá una partida.",
        lambda e: e.gano,
    ),
    Logro(
        "energia_300",
        "Sobrecarga",
        f"Extraé {ENERGIA_PARA_LOGRO} de energía del reactor en una sola partida.",
        lambda e: e.energia_reactor >= ENERGIA_PARA_LOGRO,
    ),
)

POR_CLAVE: dict[str, Logro] = {logro.clave: logro for logro in CATALOGO}


def nuevos_logros(estadisticas: EstadisticasJugador, ya_obtenidos: set[str]) -> list[Logro]:
    """Los logros que el jugador cumplió en esta partida y que todavía no tenía."""
    return [
        logro
        for logro in CATALOGO
        if logro.clave not in ya_obtenidos and logro.condicion(estadisticas)
    ]
