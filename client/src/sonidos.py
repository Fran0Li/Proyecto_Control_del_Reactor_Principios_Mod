"""Sonidos de la partida (US-29): efectos generados en código y la música de fondo.

- `DetectorSonidos` decide qué sonó comparando un estado del servidor con el anterior. No usa
  pygame, así se prueba sin audio.
- `Sonidos` los reproduce. Los efectos se sintetizan al primer uso (sin archivos); la música es
  `assets/audio/musica_partida.ogg`, los primeros 40 s de "Reactors at Critical", en bucle.
- Si no hay audio (pruebas, navegador sin permiso), no suena nada y el juego sigue igual.
"""

import array
import math
import random
from collections.abc import Callable
from pathlib import Path

import pygame

MUSICA_PARTIDA = Path(__file__).resolve().parent.parent / "assets" / "audio" / "musica_partida.ogg"
VOLUMEN_MUSICA = 0.35
VOLUMEN_EFECTOS = 0.6

EXTRACCION = "extraccion"  # el jugador sacó energía del reactor
CELDA = "celda"  # el jugador recogió una bolita de energía
GOLPE = "golpe"  # un guardián alcanzó a alguien
EVENTO = "evento"  # empezó un evento especial (puntos dobles, invasión)


class DetectorSonidos:
    """Compara cada estado con el anterior y dice qué sonidos tocan."""

    def __init__(self) -> None:
        self._anterior: dict | None = None

    def reiniciar(self) -> None:
        self._anterior = None

    def revisar(self, estado: dict, mi_id: int | None) -> list[str]:
        anterior, self._anterior = self._anterior, estado
        if anterior is None:
            return []  # el primer estado solo sirve de referencia
        sonidos = []
        sumo = _puntaje(estado, mi_id) > _puntaje(anterior, mi_id)
        if sumo and _energia(estado) < _energia(anterior):
            sonidos.append(EXTRACCION)
        if sumo and _celdas(estado) < _celdas(anterior):
            sonidos.append(CELDA)
        if _aturdidos(estado) - _aturdidos(anterior):
            sonidos.append(GOLPE)
        evento = _evento(estado)
        if evento is not None and evento != _evento(anterior):
            sonidos.append(EVENTO)
        return sonidos


def _puntaje(estado: dict, jugador_id: int | None) -> int:
    for jugador in estado.get("jugadores", []):
        if jugador.get("jugador_id") == jugador_id:
            return jugador.get("puntaje", 0)
    return 0


def _energia(estado: dict) -> float:
    return (estado.get("reactor") or {}).get("energia", 0)


def _celdas(estado: dict) -> set:
    return {c.get("id") for c in (estado.get("arena") or {}).get("celdas", [])}


def _aturdidos(estado: dict) -> set:
    return {
        j.get("jugador_id") for j in estado.get("jugadores", []) if j.get("estado") == "aturdido"
    }


def _evento(estado: dict) -> str | None:
    evento = (estado.get("partida") or {}).get("evento")
    return evento.get("nombre") if isinstance(evento, dict) else None


# síntesis de los efectos (ondas simples, como la fanfarria de la ceremonia)


def _onda(frecuencia_en: Callable[[float], float], duracion: float, ruido: float = 0.0):
    """Muestras de una onda cuya frecuencia cambia con el tiempo t (0 a 1) y se apaga al final."""
    tasa, _, canales = pygame.mixer.get_init()
    total = int(tasa * duracion)
    muestras = array.array("h")
    fase = 0.0
    azar = random.Random(7)
    for i in range(total):
        t = i / total
        fase += math.tau * frecuencia_en(t) / tasa
        valor = math.sin(fase) * (1 - ruido) + azar.uniform(-1, 1) * ruido
        envolvente = min(1.0, i / (tasa * 0.005)) * (1 - t)  # sin chasquido al empezar
        muestras.extend([int(9000 * envolvente * valor)] * canales)
    return muestras


def _sintetizar(nombre: str) -> pygame.mixer.Sound:
    if nombre == EXTRACCION:  # zumbido que sube
        muestras = _onda(lambda t: 300 + 700 * t, 0.18)
    elif nombre == CELDA:  # dos notas cortas y agudas
        muestras = _onda(lambda t: 880 if t < 0.5 else 1320, 0.14)
    elif nombre == GOLPE:  # golpe grave que baja, con ruido
        muestras = _onda(lambda t: 420 - 340 * t, 0.35, ruido=0.45)
    else:  # alarma de dos tonos para los eventos especiales
        muestras = _onda(lambda t: 660 if int(t * 4) % 2 == 0 else 880, 0.6)
    return pygame.mixer.Sound(buffer=muestras.tobytes())


class Sonidos:
    def __init__(self) -> None:
        self._efectos: dict[str, pygame.mixer.Sound] = {}
        self.silenciado = False

    def _hay_audio(self) -> bool:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            return bool(pygame.mixer.get_init())
        except pygame.error:
            return False

    def _efecto(self, nombre: str) -> pygame.mixer.Sound:
        if nombre not in self._efectos:
            self._efectos[nombre] = _sintetizar(nombre)
            self._efectos[nombre].set_volume(VOLUMEN_EFECTOS)
        return self._efectos[nombre]

    def precargar(self) -> None:
        """Genera los efectos de una vez al entrar a la arena, para que el primer golpe o la
        primera extracción no hagan una pausa (en el navegador generar es más lento)."""
        if not self._hay_audio():
            return
        try:
            for nombre in (EXTRACCION, CELDA, GOLPE, EVENTO):
                self._efecto(nombre)
        except (pygame.error, TypeError, ValueError):
            pass

    def reproducir(self, nombre: str) -> bool:
        if self.silenciado or not self._hay_audio():
            return False
        try:
            self._efecto(nombre).play()
            return True
        except (pygame.error, TypeError, ValueError):
            return False

    def iniciar_musica(self) -> bool:
        if self.silenciado or not MUSICA_PARTIDA.exists() or not self._hay_audio():
            return False
        try:
            pygame.mixer.music.load(str(MUSICA_PARTIDA))
            pygame.mixer.music.set_volume(VOLUMEN_MUSICA)
            pygame.mixer.music.play(loops=-1)  # los 40 s en bucle
            return True
        except pygame.error:
            return False

    def detener_musica(self) -> None:
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except pygame.error:
            pass

    def alternar_silencio(self) -> bool:
        """Tecla M en la arena. Devuelve True si quedó silenciado."""
        self.silenciado = not self.silenciado
        if self.silenciado:
            self.detener_musica()
        else:
            self.iniciar_musica()
        return self.silenciado


sonidos = Sonidos()  # uno para todo el juego: el silencio se mantiene entre partidas
