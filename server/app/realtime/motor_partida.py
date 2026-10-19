"""Motor de partida: mueve a los jugadores en la arena y avisa a los observadores (ADR 0003).

El servidor es autoritativo: los clientes solo mandan qué controles están presionados y el
motor decide las posiciones. El motor no sabe nada de WebSockets ni de la base de datos: avisa a
sus observadores (patrón Observer) y ellos deciden qué hacer con cada evento.
"""

import asyncio
import logging
import math
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Protocol

from app.realtime.eventos import ESTADO_ACTUALIZADO, EventoPartida

log = logging.getLogger(__name__)

ANCHO_ARENA = 960
ALTO_ARENA = 540
RADIO_JUGADOR = 20
VELOCIDAD = 120.0  # píxeles por segundo
CICLO_S = 0.05  # un tick cada 50 ms (contrato de hardware, RNF-02)
PUNTOS_DE_INICIO = [(240, 135), (720, 135), (240, 405), (720, 405)]
DIRECCIONES = {"arriba": (0, -1), "abajo": (0, 1), "izquierda": (-1, 0), "derecha": (1, 0)}


class ObservadorPartida(Protocol):
    async def al_evento(self, evento: EventoPartida) -> None: ...


@dataclass
class JugadorEnArena:
    jugador_id: int
    x: float
    y: float
    presionados: set[str] = field(default_factory=set)


class MotorPartida:
    def __init__(self, partida_id: int) -> None:
        self.partida_id = partida_id
        self._observadores: list[ObservadorPartida] = []
        self._jugadores: dict[int, JugadorEnArena] = {}
        self._hay_cambios = False
        self._tarea: asyncio.Task | None = None

    # observadores 

    def suscribir(self, observador: ObservadorPartida) -> None:
        self._observadores.append(observador)

    def desuscribir(self, observador: ObservadorPartida) -> None:
        self._observadores.remove(observador)

    async def _notificar(self, evento: EventoPartida) -> None:
        for observador in list(self._observadores):
            try:
                await observador.al_evento(evento)
            except Exception:  # un observador que falla no detiene la partida
                log.exception("Falló un observador de la partida %s", self.partida_id)

    #  jugadores 

    @property
    def hay_jugadores(self) -> bool:
        return bool(self._jugadores)

    def controles_presionados(self, jugador_id: int) -> frozenset[str]:
        jugador = self._jugadores.get(jugador_id)
        return frozenset(jugador.presionados) if jugador is not None else frozenset()

    def agregar_jugador(self, jugador_id: int) -> None:
        """Pone al jugador en su punto de inicio. Si ya estaba (reconexión), conserva su
        posición y le suelta todos los controles."""
        existente = self._jugadores.get(jugador_id)
        if existente is not None:
            existente.presionados.clear()
        else:
            x, y = PUNTOS_DE_INICIO[len(self._jugadores) % len(PUNTOS_DE_INICIO)]
            self._jugadores[jugador_id] = JugadorEnArena(jugador_id, float(x), float(y))
        self._hay_cambios = True

    def quitar_jugador(self, jugador_id: int) -> None:
        if self._jugadores.pop(jugador_id, None) is not None:
            self._hay_cambios = True

    # entradas y movimiento 

    def aplicar_entrada(self, jugador_id: int, control: str, estado: str) -> None:
        jugador = self._jugadores.get(jugador_id)
        if jugador is None or control not in DIRECCIONES:
            return  # la acción (extraer energía, terminales) llega en el Sprint 3
        if estado == "presionado":
            jugador.presionados.add(control)
        else:
            jugador.presionados.discard(control)

    def _mover(self, dt: float) -> None:
        for jugador in self._jugadores.values():
            dx = sum(DIRECCIONES[c][0] for c in jugador.presionados)
            dy = sum(DIRECCIONES[c][1] for c in jugador.presionados)
            if dx == 0 and dy == 0:
                continue
            norma = math.hypot(dx, dy)  # en diagonal se avanza igual de rápido que en recta
            x = jugador.x + dx / norma * VELOCIDAD * dt
            y = jugador.y + dy / norma * VELOCIDAD * dt
            x = min(max(x, RADIO_JUGADOR), ANCHO_ARENA - RADIO_JUGADOR)
            y = min(max(y, RADIO_JUGADOR), ALTO_ARENA - RADIO_JUGADOR)
            if (x, y) != (jugador.x, jugador.y):
                jugador.x, jugador.y = x, y
                self._hay_cambios = True

    def estado(self) -> dict:
        return {
            "jugadores": [
                {"jugador_id": j.jugador_id, "x": round(j.x), "y": round(j.y)}
                for j in sorted(self._jugadores.values(), key=lambda j: j.jugador_id)
            ],
            "arena": {"ancho": ANCHO_ARENA, "alto": ALTO_ARENA, "radio": RADIO_JUGADOR},
        }

    async def tick(self) -> None:
        """Un ciclo del motor: mueve a los jugadores y, si algo cambió, avisa a todos."""
        self._mover(CICLO_S)
        if self._hay_cambios:
            self._hay_cambios = False
            await self._notificar(EventoPartida(ESTADO_ACTUALIZADO, self.partida_id, self.estado()))

    # ciclo 

    def iniciar(self) -> None:
        if self._tarea is None or self._tarea.done():
            self._tarea = asyncio.create_task(self._ciclo())

    async def detener(self) -> None:
        tarea, self._tarea = self._tarea, None
        if tarea is None:
            return
        tarea.cancel()
        if tarea.get_loop() is asyncio.get_running_loop():
            with suppress(asyncio.CancelledError):
                await tarea  # solo se espera si es del mismo ciclo de eventos

    async def _ciclo(self) -> None:
        siguiente = time.monotonic()
        while True:
            siguiente += CICLO_S
            ahora = time.monotonic()
            if siguiente < ahora - CICLO_S:
                siguiente = ahora  # se atrasó demasiado: no recuperar a golpes
            await asyncio.sleep(max(0.0, siguiente - ahora))
            await self.tick()