"""Carga de las imágenes del juego (assets/sprites), con caché y sin romper si falta una.

Si una imagen no está (o no se puede leer), `cargar` devuelve None y quien dibuja usa la figura
de siempre (círculo o rectángulo). Así el juego y las pruebas funcionan aunque falte un archivo.
La misma carpeta va dentro del paquete del navegador (pygbag empaqueta todo `client/`).

Los sprites son pixel art y se escalan sin suavizar. Los fondos de los mapas son imágenes grandes
y se escalan suavizado (`cargar_fondo`).
"""

from pathlib import Path

import pygame

CARPETA = Path(__file__).resolve().parent.parent / "assets" / "sprites"

_cache: dict[tuple[str, tuple[int, int] | None], pygame.Surface | None] = {}
_cache_fondos: dict[tuple[str, tuple[int, int]], pygame.Surface | None] = {}


def cargar(nombre: str, tamano: tuple[int, int] | None = None) -> pygame.Surface | None:
    """Imagen `nombre`.png escalada a `tamano`, sin suavizar (el pixel art queda nítido)."""
    clave = (nombre, tamano)
    if clave not in _cache:
        _cache[clave] = _leer(nombre, tamano)
    return _cache[clave]


def _leer(nombre: str, tamano: tuple[int, int] | None) -> pygame.Surface | None:
    try:
        imagen = pygame.image.load(str(CARPETA / f"{nombre}.png"))
    except (pygame.error, OSError):
        return None
    if pygame.display.get_surface() is not None:
        imagen = imagen.convert_alpha()  # más rápido al dibujar; requiere una ventana abierta
    if tamano is not None and imagen.get_size() != tamano:
        imagen = pygame.transform.scale(imagen, tamano)
    return imagen


def cargar_fondo(nombre: str, tamano: tuple[int, int]) -> pygame.Surface | None:
    """Fondo `nombre`.png ajustado a `tamano` (suavizado y sin transparencia). None si falta."""
    clave = (nombre, tamano)
    if clave not in _cache_fondos:
        _cache_fondos[clave] = _leer_fondo(nombre, tamano)
    return _cache_fondos[clave]


def _leer_fondo(nombre: str, tamano: tuple[int, int]) -> pygame.Surface | None:
    try:
        imagen = pygame.image.load(str(CARPETA / f"{nombre}.png"))
    except (pygame.error, OSError):
        return None
    if imagen.get_size() != tamano:
        if imagen.get_bitsize() not in (24, 32):  # smoothscale solo escala imágenes de 24 o 32 bits
            plana = pygame.Surface(imagen.get_size(), depth=32)
            plana.blit(imagen, (0, 0))
            imagen = plana
        imagen = pygame.transform.smoothscale(imagen, tamano)
    if pygame.display.get_surface() is not None:
        imagen = imagen.convert()  # un fondo no tiene transparencia: se dibuja más rápido
    return imagen


def limpiar_cache() -> None:
    _cache.clear()
    _cache_fondos.clear()