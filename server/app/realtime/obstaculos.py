"""Obstáculos de la arena (US-14): qué hace cada tipo con el movimiento del jugador.

- barrera: bloquea el paso.
- trampa: no bloquea, pero frena al jugador mientras la pisa.
- puerta: bloquea mientras está cerrada y se abre y se cierra sola cada cierto tiempo.
- barrera móvil: bloquea como una barrera, pero va y viene en línea recta entre dos puntos.
"""

import math
from dataclasses import replace

from app.realtime.arena import Obstaculo

BARRERA = "barrera"
TRAMPA = "trampa"
PUERTA = "puerta"
BARRERA_MOVIL = "barrera_movil"

FACTOR_TRAMPA = 0.4  # velocidad que conserva el jugador sobre una trampa (40 %)
PUERTA_CERRADA_S = 4.0  # la puerta empieza cerrada
PUERTA_ABIERTA_S = 4.0
VELOCIDAD_BARRERA_MOVIL = 30.0  # px por segundo: el jugador (120) puede rebasarla con facilidad


def toca(x: float, y: float, radio: float, obstaculo: Obstaculo) -> bool:
    """True si el círculo (x, y, radio) se mete en el rectángulo del obstáculo.
    Rozar el borde no cuenta."""
    cercano_x = min(max(x, obstaculo.x), obstaculo.x + obstaculo.ancho)
    cercano_y = min(max(y, obstaculo.y), obstaculo.y + obstaculo.alto)
    return math.hypot(x - cercano_x, y - cercano_y) < radio


def posicion_en(obstaculo: Obstaculo, tiempo: float, velocidad: float) -> Obstaculo:
    """El obstáculo donde está pasados `tiempo` segundos. Los que no se mueven no cambian.
    Una barrera móvil va del punto inicial al destino y vuelve, sin parar, a `velocidad` px/s."""
    destino_x, destino_y = obstaculo.destino_x, obstaculo.destino_y
    if obstaculo.tipo != BARRERA_MOVIL or destino_x is None or destino_y is None:
        return obstaculo
    dx = destino_x - obstaculo.x
    dy = destino_y - obstaculo.y
    distancia = math.hypot(dx, dy)
    if distancia == 0:
        return obstaculo
    recorrido = (tiempo * velocidad) % (2 * distancia)
    avance = recorrido if recorrido <= distancia else 2 * distancia - recorrido
    fraccion = avance / distancia
    return replace(obstaculo, x=obstaculo.x + dx * fraccion, y=obstaculo.y + dy * fraccion)


class GestorObstaculos:
    def __init__(
        self,
        obstaculos: list[Obstaculo],
        radio_jugador: float,
        cerrada_s: float = PUERTA_CERRADA_S,
        abierta_s: float = PUERTA_ABIERTA_S,
        velocidad_movil: float = VELOCIDAD_BARRERA_MOVIL,
    ) -> None:
        self._obstaculos = list(obstaculos)  # donde empieza cada uno
        self._radio = radio_jugador
        self._cerrada_s = cerrada_s
        self._abierta_s = abierta_s
        self._velocidad_movil = velocidad_movil
        self._hay_puertas = any(o.tipo == PUERTA for o in self._obstaculos)
        self._hay_moviles = any(o.tipo == BARRERA_MOVIL for o in self._obstaculos)
        self._tiempo = 0.0
        self._puertas_abiertas = self._calcular_abierta()
        self._actuales = self._colocar()  # donde está cada uno ahora

    def _colocar(self) -> list[Obstaculo]:
        return [posicion_en(o, self._tiempo, self._velocidad_movil) for o in self._obstaculos]

    def _calcular_abierta(self) -> bool:
        ciclo = self._cerrada_s + self._abierta_s
        return (self._tiempo % ciclo) >= self._cerrada_s

    @property
    def puertas_abiertas(self) -> bool:
        return self._puertas_abiertas

    def actualizar(self, dt: float) -> bool:
        """Avanza el reloj de las puertas y de las barreras móviles. Devuelve True si algo
        cambió y hay que avisar a los clientes: una puerta se abrió o se cerró, o una barrera
        móvil se movió. Sin puertas ni barreras móviles nunca hay cambio."""
        self._tiempo += dt
        abiertas = self._calcular_abierta()
        cambio = (self._hay_puertas and abiertas != self._puertas_abiertas) or self._hay_moviles
        self._puertas_abiertas = abiertas
        if self._hay_moviles:
            self._actuales = self._colocar()
        return cambio

    def _bloquea(self, obstaculo: Obstaculo) -> bool:
        if obstaculo.tipo in (BARRERA, BARRERA_MOVIL):
            return True
        return obstaculo.tipo == PUERTA and not self._puertas_abiertas

    def _bloqueado(self, x: float, y: float) -> bool:
        return any(self._bloquea(o) and toca(x, y, self._radio, o) for o in self._actuales)

    def factor_velocidad(self, x: float, y: float) -> float:
        """1.0 en suelo libre; FACTOR_TRAMPA si el jugador pisa una trampa."""
        for obstaculo in self._actuales:
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
        """Los obstáculos para el mensaje de estado, donde están ahora. Las puertas llevan
        `abierta`."""
        resultado = []
        for obstaculo in self._actuales:
            datos = obstaculo.a_dict()
            if obstaculo.tipo == PUERTA:
                datos["abierta"] = self._puertas_abiertas
            resultado.append(datos)
        return resultado