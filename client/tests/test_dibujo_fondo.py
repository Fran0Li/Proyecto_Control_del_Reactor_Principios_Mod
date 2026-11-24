"""Fondos de los mapas (US-09): uno por escenario, ajustado al tamaño de la arena."""

import os

import pygame
import pytest

from src import sprites
from src.screens.dibujo_fondo import FONDOS, TAMANO_ARENA, dibujar_fondo

BLANCO = (255, 255, 255)
ESCENARIOS = (
    "laboratorio",
    "estacion_espacial",
    "planta_industrial",
    "centro_investigacion",
    "complejo_militar",
)


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def carpeta_falsa(tmp_path, monkeypatch):
    """Una carpeta de imágenes de mentira: así la prueba no depende de los fondos reales."""
    monkeypatch.setattr(sprites, "CARPETA", tmp_path)
    sprites.limpiar_cache()
    yield tmp_path
    sprites.limpiar_cache()


def guardar(carpeta, nombre, color, tamano):
    imagen = pygame.Surface(tamano)
    imagen.fill(color)
    pygame.image.save(imagen, str(carpeta / f"{nombre}.png"))


def pantalla_vacia():
    superficie = pygame.Surface((960, 640))
    superficie.fill(BLANCO)
    return superficie


def color(superficie, x, y):
    return tuple(superficie.get_at((x, y)))[:3]


def test_cada_escenario_tiene_su_fondo():
    assert set(FONDOS) == set(ESCENARIOS)
    assert len(set(FONDOS.values())) == len(ESCENARIOS)  # ninguno repetido


def test_estan_las_cinco_imagenes_de_fondo_y_se_pueden_leer():
    for nombre in FONDOS.values():
        assert (sprites.CARPETA / f"{nombre}.png").exists(), f"falta {nombre}.png"
        assert sprites.cargar_fondo(nombre, TAMANO_ARENA) is not None


def test_el_fondo_se_ajusta_al_tamano_de_la_arena(carpeta_falsa):
    guardar(carpeta_falsa, "lab", (10, 20, 30), (1920, 1080))  # más grande que la arena
    fondo = sprites.cargar_fondo("lab", TAMANO_ARENA)
    assert fondo.get_size() == TAMANO_ARENA


def test_un_fondo_mas_chico_tambien_se_estira(carpeta_falsa):
    guardar(carpeta_falsa, "lab", (10, 20, 30), (480, 270))
    assert sprites.cargar_fondo("lab", TAMANO_ARENA).get_size() == TAMANO_ARENA


def test_se_dibuja_el_fondo_del_escenario_en_la_arena(carpeta_falsa):
    guardar(carpeta_falsa, "lab", (10, 20, 30), (960, 540))
    pantalla = pantalla_vacia()
    assert dibujar_fondo(pantalla, "laboratorio") is True
    assert color(pantalla, 0, 0) == (10, 20, 30)
    assert color(pantalla, 959, 539) == (10, 20, 30)
    assert color(pantalla, 480, 600) == BLANCO  # debajo de la arena no se toca


def test_cada_escenario_dibuja_su_propia_imagen(carpeta_falsa):
    colores = {}
    for indice, (escenario, nombre) in enumerate(FONDOS.items()):
        colores[escenario] = (10 * (indice + 1), 50, 90)
        guardar(carpeta_falsa, nombre, colores[escenario], (960, 540))
    for escenario, esperado in colores.items():
        pantalla = pantalla_vacia()
        assert dibujar_fondo(pantalla, escenario)
        assert color(pantalla, 100, 100) == esperado


def test_si_falta_la_imagen_no_dibuja_nada_y_no_falla(carpeta_falsa):
    pantalla = pantalla_vacia()
    assert dibujar_fondo(pantalla, "laboratorio") is False
    assert color(pantalla, 100, 100) == BLANCO


def test_sin_escenario_o_con_uno_desconocido_no_dibuja_nada(carpeta_falsa):
    guardar(carpeta_falsa, "lab", (10, 20, 30), (960, 540))
    for escenario in (None, "", "la_luna"):
        pantalla = pantalla_vacia()
        assert dibujar_fondo(pantalla, escenario) is False
        assert color(pantalla, 100, 100) == BLANCO


def test_un_archivo_danado_no_rompe_el_juego(carpeta_falsa):
    (carpeta_falsa / "lab.png").write_bytes(b"esto no es una imagen")
    assert dibujar_fondo(pantalla_vacia(), "laboratorio") is False