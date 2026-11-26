"""Iniciar la partida desde el lobby y ver el resultado al terminar (US-17)."""

import asyncio
import os

import pygame
import pytest

from src import api_client
from src.api_client import ApiError
from src.red import Respuesta
from src.screens import panel_canal
from src.screens.arena import ArenaScreen
from src.screens.panel_canal import PanelCanal

ANCHO, ALTO = 960, 640
RESULTADO = {
    "tipo": "partida_finalizada",
    "motivo": "tiempo",
    "ganador_id": 2,
    "posiciones": [
        {"jugador_id": 2, "nombre": "beto", "puntaje": 120, "posicion": 1},
        {"jugador_id": 1, "nombre": "ana", "puntaje": 40, "posicion": 2},
    ],
}


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, ALTO))
    yield
    pygame.quit()


class CanalFalso:
    def __init__(self, partida_id, token):
        self.estado = "abierta"
        self.pendientes = []
        self.enviados = []

    async def conectar(self):
        pass

    def leer_mensajes(self):
        pendientes, self.pendientes = self.pendientes, []
        return pendientes

    def enviar(self, mensaje):
        self.enviados.append(mensaje)

    def cerrar(self):
        self.estado = "cerrada"


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=boton.rect.center, button=1)


def panel_abierto(monkeypatch, es_creador=True, estado_partida="esperando", conectados=(1, 2)):
    monkeypatch.setattr(panel_canal, "CanalPartida", CanalFalso)
    panel = PanelCanal()
    asyncio.run(panel.abrir(4, "token-ana", es_creador=es_creador))
    panel.canal.pendientes = [
        {"tipo": "presencia", "conectados": list(conectados)},
        {"tipo": "estado", "jugadores": [], "partida": {"estado": estado_partida}},
    ]
    panel.update()
    panel.draw(pygame.display.get_surface(), ANCHO // 2, 460)  # ubica los botones
    return panel


# llamada al servidor


def test_iniciar_partida_manda_el_token(monkeypatch):
    llamadas = []

    async def falsa(metodo, url, cuerpo=None, timeout=5.0, headers=None):
        llamadas.append((metodo, url, headers))
        return Respuesta(200, {"id": 4, "estado": "en_curso"})

    monkeypatch.setattr(api_client, "solicitar", falsa)

    datos = asyncio.run(api_client.iniciar_partida(4, "abc"))

    assert datos["estado"] == "en_curso"
    metodo, url, headers = llamadas[0]
    assert metodo == "POST" and url.endswith("/partidas/4/iniciar")
    assert headers == {"Authorization": "Bearer abc"}


# botón de iniciar


def test_el_creador_puede_iniciar_mientras_se_espera(monkeypatch):
    assert panel_abierto(monkeypatch).puede_iniciar()


def test_con_un_solo_jugador_el_boton_sale_en_gris_y_no_inicia(monkeypatch):
    llamadas = []

    async def iniciar(partida_id, token):
        llamadas.append(partida_id)

    monkeypatch.setattr(panel_canal, "iniciar_partida", iniciar)
    panel = panel_abierto(monkeypatch, conectados=(1,))

    assert panel.puede_iniciar() and not panel.hay_jugadores_suficientes()
    assert panel.boton_esperando.texto == "Esperando jugadores (1/2)"
    centro = panel.boton_esperando.rect.center
    assert pygame.display.get_surface().get_at(centro)[:3] != panel.boton_iniciar.color
    panel.handle_event(clic(panel.boton_esperando))
    assert not panel.ocupado() and llamadas == []


def test_cuando_se_une_el_segundo_el_boton_se_activa(monkeypatch):
    panel = panel_abierto(monkeypatch, conectados=(1,))
    panel.canal.pendientes = [{"tipo": "presencia", "conectados": [1, 2]}]
    panel.update()
    pantalla = pygame.display.get_surface()
    pantalla.fill((0, 0, 0))
    panel.draw(pantalla, ANCHO // 2, 460)

    assert panel.hay_jugadores_suficientes()
    assert pantalla.get_at(panel.boton_iniciar.rect.midleft)[:3] == panel.boton_iniciar.color


def test_un_jugador_conectado_dos_veces_cuenta_una_sola_vez(monkeypatch):
    assert not panel_abierto(monkeypatch, conectados=(1, 1)).hay_jugadores_suficientes()


def test_quien_se_unio_no_ve_el_boton_de_iniciar(monkeypatch):
    assert not panel_abierto(monkeypatch, es_creador=False).puede_iniciar()


def test_con_la_partida_en_curso_ya_no_se_puede_iniciar(monkeypatch):
    assert not panel_abierto(monkeypatch, estado_partida="en_curso").puede_iniciar()


def test_el_boton_pide_iniciar_la_partida_con_el_token(monkeypatch):
    llamadas = []

    async def iniciar(partida_id, token):
        llamadas.append((partida_id, token))

    monkeypatch.setattr(panel_canal, "iniciar_partida", iniciar)
    panel = panel_abierto(monkeypatch)

    async def escenario():
        panel.handle_event(clic(panel.boton_iniciar))
        panel.handle_event(clic(panel.boton_iniciar))  # el segundo clic no repite la petición
        while panel.ocupado():
            await asyncio.sleep(0)

    asyncio.run(escenario())
    assert llamadas == [(4, "token-ana")]
    assert panel.error == ""


def test_si_el_servidor_no_deja_iniciar_se_muestra_el_motivo(monkeypatch):
    async def iniciar(partida_id, token):
        raise ApiError("Se necesitan al menos 2 jugadores para empezar", 409)

    monkeypatch.setattr(panel_canal, "iniciar_partida", iniciar)
    panel = panel_abierto(monkeypatch)

    async def escenario():
        panel.handle_event(clic(panel.boton_iniciar))
        while panel.ocupado():
            await asyncio.sleep(0)

    asyncio.run(escenario())
    assert panel.error == "Se necesitan al menos 2 jugadores para empezar"
    panel.draw(pygame.display.get_surface(), ANCHO // 2, 460)  # dibuja el aviso sin fallar


# avisos del servidor


def test_al_empezar_todos_piden_ir_a_la_arena(monkeypatch):
    panel = panel_abierto(monkeypatch, es_creador=False)
    panel.canal.pendientes = [{"tipo": "partida_iniciada", "tiempo_limite": 300}]

    panel.update()

    assert panel.quiere_arena


def test_al_terminar_el_panel_guarda_el_resultado(monkeypatch):
    panel = panel_abierto(monkeypatch)
    panel.canal.pendientes = [RESULTADO]

    panel.update()

    assert panel.resultado == RESULTADO


# arena


def test_la_arena_muestra_las_posiciones_al_terminar_y_esc_vuelve(monkeypatch):
    panel = panel_abierto(monkeypatch)
    panel.estado = {
        "tipo": "estado",
        "jugadores": [],
        "arena": {"ancho": 960, "alto": 540, "radio": 20},
    }
    panel.resultado = RESULTADO
    arena = ArenaScreen(ANCHO, ALTO)
    arena.preparar(panel, "lobby")

    arena.draw(pygame.display.get_surface())  # no debe fallar con el cuadro final
    arena.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))

    assert arena.siguiente_pantalla == "lobby"


def test_un_canal_nuevo_empieza_el_seq_de_cero(monkeypatch):
    panel = panel_abierto(monkeypatch)
    panel.seq_enviada = 40

    asyncio.run(panel.abrir(5, "token-ana", es_creador=True))

    assert panel.seq_enviada == 0
