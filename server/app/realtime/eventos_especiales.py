"""Eventos especiales aleatorios de la partida (US-16, patrón Factory, ADR 0004).

Cada cierto tiempo ocurre un evento que cambia una regla durante unos segundos y después se
deshace solo. Hay dos: puntos dobles e invasión de guardianes. Cada evento es una clase con la
misma interfaz (`iniciar` y `terminar`) y `FabricaEventos` decide cuál crear (Factory): agregar
otro evento no toca al motor ni al programador.

`ProgramadorEventos` lleva el reloj: el primer evento sale a los 30 s de empezar la partida, cada
uno dura 10 s y el siguiente llega entre 30 y 45 s después. Siempre hay uno solo a la vez y nunca
se repite el mismo dos veces seguidas. Solo corre mientras la partida está en curso.
"""

import math
import random
from collections.abc import Callable
from typing import Protocol

from app.realtime.arena import Arena
from app.realtime.eventos import EVENTO_ESPECIAL_FINALIZADO, EVENTO_ESPECIAL_INICIADO
from app.realtime.guardianes import RADIO_GUARDIAN, Guardian, Perseguir
from app.realtime.obstaculos import BARRERA, BARRERA_MOVIL, PUERTA, toca

PRIMER_EVENTO_S = 30.0  # desde que empieza la partida hasta el primer evento
ESPERA_MINIMA_S = 30.0  # entre que termina un evento y empieza el siguiente
ESPERA_MAXIMA_S = 45.0
DURACION_EVENTO_S = 10.0
TOLERANCIA_S = 1e-9  # los segundos son decimales: se compara con un margen mínimo

MULTIPLICADOR_PUNTOS_DOBLES = 2
INVASORES = 2  # guardianes extra que trae la invasión
ID_PRIMER_INVASOR = 100  # los guardianes de los mapas usan 1, 2, 3...
DISTANCIA_AL_REACTOR = 100  # px entre el borde del reactor y donde aparece cada invasor
RADIO_DETECCION_INVASOR = 2000.0  # persiguen desde cualquier punto de la arena
BLOQUEANTES = (BARRERA, BARRERA_MOVIL, PUERTA)


class ContextoEvento(Protocol):
    """Lo que un evento puede hacerle a la partida. Lo cumple `MotorPartida`."""

    arena: Arena

    def poner_multiplicador_puntos(self, multiplicador: int) -> None: ...

    def agregar_guardian(self, guardian: Guardian) -> None: ...

    def quitar_guardian(self, guardian_id: int) -> None: ...

    def posiciones_jugadores(self) -> list[tuple[float, float]]: ...

    def publicar(self, tipo: str, datos: dict) -> None: ...


class EventoEspecial(Protocol):
    clave: str
    nombre: str

    def iniciar(self, motor: ContextoEvento) -> None: ...

    def terminar(self, motor: ContextoEvento) -> None:
        """Deshace todo lo que hizo `iniciar`."""
        ...


class PuntosDobles:
    """Todo lo que se gana vale el doble. Las penalizaciones no se duplican."""

    clave = "puntos_dobles"
    nombre = "Puntos dobles"

    def iniciar(self, motor: ContextoEvento) -> None:
        motor.poner_multiplicador_puntos(MULTIPLICADOR_PUNTOS_DOBLES)

    def terminar(self, motor: ContextoEvento) -> None:
        motor.poner_multiplicador_puntos(1)


class Invasion:
    """Aparecen dos guardianes perseguidores en lados opuestos del reactor. Al terminar el
    evento desaparecen; los guardianes del mapa no se tocan."""

    clave = "invasion"
    nombre = "Invasión"

    def __init__(self, azar: random.Random | None = None) -> None:
        self._azar = azar or random.Random()
        self._ids: list[int] = []

    def iniciar(self, motor: ContextoEvento) -> None:
        for indice, (x, y) in enumerate(self._puntos_de_aparicion(motor)):
            invasor = Guardian(
                ID_PRIMER_INVASOR + indice,
                x,
                y,
                Perseguir(radio_deteccion=RADIO_DETECCION_INVASOR),
            )
            motor.agregar_guardian(invasor)
            self._ids.append(invasor.id)

    def terminar(self, motor: ContextoEvento) -> None:
        for guardian_id in self._ids:
            motor.quitar_guardian(guardian_id)
        self._ids = []

    def _puntos_de_aparicion(self, motor: ContextoEvento) -> list[tuple[float, float]]:
        """Una pareja de puntos opuestos alrededor del reactor. Entre las parejas que caen en
        suelo libre elige la más lejana a los jugadores, para no caerle encima a nadie."""
        reactor = motor.arena.reactor
        distancia = reactor.radio + DISTANCIA_AL_REACTOR
        parejas = [
            [_punto(reactor.x, reactor.y, g, distancia) for g in (grados, grados + 180)]
            for grados in (0, 45, 90, 135)
        ]
        self._azar.shuffle(parejas)  # entre parejas igual de buenas, que decida el azar
        libres = [p for p in parejas if all(_esta_libre(motor.arena, x, y) for x, y in p)]
        jugadores = motor.posiciones_jugadores()
        return max(libres or parejas, key=lambda pareja: _lejania(pareja, jugadores))


def _punto(
    centro_x: float, centro_y: float, grados: float, distancia: float
) -> tuple[float, float]:
    angulo = math.radians(grados)
    return centro_x + math.cos(angulo) * distancia, centro_y + math.sin(angulo) * distancia


def _esta_libre(arena: Arena, x: float, y: float) -> bool:
    """Dentro de la arena y sin tocar paredes ni puertas."""
    dentro = RADIO_GUARDIAN <= x <= arena.ancho - RADIO_GUARDIAN
    dentro = dentro and RADIO_GUARDIAN <= y <= arena.alto - RADIO_GUARDIAN
    if not dentro:
        return False
    return not any(
        o.tipo in BLOQUEANTES and toca(x, y, RADIO_GUARDIAN, o) for o in arena.obstaculos
    )


def _lejania(puntos: list[tuple[float, float]], jugadores: list[tuple[float, float]]) -> float:
    """Qué tan lejos queda de los jugadores el punto que está más cerca de alguno."""
    if not jugadores:
        return math.inf
    return min(math.hypot(x - jx, y - jy) for x, y in puntos for jx, jy in jugadores)


class FabricaEventos:
    """Crea los eventos por su clave (patrón Factory)."""

    def __init__(self, azar: random.Random | None = None) -> None:
        self._azar = azar or random.Random()
        self._creadores: dict[str, Callable[[], EventoEspecial]] = {
            PuntosDobles.clave: PuntosDobles,
            Invasion.clave: lambda: Invasion(self._azar),
        }

    @property
    def claves(self) -> list[str]:
        return list(self._creadores)

    def crear(self, clave: str) -> EventoEspecial:
        if clave not in self._creadores:
            raise ValueError(f"Evento no válido: {clave}")
        return self._creadores[clave]()

    def crear_al_azar(self, excluir: str | None = None) -> EventoEspecial:
        """Un evento cualquiera, menos el de la clave `excluir` (salvo que sea el único)."""
        opciones = [c for c in self._creadores if c != excluir] or self.claves
        return self.crear(self._azar.choice(opciones))


class ProgramadorEventos:
    """Decide cuándo empieza y termina cada evento. El motor lo llama en cada ciclo."""

    def __init__(
        self,
        fabrica: FabricaEventos | None = None,
        azar: random.Random | None = None,
        primer_evento_s: float = PRIMER_EVENTO_S,
        espera_minima_s: float = ESPERA_MINIMA_S,
        espera_maxima_s: float = ESPERA_MAXIMA_S,
        duracion_s: float = DURACION_EVENTO_S,
    ) -> None:
        self._azar = azar or random.Random()
        self._fabrica = fabrica or FabricaEventos(self._azar)
        self._primer_evento_s = primer_evento_s
        self._espera_minima_s = espera_minima_s
        self._espera_maxima_s = espera_maxima_s
        self._duracion_s = duracion_s
        self._activo: EventoEspecial | None = None
        self._ultimo: str | None = None
        self._restante = 0.0
        self._segundo_mostrado = 0
        self._espera = primer_evento_s

    @property
    def activo(self) -> EventoEspecial | None:
        return self._activo

    def reiniciar(self, motor: ContextoEvento) -> None:
        """Deja todo como al principio. Lo llama el motor cuando empieza la partida."""
        self.cerrar(motor)
        self._ultimo = None
        self._espera = self._primer_evento_s

    def cerrar(self, motor: ContextoEvento) -> None:
        """Si hay un evento en marcha, lo termina y deshace sus efectos (por ejemplo, porque la
        partida acabó a la mitad de un evento)."""
        if self._activo is not None:
            self._terminar_activo(motor)

    def actualizar(self, dt: float, motor: ContextoEvento) -> bool:
        """Avanza el reloj. Devuelve True si hay algo nuevo que mostrar: empezó o terminó un
        evento, o cambió el segundo que marca la cuenta regresiva."""
        if self._activo is not None:
            self._restante -= dt
            if self._restante <= TOLERANCIA_S:
                self._terminar_activo(motor)
                return True
            segundo = math.ceil(round(self._restante, 6))
            if segundo != self._segundo_mostrado:
                self._segundo_mostrado = segundo
                return True
            return False
        self._espera -= dt
        if self._espera <= TOLERANCIA_S:
            self._arrancar(motor)
            return True
        return False

    def a_dict(self) -> dict | None:
        """El evento en marcha para el mensaje de estado, o None si no hay ninguno."""
        if self._activo is None:
            return None
        return {
            "clave": self._activo.clave,
            "nombre": self._activo.nombre,
            "restante": self._segundo_mostrado,
        }

    def _arrancar(self, motor: ContextoEvento) -> None:
        evento = self._fabrica.crear_al_azar(excluir=self._ultimo)
        evento.iniciar(motor)
        self._activo = evento
        self._ultimo = evento.clave
        self._restante = self._duracion_s
        self._segundo_mostrado = math.ceil(self._duracion_s)
        motor.publicar(
            EVENTO_ESPECIAL_INICIADO,
            {"evento": evento.clave, "nombre": evento.nombre, "duracion_s": self._duracion_s},
        )

    def _terminar_activo(self, motor: ContextoEvento) -> None:
        evento = self._activo
        if evento is None:
            return
        self._activo = None
        evento.terminar(motor)
        motor.publicar(
            EVENTO_ESPECIAL_FINALIZADO, {"evento": evento.clave, "nombre": evento.nombre}
        )
        self._espera = self._azar.uniform(self._espera_minima_s, self._espera_maxima_s)