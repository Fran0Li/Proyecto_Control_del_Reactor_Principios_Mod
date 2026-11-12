"""Celdas de energía (US-13): quien toca una celda se lleva sus puntos y la celda reaparece."""

import math
from collections.abc import Iterable

from app.realtime.arena import Celda

RADIO_CELDA = 10  # lo que ocupa una celda; el cliente la dibuja con el mismo radio
REPOSICION_S = 10.0  # segundos que tarda una celda recogida en volver al mapa


class RecolectorCeldas:
    def __init__(
        self,
        celdas: list[Celda],
        radio_jugador: float,
        reposicion_s: float = REPOSICION_S,
    ) -> None:
        self._celdas = list(celdas)
        self._radio_jugador = radio_jugador
        self._reposicion_s = reposicion_s
        # id de la celda -> segundos que faltan para que vuelva
        self._en_espera: dict[int, float] = {}

    def disponibles(self) -> list[Celda]:
        """Las celdas que están ahora en el mapa."""
        return [c for c in self._celdas if c.id not in self._en_espera]

    def recoger(self, jugadores: Iterable[tuple[int, float, float]]) -> list[tuple[int, Celda]]:
        """Recibe (jugador_id, x, y) de cada jugador y devuelve (jugador_id, celda) por cada
        celda que alguien toca. Si dos jugadores tocan la misma, se la lleva el primero."""
        jugadores = list(jugadores)
        alcance = self._radio_jugador + RADIO_CELDA
        recogidas = []
        for celda in self.disponibles():
            for jugador_id, x, y in jugadores:
                if math.hypot(x - celda.x, y - celda.y) <= alcance:
                    recogidas.append((jugador_id, celda))
                    self._en_espera[celda.id] = self._reposicion_s
                    break
        return recogidas

    def reponer(self, dt: float) -> bool:
        """Descuenta el tiempo a las celdas recogidas. Devuelve True si alguna volvió al mapa."""
        volvieron = []
        for celda_id in self._en_espera:
            self._en_espera[celda_id] -= dt
            if self._en_espera[celda_id] <= 0:
                volvieron.append(celda_id)
        for celda_id in volvieron:
            del self._en_espera[celda_id]
        return bool(volvieron)