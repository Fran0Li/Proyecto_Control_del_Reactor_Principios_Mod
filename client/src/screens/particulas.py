"""Partículas de impacto cuando un guardián alcanza a un jugador (efecto visual, parte de US-29).

Patrón **Flyweight** (estructural): cada explosión crea decenas de partículas, pero casi todo lo
que las describe se repite. Eso se separa en dos:

- **Estado intrínseco (compartido):** `TipoParticula` guarda el color, el tamaño, cuánto dura y
  la imagen ya dibujada. Hay un objeto por combinación y lo entrega `FabricaTiposParticula`, que
  lo reutiliza: mil partículas moradas de 3 px comparten un solo `TipoParticula`.
- **Estado extrínseco (de cada una):** `Particula` solo guarda posición, velocidad, edad y una
  referencia a su tipo.

Así cada partícula es liviana y la imagen se dibuja una sola vez por tipo, no una vez por
partícula ni por cuadro. La lógica no depende de la ventana: el azar y el tiempo se inyectan,
por eso se prueba sin pantalla.
"""

import math
import random
from dataclasses import dataclass

import pygame

MORADO = (190, 90, 255)
LILA = (235, 190, 255)
AMARILLO = (255, 215, 60)
BLANCO = (255, 255, 255)

PARTICULAS_POR_IMPACTO = 28
VELOCIDAD_MIN, VELOCIDAD_MAX = 60.0, 190.0  # px por segundo
FRICCION = 2.5  # cuánto frenan por segundo (se van quedando quietas)
ONDA_S = 0.3  # la onda del golpe: un aro que crece y se desvanece
ONDA_RADIO_INICIAL, ONDA_RADIO_FINAL = 18, 48


@dataclass(frozen=True)
class TipoParticula:
    """Flyweight: lo que comparten todas las partículas de un mismo color y tamaño."""

    color: tuple[int, int, int]
    radio: int
    vida_s: float

    def imagen(self) -> pygame.Surface:
        lado = 2 * self.radio
        superficie = pygame.Surface((lado, lado), pygame.SRCALPHA)
        pygame.draw.circle(superficie, (*self.color, 255), (self.radio, self.radio), self.radio)
        return superficie


class FabricaTiposParticula:
    """Entrega siempre el mismo `TipoParticula` (y su imagen) para los mismos datos."""

    def __init__(self) -> None:
        self._tipos: dict[tuple, TipoParticula] = {}
        self._imagenes: dict[TipoParticula, pygame.Surface] = {}

    def obtener(self, color: tuple[int, int, int], radio: int, vida_s: float) -> TipoParticula:
        clave = (color, radio, vida_s)
        if clave not in self._tipos:
            self._tipos[clave] = TipoParticula(color, radio, vida_s)
        return self._tipos[clave]

    def imagen(self, tipo: TipoParticula) -> pygame.Surface:
        if tipo not in self._imagenes:
            self._imagenes[tipo] = tipo.imagen()
        return self._imagenes[tipo]

    @property
    def cantidad_tipos(self) -> int:
        return len(self._tipos)


@dataclass
class Particula:
    """Estado extrínseco: lo único propio de cada partícula."""

    x: float
    y: float
    vx: float
    vy: float
    tipo: TipoParticula
    edad: float = 0.0

    @property
    def viva(self) -> bool:
        return self.edad < self.tipo.vida_s

    @property
    def opacidad(self) -> int:
        return max(0, min(255, int(255 * (1 - self.edad / self.tipo.vida_s))))


class SistemaParticulas:
    def __init__(self, azar: random.Random | None = None) -> None:
        self._azar = azar or random.Random()
        self.fabrica = FabricaTiposParticula()
        self.particulas: list[Particula] = []
        self.ondas: list[list[float]] = []  # [x, y, edad]
        # pocos tipos para muchas partículas: chispas moradas, lilas, amarillas y destellos
        self._tipos_impacto = [
            self.fabrica.obtener(MORADO, 3, 0.7),
            self.fabrica.obtener(MORADO, 2, 0.5),
            self.fabrica.obtener(LILA, 2, 0.6),
            self.fabrica.obtener(AMARILLO, 2, 0.45),
            self.fabrica.obtener(BLANCO, 1, 0.35),
        ]

    def impacto(self, x: float, y: float, cantidad: int = PARTICULAS_POR_IMPACTO) -> None:
        """Explosión de chispas en todas las direcciones desde (x, y), con una onda."""
        self.ondas.append([x, y, 0.0])
        for i in range(cantidad):
            angulo = 2 * math.pi * i / cantidad + self._azar.uniform(-0.3, 0.3)
            rapidez = self._azar.uniform(VELOCIDAD_MIN, VELOCIDAD_MAX)
            tipo = self._azar.choice(self._tipos_impacto)
            self.particulas.append(
                Particula(x, y, math.cos(angulo) * rapidez, math.sin(angulo) * rapidez, tipo)
            )

    def actualizar(self, dt: float) -> None:
        if dt <= 0:
            return
        freno = max(0.0, 1 - FRICCION * dt)
        for p in self.particulas:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= freno
            p.vy *= freno
            p.edad += dt
        self.particulas = [p for p in self.particulas if p.viva]
        for onda in self.ondas:
            onda[2] += dt
        self.ondas = [o for o in self.ondas if o[2] < ONDA_S]

    def dibujar(self, pantalla: pygame.Surface) -> None:
        for x, y, edad in self.ondas:
            avance = edad / ONDA_S
            radio = int(ONDA_RADIO_INICIAL + (ONDA_RADIO_FINAL - ONDA_RADIO_INICIAL) * avance)
            lado = 2 * radio + 2
            aro = pygame.Surface((lado, lado), pygame.SRCALPHA)
            pygame.draw.circle(
                aro, (*MORADO, int(200 * (1 - avance))), (radio + 1, radio + 1), radio, 3
            )
            pantalla.blit(aro, (int(x) - radio - 1, int(y) - radio - 1))
        for p in self.particulas:
            imagen = self.fabrica.imagen(p.tipo)
            imagen.set_alpha(p.opacidad)  # la imagen es compartida: se ajusta justo antes
            radio = p.tipo.radio
            pantalla.blit(imagen, (int(p.x) - radio, int(p.y) - radio))

    def vaciar(self) -> None:
        self.particulas = []
        self.ondas = []
