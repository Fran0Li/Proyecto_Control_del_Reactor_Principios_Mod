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
from app.realtime.celdas import RecolectorCeldas
from app.realtime.estados_jugador import EstadoJugador, Normal
from app.realtime.eventos import (
    ACCION_REALIZADA,
    ESTADO_ACTUALIZADO,
    JUGADOR_PENALIZADO,
    PARTIDA_FINALIZADA,
    PARTIDA_INICIADA,
    EventoPartida,
)
from app.realtime.guardianes import Guardian
from app.realtime.obstaculos import GestorObstaculos
from app.realtime.reactor import ExtraccionReactor
from app.realtime.reglas_victoria import ReglasVictoria, ganador, ordenar

log = logging.getLogger(__name__)

VELOCIDAD = 120.0  # píxeles por segundo
CICLO_S = 0.05  # un tick cada 50 ms (contrato de hardware, RNF-02)
PENALIZACION_PUNTOS = 5  # lo que pierde el jugador al ser alcanzado por un guardián
DIRECCIONES = {"arriba": (0, -1), "abajo": (0, 1), "izquierda": (-1, 0), "derecha": (1, 0)}

# Ciclo de la partida (US-17). Antes de iniciar los jugadores pueden moverse por la arena para
# probar el control, pero no corre el reloj ni se gana; al iniciar todo vuelve a cero.
ESPERANDO = "esperando"
EN_CURSO = "en_curso"
FINALIZADA = "finalizada"


class ObservadorPartida(Protocol):
    async def al_evento(self, evento: EventoPartida) -> None: ...


@dataclass
class JugadorEnArena:
    jugador_id: int
    x: float
    y: float
    presionados: set[str] = field(default_factory=set)
    puntaje: int = 0
    estado: EstadoJugador = field(default_factory=Normal)
    nombre: str = ""
    conectado: bool = True


class MotorPartida:
    def __init__(
        self,
        partida_id: int,
        arena: Arena | None = None,
        acciones: list[AccionContextual] | None = None,
        guardianes: list[Guardian] | None = None,
    ) -> None:
        self.partida_id = partida_id
        self.arena = arena if arena is not None else arena_basica()
        # Lo que hace el botón de acción, en orden de prioridad (ver acciones.py)
        self._acciones: list[AccionContextual] = (
            acciones
            if acciones is not None
            else [ExtraccionReactor(self.arena.reactor, self.arena.radio_jugador)]
        )
        # Las celdas de energía se recogen al tocarlas y reaparecen solas (ver celdas.py)
        self._celdas = RecolectorCeldas(self.arena.celdas, self.arena.radio_jugador)
        # Los guardianes se mueven solos y penalizan al jugador que alcanzan (ver guardianes.py)
        self._guardianes: list[Guardian] = list(guardianes) if guardianes else []
        self._obstaculos = GestorObstaculos(self.arena.obstaculos, self.arena.radio_jugador)
        self._observadores: list[ObservadorPartida] = []
        self._jugadores: dict[int, JugadorEnArena] = {}
        self._hay_cambios = False
        self._eventos_pendientes: list[EventoPartida] = []
        self._ticks = 0  # ticks desde que arrancó el motor (el tiempo de la partida)
        self._tarea: asyncio.Task | None = None
        self.estado_partida = ESPERANDO
        self._reglas: ReglasVictoria | None = None
        self._tick_inicio = 0
        self._tick_fin = 0
        self._segundos_mostrados: int | None = None  # para avisar cuando cambia el reloj

    # observadores

    def suscribir(self, observador: ObservadorPartida) -> None:
        self._observadores.append(observador)

    def desuscribir(self, observador: ObservadorPartida) -> None:
        self._observadores.remove(observador)

    def publicar(self, tipo: str, datos: dict) -> None:
        """Deja un evento para avisarlo en el próximo tick. Lo usan los observadores que también
        producen eventos, como los retos (US-27), sin que el motor los conozca."""
        self._eventos_pendientes.append(EventoPartida(tipo, self.partida_id, datos))

    async def _notificar(self, evento: EventoPartida) -> None:
        for observador in list(self._observadores):
            try:
                await observador.al_evento(evento)
            except Exception:  # un observador que falla no detiene la partida
                log.exception("Falló un observador de la partida %s", self.partida_id)

    #  jugadores

    @property
    def hay_jugadores(self) -> bool:
        """Si queda alguien conectado (en una partida en curso se guardan también los que se
        fueron, para que su puntaje cuente al final)."""
        return any(j.conectado for j in self._jugadores.values())

    def controles_presionados(self, jugador_id: int) -> frozenset[str]:
        jugador = self._jugadores.get(jugador_id)
        return frozenset(jugador.presionados) if jugador is not None else frozenset()

    def agregar_jugador(self, jugador_id: int, nombre: str = "") -> None:
        """Pone al jugador en su punto de inicio. Si ya estaba (reconexión), conserva su
        posición y le suelta todos los controles."""
        existente = self._jugadores.get(jugador_id)
        if existente is not None:
            existente.presionados.clear()
            existente.conectado = True
            existente.nombre = nombre or existente.nombre
        else:
            puntos = self.arena.puntos_inicio
            x, y = puntos[len(self._jugadores) % len(puntos)]
            self._jugadores[jugador_id] = JugadorEnArena(
                jugador_id, float(x), float(y), nombre=nombre
            )
        self._hay_cambios = True

    def quitar_jugador(self, jugador_id: int) -> None:
        if self.estado_partida == EN_CURSO:
            # Se queda en la partida (puede volver y su puntaje cuenta al final)
            jugador = self._jugadores.get(jugador_id)
            if jugador is not None:
                jugador.conectado = False
                jugador.presionados.clear()
                self._hay_cambios = True
            return
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

    # inicio y fin de la partida (US-17, US-22)

    @property
    def transcurrido(self) -> float:
        """Segundos desde que se inició la partida (0 si todavía no empieza)."""
        if self.estado_partida == ESPERANDO:
            return 0.0
        fin = self._tick_fin if self.estado_partida == FINALIZADA else self._ticks
        return (fin - self._tick_inicio) * CICLO_S

    def iniciar_partida(self, tiempo_limite_s: float, puntaje_objetivo: int) -> bool:
        """Arranca el reloj. Todos vuelven a su punto de inicio con 0 puntos.
        Devuelve False si la partida ya había empezado."""
        if self.estado_partida != ESPERANDO:
            return False
        puntos = self.arena.puntos_inicio
        jugadores = sorted(self._jugadores.values(), key=lambda j: j.jugador_id)
        for indice, jugador in enumerate(jugadores):
            jugador.x, jugador.y = (float(v) for v in puntos[indice % len(puntos)])
            jugador.puntaje = 0
            jugador.estado = Normal()
            jugador.presionados.clear()
        self._celdas = RecolectorCeldas(self.arena.celdas, self.arena.radio_jugador)
        self._reglas = ReglasVictoria(tiempo_limite_s, puntaje_objetivo)
        self._tick_inicio = self._ticks
        self.estado_partida = EN_CURSO
        self._hay_cambios = True
        self._eventos_pendientes.append(
            EventoPartida(
                PARTIDA_INICIADA,
                self.partida_id,
                {
                    "tiempo_limite": tiempo_limite_s,
                    "puntaje_objetivo": puntaje_objetivo,
                    "jugadores": [j.jugador_id for j in jugadores],
                },
            )
        )
        return True

    def terminar(self, motivo: str) -> bool:
        """Cierra la partida y ordena a los jugadores. Devuelve False si no estaba en curso."""
        if self.estado_partida != EN_CURSO:
            return False
        self.estado_partida = FINALIZADA
        self._tick_fin = self._ticks
        posiciones = ordenar(
            [(j.jugador_id, j.nombre, j.puntaje) for j in self._jugadores.values()]
        )
        for jugador in self._jugadores.values():
            jugador.presionados.clear()
        self._hay_cambios = True
        self._eventos_pendientes.append(
            EventoPartida(
                PARTIDA_FINALIZADA,
                self.partida_id,
                {
                    "puntajes": {p.jugador_id: p.puntaje for p in posiciones},
                    "ganador_id": ganador(posiciones),
                    "posiciones": [p.a_dict() for p in posiciones],
                    "motivo": motivo,
                    "duracion_s": round(self.transcurrido),
                },
            )
        )
        return True

    def _revisar_fin(self) -> None:
        if self.estado_partida != EN_CURSO or self._reglas is None:
            return
        segundos = math.ceil(self._reglas.tiempo_restante(self.transcurrido))
        if segundos != self._segundos_mostrados:
            self._segundos_mostrados = segundos
            self._hay_cambios = True  # el reloj de los jugadores cambia una vez por segundo
        motivo = self._reglas.motivo_de_fin(
            self.transcurrido, [j.puntaje for j in self._jugadores.values()]
        )
        if motivo is not None:
            self.terminar(motivo)

    def _info_partida(self) -> dict:
        info: dict = {"estado": self.estado_partida}
        if self._reglas is not None:
            info["tiempo_limite"] = self._reglas.tiempo_limite_s
            info["puntaje_objetivo"] = self._reglas.puntaje_objetivo
            info["tiempo_restante"] = math.ceil(self._reglas.tiempo_restante(self.transcurrido))
        return info

    # entradas y movimiento

    def aplicar_entrada(self, jugador_id: int, control: str, estado: str) -> None:
        jugador = self._jugadores.get(jugador_id)
        if jugador is None or self.estado_partida == FINALIZADA:
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
            if (dx == 0 and dy == 0) or not jugador.estado.puede_moverse:
                continue
            norma = math.hypot(dx, dy)  # en diagonal se avanza igual de rápido que en recta
            velocidad = VELOCIDAD * self._obstaculos.factor_velocidad(jugador.x, jugador.y)
            x = jugador.x + dx / norma * velocidad * dt
            y = jugador.y + dy / norma * velocidad * dt
            radio = self.arena.radio_jugador
            x = min(max(x, radio), self.arena.ancho - radio)
            y = min(max(y, radio), self.arena.alto - radio)
            x, y = self._obstaculos.mover(jugador.x, jugador.y, x, y)
            if (x, y) != (jugador.x, jugador.y):
                jugador.x, jugador.y = x, y
                self._hay_cambios = True

    def _actualizar_celdas(self) -> None:
        """Repone las celdas que ya les toca y da cada celda tocada a su jugador."""
        if self._celdas.reponer(CICLO_S):
            self._hay_cambios = True
        jugadores = sorted(self._jugadores.values(), key=lambda j: j.jugador_id)
        posiciones = [(j.jugador_id, j.x, j.y) for j in jugadores]
        for jugador_id, celda in self._celdas.recoger(posiciones):
            self.sumar_puntaje(jugador_id, celda.valor)
            self._hay_cambios = True

    def _actualizar_guardianes(self, dt: float) -> None:
        """Mueve a los guardianes, avanza el estado de cada jugador y penaliza a los alcanzados."""
        jugadores = list(self._jugadores.values())
        for guardian in self._guardianes:
            if guardian.mover(dt, jugadores):
                self._hay_cambios = True
        for jugador in jugadores:
            nuevo = jugador.estado.actualizar(dt)
            if nuevo is not jugador.estado:
                jugador.estado = nuevo
                self._hay_cambios = True
            if not jugador.estado.vulnerable:
                continue
            for guardian in self._guardianes:
                if guardian.alcanza(jugador.x, jugador.y, self.arena.radio_jugador):
                    self._penalizar(jugador, guardian)
                    break

    def _penalizar(self, jugador: JugadorEnArena, guardian: Guardian) -> None:
        """Un guardián alcanzó al jugador: queda aturdido y pierde puntos (sin bajar de 0)."""
        jugador.estado = jugador.estado.golpeado()
        perdidos = min(PENALIZACION_PUNTOS, jugador.puntaje)
        self.sumar_puntaje(jugador.jugador_id, -perdidos)
        self._hay_cambios = True
        self._eventos_pendientes.append(
            EventoPartida(
                JUGADOR_PENALIZADO,
                self.partida_id,
                {
                    "jugador_id": jugador.jugador_id,
                    "guardian_id": guardian.id,
                    "puntos": -perdidos,
                    "estado": jugador.estado.nombre,
                },
            )
        )

    def estado(self) -> dict:
        arena = self.arena.a_dict()
        # Solo las celdas que están ahora en el mapa
        arena["celdas"] = [c.a_dict() for c in self._celdas.disponibles()]
        # Las puertas dicen si están abiertas o cerradas
        arena["obstaculos"] = self._obstaculos.a_dicts()
        return {
            "jugadores": [
                {
                    "jugador_id": j.jugador_id,
                    "x": round(j.x),
                    "y": round(j.y),
                    "puntaje": j.puntaje,
                    "estado": j.estado.nombre,
                    "nombre": j.nombre,
                }
                for j in sorted(self._jugadores.values(), key=lambda j: j.jugador_id)
            ],
            "arena": arena,
            "guardianes": [g.a_dict() for g in self._guardianes],
            "partida": self._info_partida(),
            **{accion.clave: accion.a_dict() for accion in self._acciones},
        }

    async def tick(self) -> None:
        """Un ciclo del motor: avanza las acciones, mueve a los jugadores y, si algo cambió,
        avisa a todos. Las acciones que pasaron desde el tick anterior se avisan primero."""
        self._ticks += 1
        if self.estado_partida != FINALIZADA:  # terminada, la arena se queda quieta
            for accion in self._acciones:
                if accion.actualizar(CICLO_S):
                    self._hay_cambios = True
            if self._obstaculos.actualizar(CICLO_S):
                self._hay_cambios = True  # una puerta se abrió o se cerró
            self._mover(CICLO_S)
            self._actualizar_guardianes(CICLO_S)
            self._actualizar_celdas()
            self._revisar_fin()
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