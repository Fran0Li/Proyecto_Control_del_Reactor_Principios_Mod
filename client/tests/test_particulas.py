"""Partículas de impacto cuando un guardián alcanza a un jugador (Flyweight)."""

import os
import random

import pygame
import pytest

from src.screens.arena import ArenaScreen
from src.screens.particulas import (
    ONDA_S,
    PARTICULAS_POR_IMPACTO,
    FabricaTiposParticula,
    SistemaParticulas,
)
from tests.test_arena import ALTO, ANCHO, PanelFalso

BLANCO = (255, 255, 255)


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    yield
    pygame.quit()


def sistema():
    return SistemaParticulas(random.Random(7))


# --- Flyweight ----------------------------------------------------------------------------------


def test_la_fabrica_reutiliza_el_mismo_tipo_para_los_mismos_datos():
    fabrica = FabricaTiposParticula()
    uno = fabrica.obtener((255, 0, 0), 3, 0.5)
    otro = fabrica.obtener((255, 0, 0), 3, 0.5)
    distinto = fabrica.obtener((0, 0, 255), 3, 0.5)
    assert uno is otro
    assert distinto is not uno
    assert fabrica.cantidad_tipos == 2
    assert fabrica.imagen(uno) is fabrica.imagen(otro)  # la imagen se dibuja una vez


def test_muchas_particulas_comparten_pocos_tipos():
    s = sistema()
    for _ in range(10):
        s.impacto(100, 100)
    assert len(s.particulas) == 10 * PARTICULAS_POR_IMPACTO
    tipos = {id(p.tipo) for p in s.particulas}
    assert len(tipos) <= s.fabrica.cantidad_tipos <= 5


# --- comportamiento -----------------------------------------------------------------------------


def test_el_impacto_lanza_chispas_en_todas_direcciones():
    s = sistema()
    s.impacto(200, 150)
    s.actualizar(0.1)
    assert any(p.x < 200 for p in s.particulas) and any(p.x > 200 for p in s.particulas)
    assert any(p.y < 150 for p in s.particulas) and any(p.y > 150 for p in s.particulas)


def test_las_chispas_se_desvanecen_y_desaparecen():
    s = sistema()
    s.impacto(200, 150)
    p = s.particulas[0]
    s.actualizar(0.2)
    assert p.opacidad < 255
    for _ in range(20):
        s.actualizar(0.1)  # 2 s: más que la vida de cualquier chispa
    assert s.particulas == []
    assert s.ondas == []


def test_la_onda_dura_poco():
    s = sistema()
    s.impacto(10, 10)
    assert len(s.ondas) == 1
    s.actualizar(ONDA_S + 0.01)
    assert s.ondas == []


def test_dibuja_cerca_del_impacto():
    s = sistema()
    s.impacto(150, 100)
    s.actualizar(0.05)
    pantalla = pygame.Surface((300, 200))
    pantalla.fill(BLANCO)
    s.dibujar(pantalla)
    zona = [(x, y) for x in range(100, 200) for y in range(50, 150)]
    assert any(tuple(pantalla.get_at(p))[:3] != BLANCO for p in zona)
    assert tuple(pantalla.get_at((5, 5)))[:3] == BLANCO


def test_sin_tiempo_no_se_mueven():
    s = sistema()
    s.impacto(50, 50)
    s.actualizar(0)
    assert all((p.x, p.y) == (50, 50) for p in s.particulas)


# --- en la arena --------------------------------------------------------------------------------


class Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def arena_con_jugador(estado="normal"):
    reloj = Reloj()
    panel = PanelFalso([(1, 240, 135)])
    panel.estado["jugadores"][0]["estado"] = estado
    arena = ArenaScreen(ANCHO, ALTO, reloj=reloj)
    arena.preparar(panel, "lobby")
    arena.update()
    return arena, panel, reloj


def poner_estado(panel, estado):
    panel.estado["jugadores"][0]["estado"] = estado


def test_cuando_un_guardian_alcanza_al_jugador_salen_chispas():
    arena, panel, reloj = arena_con_jugador("normal")
    assert arena.particulas.particulas == []

    poner_estado(panel, "aturdido")
    reloj.t += 0.016
    arena.update()

    assert len(arena.particulas.particulas) == PARTICULAS_POR_IMPACTO


def test_seguir_aturdido_no_lanza_mas_chispas():
    arena, panel, reloj = arena_con_jugador("normal")
    poner_estado(panel, "aturdido")
    arena.update()
    cantidad = len(arena.particulas.particulas)

    for _ in range(5):
        arena.update()

    assert len(arena.particulas.particulas) == cantidad


def test_un_jugador_que_llega_ya_aturdido_no_lanza_chispas():
    arena, _, _ = arena_con_jugador("aturdido")
    assert arena.particulas.particulas == []


def test_otro_golpe_despues_de_recuperarse_vuelve_a_lanzar_chispas():
    arena, panel, reloj = arena_con_jugador("normal")
    for estado in ("aturdido", "escudado", "normal", "aturdido"):
        poner_estado(panel, estado)
        reloj.t += 0.016
        arena.update()
    assert len(arena.particulas.particulas) == 2 * PARTICULAS_POR_IMPACTO


def test_las_chispas_se_mueven_con_el_reloj_de_la_arena_y_se_borran_al_salir():
    arena, panel, reloj = arena_con_jugador("normal")
    poner_estado(panel, "aturdido")
    arena.update()
    for _ in range(30):
        reloj.t += 0.1
        arena.update()
    assert arena.particulas.particulas == []

    poner_estado(panel, "normal")
    arena.update()
    poner_estado(panel, "aturdido")
    arena.update()
    arena.cerrar()
    assert arena.particulas.particulas == []
