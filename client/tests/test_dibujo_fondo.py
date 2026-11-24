"""Fondos de los mapas (US-09): uno por escenario, ajustado al tamaño de la arena."""

import os

import pygame
import pytest

from src import sprites
from src.screens import buscar_partida, ceremonia, formulario, lobby
from src.screens.buscar_partida import BuscarPartidaScreen
from src.screens.ceremonia import CeremoniaScreen
from src.screens.dibujo_fondo import (
    FONDO_MENU,
    FONDOS,
    TAMANO_ARENA,
    VELO_MENU,
    dibujar_fondo,
    dibujar_fondo_menu,
)
from src.screens.lobby import LobbyScreen
from src.screens.login import LoginScreen
from src.screens.perfil import PerfilScreen
from src.screens.recuperar import RecuperarScreen
from src.screens.registro import RegistroScreen
from src.screens.verificar_correo import VerificarCorreoScreen

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


# fondo de las pantallas que no son de partida

COLOR_LISO = (12, 16, 32)  # el color de siempre, cuando no hay imagen


def ventana(tamano=(960, 640)):
    superficie = pygame.Surface(tamano)
    superficie.fill(BLANCO)
    return superficie


def test_esta_la_imagen_del_fondo_de_los_menus():
    assert (sprites.CARPETA / f"{FONDO_MENU}.png").exists()
    assert sprites.cargar_fondo(FONDO_MENU, (960, 640)) is not None


def test_el_fondo_de_los_menus_cubre_toda_la_ventana(carpeta_falsa):
    guardar(carpeta_falsa, FONDO_MENU, (200, 0, 0), (1440, 960))
    pantalla = ventana()
    assert dibujar_fondo_menu(pantalla, COLOR_LISO) is True
    for punto in ((0, 0), (959, 0), (0, 639), (959, 639), (480, 320)):
        rojo, verde, azul = color(pantalla, *punto)
        assert rojo > 120 and verde < 40  # se ve la imagen, no el color liso ni el blanco


def test_el_velo_oscurece_un_poco_la_imagen(carpeta_falsa):
    guardar(carpeta_falsa, FONDO_MENU, (200, 200, 200), (960, 640))
    pantalla = ventana()
    dibujar_fondo_menu(pantalla, COLOR_LISO)
    rojo = color(pantalla, 10, 10)[0]
    assert VELO_MENU[0] < rojo < 200  # más oscuro que la imagen, pero no tapa


def test_sin_imagen_el_menu_se_pinta_con_el_color_liso(carpeta_falsa):
    pantalla = ventana()
    assert dibujar_fondo_menu(pantalla, COLOR_LISO) is False
    assert color(pantalla, 10, 10) == COLOR_LISO
    assert color(pantalla, 959, 639) == COLOR_LISO


def test_un_archivo_danado_deja_el_color_liso(carpeta_falsa):
    (carpeta_falsa / f"{FONDO_MENU}.png").write_bytes(b"esto no es una imagen")
    pantalla = ventana()
    assert dibujar_fondo_menu(pantalla, COLOR_LISO) is False
    assert color(pantalla, 10, 10) == COLOR_LISO


def test_el_fondo_de_los_menus_se_ajusta_a_otro_tamano_de_ventana(carpeta_falsa):
    guardar(carpeta_falsa, FONDO_MENU, (200, 0, 0), (960, 640))
    pantalla = ventana((480, 320))
    assert dibujar_fondo_menu(pantalla, COLOR_LISO) is True
    assert color(pantalla, 479, 319)[0] > 120


PANTALLAS = {
    "login": lambda: LoginScreen(960),
    "registro": lambda: RegistroScreen(960),
    "verificar_correo": lambda: VerificarCorreoScreen(960),
    "recuperar": lambda: RecuperarScreen(960),
    "perfil": lambda: PerfilScreen(960),
    "lobby": lambda: LobbyScreen(960),
    "buscar_partida": lambda: BuscarPartidaScreen(960),
    "ceremonia": lambda: CeremoniaScreen(960, 640),
}


@pytest.mark.parametrize("nombre", PANTALLAS)
def test_toda_pantalla_que_no_es_de_partida_dibuja_el_fondo_de_los_menus(nombre, carpeta_falsa):
    guardar(carpeta_falsa, FONDO_MENU, (200, 0, 0), (960, 640))
    pantalla = PANTALLAS[nombre]()
    superficie = ventana()
    pantalla.draw(superficie)
    assert color(superficie, 3, 3)[0] > 120  # la esquina de arriba a la izquierda es la imagen
    assert color(superficie, 956, 636)[0] > 120


@pytest.mark.parametrize("nombre", PANTALLAS)
def test_toda_pantalla_sin_imagen_sigue_con_el_color_liso(nombre, carpeta_falsa):
    pantalla = PANTALLAS[nombre]()
    superficie = ventana()
    pantalla.draw(superficie)
    assert color(superficie, 3, 3) == COLOR_LISO


def test_los_modulos_de_las_pantallas_usan_el_mismo_color_liso():
    for modulo in (formulario, lobby, buscar_partida, ceremonia):
        assert modulo.COLOR_FONDO == COLOR_LISO