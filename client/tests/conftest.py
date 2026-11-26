"""Configuración común de las pruebas del cliente."""

import pytest

from src import sprites
from src.screens import componentes


@pytest.fixture(autouse=True)
def sin_sprites_del_reactor_y_la_celda(monkeypatch, request):
    """Las pruebas que miran colores exactos dibujan sin los sprites del reactor y de la celda
    (figuras de siempre). Las que sí quieren los sprites piden la fixture `con_sprites_extra`."""
    if "con_sprites_extra" in request.fixturenames:
        return
    cargar_real = sprites.cargar

    def cargar(nombre, tamano=None):
        if nombre.startswith("extra/"):
            return None
        return cargar_real(nombre, tamano)

    monkeypatch.setattr(sprites, "cargar", cargar)


@pytest.fixture
def con_sprites_extra():
    """Marca la prueba para que use los sprites de assets/sprites/extra."""


@pytest.fixture(autouse=True)
def toques_limpios():
    """Cada prueba empieza sin haber visto dedos (si no, los clics de mouse se ignorarían)."""
    componentes.reiniciar_toques()
    yield
    componentes.reiniciar_toques()
