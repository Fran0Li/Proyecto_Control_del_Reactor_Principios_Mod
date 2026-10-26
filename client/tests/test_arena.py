"""Pruebas de la pantalla de la arena y del botón del panel del canal (US-25)."""

import asyncio
import os

import pygame
import pytest

from src.screens import panel_canal
from src.screens.arena import BLANCO, ROJO, SUAVIZADO, ArenaScreen
from src.screens.panel_canal import PanelCanal

ANCHO, ALTO = 960, 640
ARENA = {"ancho": 960, "alto": 540, "radio": 20}


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    yield
    pygame.quit()


class CanalFalso:
    def __init__(self, estado="abierta"):
        self.estado = estado
        self.enviados = []

    def enviar(self, mensaje):
        self.enviados.append(mensaje)

    def leer_mensajes(self):
        return []

    def cerrar(self):
        self.estado = "cerrada"


class PanelFalso:
    """Lo mínimo del panel del canal que usa la arena."""

    def __init__(self, jugadores=None, canal=True):
        self.canal = CanalFalso() if canal else None
        self.estado = None if jugadores is None else estado_con(jugadores)


def estado_con(jugadores):
    lista = [{"jugador_id": i, "x": x, "y": y} for i, x, y in jugadores]
    return {"tipo": "estado", "jugadores": lista, "arena": ARENA}


def arena_con(panel, ancho=ANCHO, alto=ALTO, volver_a="lobby"):
    arena = ArenaScreen(ancho, alto)
    arena.preparar(panel, volver_a)
    return arena


def dibujar(arena):
    superficie = pygame.Surface((arena.ancho, arena.alto))
    arena.draw(superficie)
    return superficie


def tecla(tipo, clave):
    return pygame.event.Event(tipo, key=clave)


# dibujo 


def test_el_fondo_es_blanco():
    arena = arena_con(PanelFalso([(1, 240, 135)]))
    arena.update()

    pantalla = dibujar(arena)

    assert tuple(pantalla.get_at((10, 10)))[:3] == BLANCO
    assert tuple(pantalla.get_at((480, 300)))[:3] == BLANCO


def test_dibuja_un_circulo_rojo_por_jugador_en_su_posicion():
    arena = arena_con(PanelFalso([(1, 240, 135), (2, 720, 135)]))
    arena.update()

    pantalla = dibujar(arena)

    assert tuple(pantalla.get_at((240, 135)))[:3] == ROJO
    assert tuple(pantalla.get_at((720, 135)))[:3] == ROJO


def test_el_circulo_tiene_el_radio_que_manda_el_servidor():
    arena = arena_con(PanelFalso([(1, 240, 135)]))
    arena.update()

    pantalla = dibujar(arena)

    radio = ARENA["radio"]
    assert tuple(pantalla.get_at((240 + radio - 2, 135)))[:3] == ROJO
    assert tuple(pantalla.get_at((240 + radio + 3, 135)))[:3] == BLANCO


def test_sin_estado_solo_hay_fondo_blanco_y_no_falla():
    arena = arena_con(PanelFalso(jugadores=None))
    arena.update()

    pantalla = dibujar(arena)

    assert tuple(pantalla.get_at((240, 135)))[:3] == BLANCO
    assert tuple(pantalla.get_at((480, 300)))[:3] == BLANCO


def test_sin_canal_no_falla_ni_manda_teclas():
    arena = arena_con(PanelFalso(jugadores=[(1, 240, 135)], canal=False))
    arena.update()

    dibujar(arena)

    assert arena.controles is None  # sin canal no hay a dónde mandar las teclas


#  suavizado


def test_la_primera_vez_aparece_en_su_lugar_y_despues_se_acerca_sin_saltar():
    panel = PanelFalso([(1, 240, 135)])
    arena = arena_con(panel)
    arena.update()
    assert arena.visuales[1] == [240.0, 135.0]

    panel.estado = estado_con([(1, 300, 135)])
    arena.update()
    paso = arena.visuales[1][0]

    assert paso == pytest.approx(240 + 60 * SUAVIZADO)
    for _ in range(40):
        arena.update()
    assert arena.visuales[1][0] == pytest.approx(300, abs=0.01)


def test_quien_se_va_deja_de_dibujarse():
    panel = PanelFalso([(1, 240, 135), (2, 720, 135)])
    arena = arena_con(panel)
    arena.update()

    panel.estado = estado_con([(1, 240, 135)])
    arena.update()

    assert set(arena.visuales) == {1}
    assert tuple(dibujar(arena).get_at((720, 135)))[:3] == BLANCO


# teclas


def test_las_teclas_se_envian_por_el_canal():
    panel = PanelFalso([(1, 240, 135)])
    arena = arena_con(panel)

    arena.handle_event(tecla(pygame.KEYDOWN, pygame.K_d))
    arena.update()
    arena.handle_event(tecla(pygame.KEYUP, pygame.K_d))
    arena.update()

    primero, segundo = panel.canal.enviados
    assert primero == {
        "tipo": "entrada",
        "control": "derecha",
        "estado": "presionado",
        "origen": "teclado",
        "seq": 1,
    }
    assert segundo["estado"] == "liberado" and segundo["seq"] == 2


def test_escape_vuelve_a_la_pantalla_de_origen():
    arena = arena_con(PanelFalso([(1, 240, 135)]), volver_a="buscar")

    arena.handle_event(tecla(pygame.KEYDOWN, pygame.K_ESCAPE))

    assert arena.siguiente_pantalla == "buscar"
    assert not arena.activa


def test_al_salir_se_sueltan_todos_los_controles_aunque_haya_una_tecla_apretada():
    panel = PanelFalso([(1, 240, 135)])
    arena = arena_con(panel)
    arena.handle_event(tecla(pygame.KEYDOWN, pygame.K_d))
    arena.update()

    arena.handle_event(tecla(pygame.KEYDOWN, pygame.K_ESCAPE))

    liberados = {m["control"] for m in panel.canal.enviados if m["estado"] == "liberado"}
    assert liberados == {"arriba", "abajo", "izquierda", "derecha", "accion"}


def test_despues_de_salir_no_se_envia_nada_mas():
    panel = PanelFalso([(1, 240, 135)])
    arena = arena_con(panel)
    arena.handle_event(tecla(pygame.KEYDOWN, pygame.K_ESCAPE))
    enviados = len(panel.canal.enviados)

    arena.handle_event(tecla(pygame.KEYDOWN, pygame.K_d))
    arena.update()

    assert len(panel.canal.enviados) == enviados


def test_volver_a_preparar_empieza_limpio():
    panel = PanelFalso([(1, 240, 135)])
    arena = arena_con(panel)
    arena.update()
    arena.handle_event(tecla(pygame.KEYDOWN, pygame.K_ESCAPE))

    arena.preparar(panel, "lobby")

    assert arena.activa and arena.siguiente_pantalla is None and arena.visuales == {}


def test_sin_canal_escape_tambien_funciona():
    arena = arena_con(PanelFalso(jugadores=None, canal=False))

    arena.handle_event(tecla(pygame.KEYDOWN, pygame.K_ESCAPE))

    assert arena.siguiente_pantalla == "lobby"


# panel del canal: estado y botón de la arena 


class CanalDelPanel:
    mensajes: list = []

    def __init__(self, partida_id, jugador_id):
        self.estado = "abierta"
        self.pendientes = list(self.mensajes)

    async def conectar(self):
        pass

    def leer_mensajes(self):
        pendientes, self.pendientes = self.pendientes, []
        return pendientes

    def cerrar(self):
        pass


def panel_abierto(monkeypatch, mensajes=()):
    CanalDelPanel.mensajes = list(mensajes)
    monkeypatch.setattr(panel_canal, "CanalPartida", CanalDelPanel)
    panel = PanelCanal()
    asyncio.run(panel.abrir(3, 1))
    return panel


def test_el_panel_guarda_el_ultimo_estado_de_la_arena(monkeypatch):
    uno = estado_con([(1, 240, 135)])
    dos = estado_con([(1, 300, 135)])
    panel = panel_abierto(monkeypatch, [uno, {"tipo": "jugador_conectado", "conectados": [1]}, dos])

    panel.update()

    assert panel.estado == dos and panel.conectados == [1]


def test_el_panel_olvida_el_estado_al_abrir_otro_canal_o_cerrar(monkeypatch):
    panel = panel_abierto(monkeypatch, [estado_con([(1, 240, 135)])])
    panel.update()
    assert panel.estado is not None

    panel.cerrar()

    assert panel.estado is None


def test_el_boton_de_la_arena_pide_entrar(monkeypatch):
    panel = panel_abierto(monkeypatch)
    panel.draw(pygame.Surface((ANCHO, ALTO)), ANCHO // 2, 460)
    clic = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=panel.boton_arena.rect.center, button=1)

    panel.handle_event(clic)

    assert panel.quiere_arena


def test_sin_canal_el_boton_de_la_arena_no_hace_nada():
    panel = PanelCanal()
    panel.draw(pygame.Surface((ANCHO, ALTO)), ANCHO // 2, 460)
    clic = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=panel.boton_arena.rect.center, button=1)

    panel.handle_event(clic)

    assert not panel.quiere_arena


def test_el_panel_puede_dibujarse_sin_el_boton(monkeypatch):
    panel = panel_abierto(monkeypatch)
    superficie = pygame.Surface((ANCHO, ALTO))
    antes = panel.boton_arena.rect.copy()

    panel.draw(superficie, ANCHO // 2, 460, con_boton=False)

    assert panel.boton_arena.rect == antes  # no lo movió ni lo dibujó