"""Retos de la partida (US-27, criterio 3): metas que dan puntos extra en el momento.

A diferencia de los logros, que se guardan al terminar la partida y duran para siempre, un reto
se cumple *durante* una partida y suma puntos a esa partida. Cada reto se puede cumplir una vez
por jugador y por partida. Lo de antes de iniciar la partida no cuenta (igual que los logros).

`GestorRetos` es otro Subscriber del motor (Observer, ADR 0006): escucha los eventos que ya
existían (`partida_iniciada`, `accion_realizada`, `jugador_penalizado`, `estado_actualizado`) y,
cuando alguien cumple un reto, suma los puntos con `motor.sumar_puntaje` y publica
`reto_completado`. Los puntos cuentan para el ganador porque las reglas de victoria (US-17) leen
los puntajes en cada tick. Agregar un reto es agregar una entrada a CATALOGO y su regla aquí.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Protocol

from app.realtime.eventos import (
    ACCION_REALIZADA,
    ESTADO_ACTUALIZADO,
    JUGADOR_PENALIZADO,
    PARTIDA_FINALIZADA,
    PARTIDA_INICIADA,
    RETO_COMPLETADO,
    EventoPartida,
)

# Racha nuclear: sacar 50 de energía del reactor en 15 segundos
ENERGIA_RACHA = 50
VENTANA_RACHA_S = 15.0
# Sin rasguños: 60 segundos seguidos sin que te alcance un guardián
SEGUNDOS_SIN_RASGUNOS = 60.0


@dataclass(frozen=True)
class Reto:
    clave: str
    nombre: str
    descripcion: str
    puntos: int


CATALOGO: tuple[Reto, ...] = (
    Reto(
        "racha_nuclear",
        "Racha nuclear",
        f"Sacá {ENERGIA_RACHA} de energía del reactor en {VENTANA_RACHA_S:.0f} segundos.",
        25,
    ),
    Reto(
        "primera_chispa",
        "Primera chispa",
        "Sé el primero en sacar energía del reactor después de iniciar la partida.",
        10,
    ),
    Reto(
        "sin_rasgunos",
        "Sin rasguños",
        f"Aguantá {SEGUNDOS_SIN_RASGUNOS:.0f} segundos seguidos sin que te alcance un guardián.",
        30,
    ),
)
POR_CLAVE = {reto.clave: reto for reto in CATALOGO}


class MotorConPuntaje(Protocol):
    """Lo que los retos necesitan del motor (así se prueban con un motor falso)."""

    @property
    def transcurrido(self) -> float: ...

    def sumar_puntaje(self, jugador_id: int, puntos: int) -> None: ...

    def publicar(self, tipo: str, datos: dict) -> None: ...


@dataclass
class _Progreso:
    extracciones: deque = field(default_factory=deque)  # (segundo, energía) dentro de la ventana
    sin_golpes_desde: float = 0.0
    cumplidos: set[str] = field(default_factory=set)


class GestorRetos:
    def __init__(self, motor: MotorConPuntaje) -> None:
        self._motor = motor
        self._activa = False  # solo entre partida_iniciada y partida_finalizada
        self._progreso: dict[int, _Progreso] = {}
        self._hubo_extraccion = False

    def progreso(self, jugador_id: int) -> _Progreso:
        if jugador_id not in self._progreso:
            self._progreso[jugador_id] = _Progreso(sin_golpes_desde=self._motor.transcurrido)
        return self._progreso[jugador_id]

    def cumplidos(self, jugador_id: int) -> set[str]:
        return set(self.progreso(jugador_id).cumplidos)

    async def al_evento(self, evento: EventoPartida) -> None:
        if evento.tipo == PARTIDA_INICIADA:
            self._activa = True
            self._progreso.clear()
            self._hubo_extraccion = False
            for jugador_id in evento.datos.get("jugadores", []):
                self.progreso(int(jugador_id))  # el reloj de "sin rasguños" arranca ya
            return
        if evento.tipo == PARTIDA_FINALIZADA:
            self._activa = False
            return
        if not self._activa:
            return  # practicar antes de iniciar no cuenta
        if evento.tipo == ACCION_REALIZADA and evento.datos.get("accion") == "reactor":
            self._al_extraer(int(evento.datos["jugador_id"]), int(evento.datos["puntos"]))
        elif evento.tipo == JUGADOR_PENALIZADO:
            self.progreso(
                int(evento.datos["jugador_id"])
            ).sin_golpes_desde = self._motor.transcurrido
        elif evento.tipo == ESTADO_ACTUALIZADO:
            # llega al menos una vez por segundo mientras corre el reloj
            for jugador in evento.datos.get("jugadores", []):
                self._revisar_sin_rasgunos(int(jugador["jugador_id"]))

    def _al_extraer(self, jugador_id: int, energia: int) -> None:
        if not self._hubo_extraccion:
            self._hubo_extraccion = True
            self._cumplir(jugador_id, "primera_chispa")
        ahora = self._motor.transcurrido
        racha = self.progreso(jugador_id).extracciones
        racha.append((ahora, energia))
        while racha and ahora - racha[0][0] > VENTANA_RACHA_S:
            racha.popleft()
        if sum(e for _, e in racha) >= ENERGIA_RACHA:
            self._cumplir(jugador_id, "racha_nuclear")

    def _revisar_sin_rasgunos(self, jugador_id: int) -> None:
        progreso = self.progreso(jugador_id)
        if self._motor.transcurrido - progreso.sin_golpes_desde >= SEGUNDOS_SIN_RASGUNOS:
            self._cumplir(jugador_id, "sin_rasgunos")

    def _cumplir(self, jugador_id: int, clave: str) -> None:
        progreso = self.progreso(jugador_id)
        if clave in progreso.cumplidos:
            return
        progreso.cumplidos.add(clave)
        reto = POR_CLAVE[clave]
        self._motor.sumar_puntaje(jugador_id, reto.puntos)
        self._motor.publicar(
            RETO_COMPLETADO,
            {
                "jugador_id": jugador_id,
                "reto": reto.clave,
                "nombre": reto.nombre,
                "puntos": reto.puntos,
            },
        )
