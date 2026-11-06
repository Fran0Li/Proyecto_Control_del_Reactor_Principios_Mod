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

from app.realtime.acciones import AccionContextual
from app.realtime.arena import Arena, arena_basica
from app.realtime.eventos import ACCION_REALIZADA, ESTADO_ACTUALIZADO, EventoPartida
from app.realtime.reactor import ExtraccionReactor

log = logging.getLogger(__name__)

VELOCIDAD = 120.0  # píxeles por segundo
CICLO_S = 0.05  # un tick cada 50 ms (contrato de hardware, RNF-02)
DIRECCIONES = {"arriba": (0, -1), "abajo": (0, 1), "izquierda": (-1, 0), "derecha": (1, 0)}


class ObservadorPartida(Protocol):
    async def al_evento(self, evento: EventoPartida) -> None: ...


@dataclass
class JugadorEnArena:
    jugador_id: int
    x: float
    y: float
    presionados: set[str] = field(default_factory=set)
    puntaje: int = 0


class MotorPartida:
    def __init__(
        self,
        partida_id: int,
        arena: Arena | None = None,
        acciones: list[AccionContextual] | None = None,
    ) -> None:
        self.partida_id = partida_id
        self.arena = arena if arena is not None else arena_basica()
        # Lo que hace el botón de acción, en orden de prioridad (ver acciones.py)
        self._acciones: list[AccionContextual] = (
            acciones
            if acciones is not None
            else [ExtraccionReactor(self.arena.reactor, self.arena.radio_jugador)]
        )
        self._observadores: list[ObservadorPartida] = []
        self._jugadores: dict[int, JugadorEnArena] = {}
        self._hay_cambios = False
        self._eventos_pendientes: list[EventoPartida] = []
        self._ticks = 0  # ticks desde que arrancó el motor (el tiempo de la partida)
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
            puntos = self.arena.puntos_inicio
            x, y = puntos[len(self._jugadores) % len(puntos)]
            self._jugadores[jugador_id] = JugadorEnArena(jugador_id, float(x), float(y))
        self._hay_cambios = True

    def quitar_jugador(self, jugador_id: int) -> None:
        if self._jugadores.pop(jugador_id, None) is not None:
            self._hay_cambios = True

    def sumar_puntaje(self, jugador_id: int, puntos: int) -> None:
        """Suma (o resta) puntos al jugador. Lo usan las mecánicas: celdas, extraer del reactor."""
        jugador = self._jugadores.get(jugador_id)
        if jugador is None or puntos == 0:
            return
        jugador.puntaje += puntos
        self._hay_cambios = True

    @property
    def tiempo(self) -> float:
        """Segundos de partida según los ticks (se cuentan enteros para no acumular error)."""
        return self._ticks * CICLO_S

    # entradas y movimiento 

    def aplicar_entrada(self, jugador_id: int, control: str, estado: str) -> None:
        jugador = self._jugadores.get(jugador_id)
        if jugador is None:
            return
        if control == "accion":
            if estado == "presionado":  # soltar la acción no hace nada (contrato)
                self._accionar(jugador)
            return
        if control not in DIRECCIONES:
            return
        if estado == "presionado":
            jugador.presionados.add(control)
        else:
            jugador.presionados.discard(control)

    def _accionar(self, jugador: JugadorEnArena) -> None:
        """Hace la primera acción del contexto que aplique donde está el jugador."""
        for accion in self._acciones:
            resultado = accion.intentar(jugador, self.tiempo)
            if resultado is None:
                continue
            self.sumar_puntaje(jugador.jugador_id, resultado.puntos)
            self._eventos_pendientes.append(
                EventoPartida(
                    ACCION_REALIZADA,
                    self.partida_id,
                    {
                        "jugador_id": jugador.jugador_id,
                        "accion": resultado.accion,
                        "puntos": resultado.puntos,
                    },
                )
            )
            return

    def _mover(self, dt: float) -> None:
        for jugador in self._jugadores.values():
            dx = sum(DIRECCIONES[c][0] for c in jugador.presionados)
            dy = sum(DIRECCIONES[c][1] for c in jugador.presionados)
            if dx == 0 and dy == 0:
                continue
            norma = math.hypot(dx, dy)  # en diagonal se avanza igual de rápido que en recta
            x = jugador.x + dx / norma * VELOCIDAD * dt
            y = jugador.y + dy / norma * VELOCIDAD * dt
            radio = self.arena.radio_jugador
            x = min(max(x, radio), self.arena.ancho - radio)
            y = min(max(y, radio), self.arena.alto - radio)
            if (x, y) != (jugador.x, jugador.y):
                jugador.x, jugador.y = x, y
                self._hay_cambios = True

    def estado(self) -> dict:
        return {
            "jugadores": [
                {
                    "jugador_id": j.jugador_id,
                    "x": round(j.x),
                    "y": round(j.y),
                    "puntaje": j.puntaje,
                }
                for j in sorted(self._jugadores.values(), key=lambda j: j.jugador_id)
            ],
            "arena": self.arena.a_dict(),
            **{accion.clave: accion.a_dict() for accion in self._acciones},
        }

    async def tick(self) -> None:
        """Un ciclo del motor: avanza las acciones, mueve a los jugadores y, si algo cambió,
        avisa a todos. Las acciones que pasaron desde el tick anterior se avisan primero."""
        self._ticks += 1
        for accion in self._acciones:
            if accion.actualizar(CICLO_S):
                self._hay_cambios = True
        self._mover(CICLO_S)
        eventos, self._eventos_pendientes = self._eventos_pendientes, []
        for evento in eventos:
            await self._notificar(evento)
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