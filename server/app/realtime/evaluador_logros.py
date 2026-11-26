"""Observador que evalúa los logros de cada jugador al terminar la partida (US-27)."""

import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.realtime.eventos import (
    ACCION_REALIZADA,
    JUGADOR_PENALIZADO,
    PARTIDA_FINALIZADA,
    PARTIDA_INICIADA,
    EventoPartida,
)
from app.realtime.logros import EstadisticasJugador, nuevos_logros
from app.realtime.reactor import ExtraccionReactor
from app.repositories.logro_repository import LogroRepository

log = logging.getLogger(__name__)

FabricaSesiones = Callable[[], Session]


class EvaluadorLogros:
    """Junta lo que hace cada jugador durante la partida y, al terminar, guarda los logros nuevos.

    Es un Subscriber del motor (Observer, ADR 0006): el motor no sabe que los logros existen, y
    agregarlos no lo modificó. Hay uno por partida, así sus estadísticas se van con el motor.

    Antes de iniciar la partida los jugadores pueden moverse y extraer energía para probar el
    control (US-17), pero eso no cuenta: al llegar `partida_iniciada` se borran las estadísticas,
    igual que el motor pone los puntajes en cero.
    """

    def __init__(self, fabrica_sesiones: FabricaSesiones) -> None:
        self._fabrica = fabrica_sesiones
        self._estadisticas: dict[int, EstadisticasJugador] = {}
        self._evaluada = False

    def estadisticas(self, jugador_id: int) -> EstadisticasJugador:
        if jugador_id not in self._estadisticas:
            self._estadisticas[jugador_id] = EstadisticasJugador(jugador_id)
        return self._estadisticas[jugador_id]

    async def al_evento(self, evento: EventoPartida) -> None:
        if evento.tipo == PARTIDA_INICIADA:
            self._estadisticas.clear()  # lo de antes de iniciar era práctica
        elif evento.tipo == ACCION_REALIZADA:
            self._registrar_accion(evento.datos)
        elif evento.tipo == JUGADOR_PENALIZADO:
            self.estadisticas(int(evento.datos["jugador_id"])).penalizaciones += 1
        elif evento.tipo == PARTIDA_FINALIZADA and not self._evaluada:
            self._evaluada = True  # una partida se evalúa una sola vez
            # La base es sincrónica: se escribe en otro hilo para no frenar el ciclo de eventos
            # mientras tanto (regla del ADR 0006: nada bloqueante dentro del motor).
            await asyncio.to_thread(self._evaluar, evento.partida_id, evento.datos)

    def _registrar_accion(self, datos: dict) -> None:
        if datos.get("accion") != ExtraccionReactor.clave:
            return
        estadisticas = self.estadisticas(int(datos["jugador_id"]))
        estadisticas.energia_reactor += int(datos["puntos"])
        estadisticas.extracciones += 1

    def _evaluar(self, partida_id: int, datos: dict) -> None:
        ganador = datos.get("ganador_id")
        with self._fabrica() as sesion:
            repo = LogroRepository(sesion)
            for jugador_id, puntaje in datos.get("puntajes", {}).items():
                estadisticas = self.estadisticas(int(jugador_id))
                estadisticas.puntaje_final = int(puntaje)
                estadisticas.gano = ganador is not None and int(jugador_id) == int(ganador)
                nuevos = nuevos_logros(estadisticas, repo.claves_obtenidas(int(jugador_id)))
                if nuevos:
                    repo.agregar(int(jugador_id), [logro.clave for logro in nuevos], partida_id)
                    log.info(
                        "Partida %s: el jugador %s desbloqueó %s",
                        partida_id,
                        jugador_id,
                        ", ".join(logro.clave for logro in nuevos),
                    )
