"""Obstáculos de la arena (US-14): qué hace cada tipo con el movimiento del jugador.

- barrera: bloquea el paso.
- trampa: no bloquea, pero frena al jugador mientras la pisa.
- puerta: bloquea mientras está cerrada y se abre y se cierra sola cada cierto tiempo.
"""

import math

from app.realtime.arena import Obstaculo

BARRERA = "barrera"
TRAMPA = "trampa"
PUERTA = "puerta"

FACTOR_TRAMPA = 0.4  # velocidad que conserva el jugador sobre una trampa (40 %)
PUERTA_CERRADA_S = 4.0  # la puerta empieza cerrada
PUERTA_ABIERTA_S = 4.0


def toca(x: float, y: float, radio: float, obstaculo: Obstaculo) -> bool:
    """True si el círculo (x, y, radio) se mete en el rectángulo del obstáculo.
    Rozar el borde no cuenta."""
    cercano_x = min(max(x, obstaculo.x), obstaculo.x + obstaculo.ancho)
    cercano_y = min(max(y, obstaculo.y), obstaculo.y + obstaculo.alto)
    return math.hypot(x - cercano_x, y - cercano_y) < radio


class GestorObstaculos:
    def __init__(
        self,
        obstaculos: list[Obstaculo],
        radio_jugador: float,
        cerrada_s: float = PUERTA_CERRADA_S,
        abierta_s: float = PUERTA_ABIERTA_S,
    ) -> None:
        self._obstaculos = list(obstaculos)
        self._radio = radio_jugador
        self._cerrada_s = cerrada_s
        self._abierta_s = abierta_s
        self._tiempo = 0.0
        self._puertas_abiertas = self._calcular_abierta()

    def _calcular_abierta(self) -> bool:
        ciclo = self._cerrada_s + self._abierta_s
        return (self._tiempo % ciclo) >= self._cerrada_s

    @property
    def puertas_abiertas(self) -> bool:
        return self._puertas_abiertas

    def actualizar(self, dt: float) -> bool:
        """Avanza el reloj de las puertas. Devuelve True si cambiaron de abiertas a cerradas
        o al revés, para que el motor avise a los clientes."""
        self._tiempo += dt
        abiertas = self._calcular_abierta()
        cambio = abiertas != self._puertas_abiertas
        self._puertas_abiertas = abiertas
        return cambio

    def _bloquea(self, obstaculo: Obstaculo) -> bool:
        if obstaculo.tipo == BARRERA:
            return True
        return obstaculo.tipo == PUERTA and not self._puertas_abiertas

    def _bloqueado(self, x: float, y: float) -> bool:
        return any(self._bloquea(o) and toca(x, y, self._radio, o) for o in self._obstaculos)

    def factor_velocidad(self, x: float, y: float) -> float:
        """1.0 en suelo libre; FACTOR_TRAMPA si el jugador pisa una trampa."""
        for obstaculo in self._obstaculos:
            if obstaculo.tipo == TRAMPA and toca(x, y, self._radio, obstaculo):
                return FACTOR_TRAMPA
        return 1.0

    def mover(self, x: float, y: float, nuevo_x: float, nuevo_y: float) -> tuple[float, float]:
        """Posición final al ir de (x, y) hacia (nuevo_x, nuevo_y): si algo bloquea, el jugador
        se desliza por el eje que queda libre. Si ya estaba dentro de un bloqueo (por ejemplo,
        se le cerró una puerta encima), puede salir moviéndose."""
        if self._bloqueado(x, y):
            return nuevo_x, nuevo_y
        if not self._bloqueado(nuevo_x, nuevo_y):
            return nuevo_x, nuevo_y
        if not self._bloqueado(nuevo_x, y):
            return nuevo_x, y
        if not self._bloqueado(x, nuevo_y):
            return x, nuevo_y
        return x, y

    def a_dicts(self) -> list[dict]:
        """Los obstáculos para el mensaje de estado. Las puertas llevan `abierta`."""
        resultado = []
        for obstaculo in self._obstaculos:
            datos = obstaculo.a_dict()
            if obstaculo.tipo == PUERTA:
                datos["abierta"] = self._puertas_abiertas
            resultado.append(datos)
        return resultado