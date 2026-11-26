"""Acciones del contexto: lo que pasa cuando un jugador presiona el botón de acción.

El botón de acción hace algo distinto según dónde esté el jugador: junto al reactor extrae
energía (US-11) y junto a una terminal la activa (US-12). Cada acción es una clase aparte con la
misma interfaz, así el motor no sabe qué hace cada una y agregar otra no lo modifica
(Open/Closed). El motor las prueba en orden y se queda con la primera que aplica.
"""

from dataclasses import dataclass
from typing import Protocol


class PosicionJugador(Protocol):
    """Lo que una acción necesita saber del jugador."""

    jugador_id: int
    x: float
    y: float


@dataclass(frozen=True)
class ResultadoAccion:
    """Qué logró el jugador con la acción: cuántos puntos gana y de qué acción vienen."""

    accion: str
    puntos: int


class AccionContextual(Protocol):
    clave: str
    """Nombre de la acción. También es la clave de su estado en el mensaje `estado`."""

    def actualizar(self, dt: float) -> bool:
        """Avanza el tiempo de la acción. Devuelve True si cambió algo que ven los jugadores."""
        ...

    def intentar(self, jugador: PosicionJugador, tiempo: float) -> ResultadoAccion | None:
        """Aplica la acción si el jugador puede hacerla ahora; si no, devuelve None."""
        ...

    def a_dict(self) -> dict:
        """El estado de la acción que se manda a los clientes."""
        ...
