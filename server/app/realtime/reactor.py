"""Extraer energía del reactor con el botón de acción (US-11, RF-011).

El reactor tiene una reserva de energía que se llena sola con el tiempo, hasta su capacidad.
Cada vez que un jugador presiona la acción tocando el reactor, extrae una parte de esa reserva y
la suma a su puntaje. Como la reserva es compartida, los jugadores compiten cerca del reactor,
que es lo que pidió el stakeholder.

Los valores son provisionales (el stakeholder no dio números) y se pueden cambiar al crear la
mecánica, por ejemplo desde un escenario (US-09).
"""

import math

from app.realtime.acciones import PosicionJugador, ResultadoAccion
from app.realtime.arena import Reactor

CAPACIDAD = 100  # energía máxima que guarda el reactor
GENERACION_POR_SEGUNDO = 5.0  # energía que produce el reactor cada segundo
ENERGIA_POR_EXTRACCION = 10  # lo máximo que saca un jugador en cada presión
ESPERA_ENTRE_EXTRACCIONES_S = 0.5  # por jugador, para que no gane solo quien presiona más rápido


class ExtraccionReactor:
    clave = "reactor"

    def __init__(
        self,
        reactor: Reactor,
        radio_jugador: float,
        capacidad: int = CAPACIDAD,
        generacion_por_segundo: float = GENERACION_POR_SEGUNDO,
        energia_por_extraccion: int = ENERGIA_POR_EXTRACCION,
        espera_s: float = ESPERA_ENTRE_EXTRACCIONES_S,
    ) -> None:
        self._reactor = reactor
        self._alcance = reactor.radio + radio_jugador  # basta con que el jugador lo toque
        self._capacidad = capacidad
        self._generacion = generacion_por_segundo
        self._por_extraccion = energia_por_extraccion
        self._espera = espera_s
        self._energia = float(capacidad)  # empieza lleno
        self._ultima_extraccion: dict[int, float] = {}

    @property
    def energia(self) -> int:
        return math.floor(self._energia)

    def actualizar(self, dt: float) -> bool:
        antes = self.energia
        self._energia = min(self._capacidad, self._energia + self._generacion * dt)
        return self.energia != antes

    def esta_en_alcance(self, jugador: PosicionJugador) -> bool:
        distancia = math.hypot(jugador.x - self._reactor.x, jugador.y - self._reactor.y)
        return distancia <= self._alcance

    def intentar(self, jugador: PosicionJugador, tiempo: float) -> ResultadoAccion | None:
        if not self.esta_en_alcance(jugador):
            return None
        ultima = self._ultima_extraccion.get(jugador.jugador_id)
        if ultima is not None and tiempo - ultima < self._espera:
            return None
        cantidad = min(self._por_extraccion, self.energia)
        if cantidad <= 0:
            return None  # el reactor está vacío: hay que esperar a que se recargue
        self._energia -= cantidad
        self._ultima_extraccion[jugador.jugador_id] = tiempo
        return ResultadoAccion(self.clave, cantidad)

    def a_dict(self) -> dict:
        return {"energia": self.energia, "capacidad": self._capacidad}
