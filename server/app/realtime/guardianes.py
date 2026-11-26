"""Guardianes de la arena (US-15, patrón Strategy, ADR 0006).

El contexto es `Guardian`: guarda su posición y una estrategia, y le delega `mover()`. Las
estrategias (`RutaFija`, `Patrulla`, `Perseguir`) tienen la misma interfaz; el escenario elige
cuál usa cada guardián, y el guardián no sabe cuál es.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

RADIO_GUARDIAN = 18
VELOCIDAD_GUARDIAN = 80.0  # menos que los 120 px/s del jugador: se puede escapar
RADIO_DETECCION = 150.0


class Objetivo(Protocol):
    """Lo que un guardián necesita saber de un jugador."""

    x: float
    y: float


class EstrategiaMovimiento(Protocol):
    def mover(self, guardian: "Guardian", dt: float, objetivos: Sequence[Objetivo]) -> None:
        """Cambia la posición del guardián durante `dt` segundos."""
        ...


def _avanzar_hacia(guardian: "Guardian", x: float, y: float, distancia: float) -> bool:
    """Acerca al guardián a (x, y) hasta `distancia` píxeles. True si llegó."""
    restante = math.hypot(x - guardian.x, y - guardian.y)
    if restante <= distancia:
        guardian.x, guardian.y = float(x), float(y)
        return True
    guardian.x += (x - guardian.x) / restante * distancia
    guardian.y += (y - guardian.y) / restante * distancia
    return False


class RutaFija:
    """Recorre los puntos en orden y, al llegar al último, vuelve al primero (un circuito)."""

    def __init__(
        self, puntos: Sequence[tuple[float, float]], velocidad: float = VELOCIDAD_GUARDIAN
    ) -> None:
        if not puntos:
            raise ValueError("La ruta necesita al menos un punto")
        self._puntos = list(puntos)
        self._velocidad = velocidad
        self._indice = 0

    def mover(self, guardian: "Guardian", dt: float, objetivos: Sequence[Objetivo]) -> None:
        x, y = self._puntos[self._indice]
        if _avanzar_hacia(guardian, x, y, self._velocidad * dt):
            self._indice = (self._indice + 1) % len(self._puntos)


class Patrulla:
    """Va de un extremo de la lista al otro y se devuelve (ida y vuelta)."""

    def __init__(
        self, puntos: Sequence[tuple[float, float]], velocidad: float = VELOCIDAD_GUARDIAN
    ) -> None:
        if not puntos:
            raise ValueError("La patrulla necesita al menos un punto")
        self._puntos = list(puntos)
        self._velocidad = velocidad
        self._indice = 0
        self._paso = 1

    def mover(self, guardian: "Guardian", dt: float, objetivos: Sequence[Objetivo]) -> None:
        x, y = self._puntos[self._indice]
        if not _avanzar_hacia(guardian, x, y, self._velocidad * dt):
            return
        siguiente = self._indice + self._paso
        if not 0 <= siguiente < len(self._puntos):
            self._paso = -self._paso  # llegó a un extremo: da la vuelta
            siguiente = self._indice + self._paso
        if 0 <= siguiente < len(self._puntos):
            self._indice = siguiente


class Perseguir:
    """Va hacia el jugador más cercano que esté dentro de su radio de detección.
    Si no hay ninguno, se queda quieto."""

    def __init__(
        self, radio_deteccion: float = RADIO_DETECCION, velocidad: float = VELOCIDAD_GUARDIAN
    ) -> None:
        self._radio_deteccion = radio_deteccion
        self._velocidad = velocidad

    def mover(self, guardian: "Guardian", dt: float, objetivos: Sequence[Objetivo]) -> None:
        cercano = None
        menor = self._radio_deteccion
        for objetivo in objetivos:
            distancia = math.hypot(objetivo.x - guardian.x, objetivo.y - guardian.y)
            if distancia <= menor:
                cercano, menor = objetivo, distancia
        if cercano is not None:
            _avanzar_hacia(guardian, cercano.x, cercano.y, self._velocidad * dt)


@dataclass
class Guardian:
    id: int
    x: float
    y: float
    estrategia: EstrategiaMovimiento
    radio: float = RADIO_GUARDIAN

    def mover(self, dt: float, objetivos: Sequence[Objetivo]) -> bool:
        """Se mueve según su estrategia. Devuelve True si cambió de lugar."""
        antes = (self.x, self.y)
        self.estrategia.mover(self, dt, objetivos)
        return (self.x, self.y) != antes

    def alcanza(self, x: float, y: float, radio_jugador: float) -> bool:
        """True si el guardián toca al jugador que está en (x, y)."""
        return math.hypot(self.x - x, self.y - y) <= self.radio + radio_jugador

    def a_dict(self) -> dict:
        return {"id": self.id, "x": round(self.x), "y": round(self.y), "radio": round(self.radio)}