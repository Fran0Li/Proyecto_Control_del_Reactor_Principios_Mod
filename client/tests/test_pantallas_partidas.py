"""Pruebas del lobby, la pantalla de buscar partidas y el panel del canal (con la red simulada)."""

import asyncio
import os

import pygame
import pytest

from src import sesion
from src.api_client import ApiError
from src.config import JUGADOR_ID
from src.screens import buscar_partida, lobby, panel_canal
from src.screens.buscar_partida import BuscarPartidaScreen
from src.screens.lobby import LobbyScreen
from src.screens.panel_canal import PanelCanal

ANCHO = 960
PARTIDAS = [
    {"id": 1, "escenario": "laboratorio", "jugadores": 1},
    {"id": 2, "escenario": "planta_industrial", "jugadores": 3},
]


@pytest.fixture(scope="module", autouse=True)
def pygame_sin_ventana():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((ANCHO, 640))
    yield
    pygame.quit()


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=boton.rect.center, button=1)


async def terminar(pantalla):
    """Espera a que termine la petición en curso de la pantalla."""
    while pantalla.ocupada():
        await asyncio.sleep(0)


class PanelFalso:
    def __init__(self):
        self.abierto = None
        self.cerrado = False

    async def abrir(self, partida_id, token):
        self.abierto = (partida_id, token)

    def update(self):
        pass

    def cerrar(self):
        self.cerrado = True

    def draw(self, screen, centro_x, y):
        pass


class Servidor:
    """Respuestas simuladas de la API de partidas; anota las llamadas."""

    def __init__(self, monkeypatch, partidas=None, error_al_listar=None, error_al_unirse=None):
        self.listados = 0
        self.uniones = []
        self.espera = 0

        async def listar():
            self.listados += 1
            if error_al_listar:
                raise error_al_listar
            return PARTIDAS if partidas is None else partidas

        async def unirse(partida_id, jugador_id):
            self.uniones.append((partida_id, jugador_id))
            await asyncio.sleep(self.espera)
            if error_al_unirse:
                raise error_al_unirse
            return {"id": partida_id, "escenario": "laboratorio", "jugadores": 2}

        monkeypatch.setattr(buscar_partida, "listar_partidas_disponibles", listar)
        monkeypatch.setattr(buscar_partida, "unirse_a_partida", unirse)


def pantalla_buscar():
    pantalla = BuscarPartidaScreen(ANCHO)
    pantalla.panel = PanelFalso()
    return pantalla


# --- buscar partidas -------------------------------------------------------------------------


def test_al_mostrarse_carga_las_partidas_y_crea_un_boton_por_fila(monkeypatch):
    Servidor(monkeypatch)

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.al_mostrar()
        await terminar(pantalla)
        return pantalla

    pantalla = asyncio.run(escenario())
    assert pantalla.partidas == PARTIDAS
    assert len(pantalla.botones_unirse) == 2
    assert pantalla.mensaje == ""


def test_sin_partidas_muestra_un_aviso(monkeypatch):
    Servidor(monkeypatch, partidas=[])

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.al_mostrar()
        await terminar(pantalla)
        return pantalla

    pantalla = asyncio.run(escenario())
    assert "No hay partidas" in pantalla.mensaje and not pantalla.mensaje_es_error


def test_error_al_cargar_muestra_el_mensaje_en_rojo(monkeypatch):
    Servidor(monkeypatch, error_al_listar=ApiError("Sin conexión con el servidor"))

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.al_mostrar()
        await terminar(pantalla)
        return pantalla

    pantalla = asyncio.run(escenario())
    assert pantalla.mensaje == "Sin conexión con el servidor" and pantalla.mensaje_es_error
    assert pantalla.partidas == [] and pantalla.botones_unirse == []


def test_unirse_envia_la_partida_y_el_jugador_y_abre_el_canal(monkeypatch):
    servidor = Servidor(monkeypatch)

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.al_mostrar()
        await terminar(pantalla)
        pantalla.handle_event(clic(pantalla.botones_unirse[1]))  # la partida #2
        await terminar(pantalla)
        return pantalla

    pantalla = asyncio.run(escenario())
    assert servidor.uniones == [(2, JUGADOR_ID)]
    assert pantalla.unido_a == 2
    assert pantalla.panel.abierto == (2, sesion.token())
    assert "#2" in pantalla.mensaje and not pantalla.mensaje_es_error


def test_unirse_con_error_muestra_el_mensaje_y_no_abre_el_canal(monkeypatch):
    Servidor(monkeypatch, error_al_unirse=ApiError("La partida 1 está llena"))

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.al_mostrar()
        await terminar(pantalla)
        pantalla.handle_event(clic(pantalla.botones_unirse[0]))
        await terminar(pantalla)
        return pantalla

    pantalla = asyncio.run(escenario())
    assert pantalla.mensaje == "La partida 1 está llena" and pantalla.mensaje_es_error
    assert pantalla.unido_a is None and pantalla.panel.abierto is None


def test_un_segundo_clic_mientras_espera_no_duplica_la_peticion(monkeypatch):
    servidor = Servidor(monkeypatch)
    servidor.espera = 0.05

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.al_mostrar()
        await terminar(pantalla)
        pantalla.handle_event(clic(pantalla.botones_unirse[0]))
        pantalla.handle_event(clic(pantalla.botones_unirse[0]))  # mientras la primera espera
        await terminar(pantalla)

    asyncio.run(escenario())
    assert servidor.uniones == [(1, JUGADOR_ID)]


def test_despues_de_unirse_los_botones_de_unirse_ya_no_hacen_nada(monkeypatch):
    servidor = Servidor(monkeypatch)

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.al_mostrar()
        await terminar(pantalla)
        boton = pantalla.botones_unirse[0]
        pantalla.handle_event(clic(boton))
        await terminar(pantalla)
        pantalla.handle_event(clic(boton))
        await terminar(pantalla)

    asyncio.run(escenario())
    assert len(servidor.uniones) == 1


def test_actualizar_vuelve_a_pedir_la_lista(monkeypatch):
    servidor = Servidor(monkeypatch)

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.al_mostrar()
        await terminar(pantalla)
        pantalla.handle_event(clic(pantalla.boton_actualizar))
        await terminar(pantalla)

    asyncio.run(escenario())
    assert servidor.listados == 2


def test_volver_pide_ir_al_lobby():
    pantalla = pantalla_buscar()
    pantalla.handle_event(clic(pantalla.boton_volver))
    assert pantalla.siguiente_pantalla == "lobby"


def test_cerrar_cierra_el_canal():
    pantalla = pantalla_buscar()
    pantalla.cerrar()
    assert pantalla.panel.cerrado


def test_describe_la_fila_con_singular_y_plural():
    uno = BuscarPartidaScreen._describir(PARTIDAS[0])
    tres = BuscarPartidaScreen._describir(PARTIDAS[1])
    assert uno == "Partida #1   laboratorio   1 jugador"
    assert tres == "Partida #2   planta industrial   3 jugadores"


def test_solo_muestra_las_primeras_filas_y_avisa_del_resto(monkeypatch):
    muchas = [{"id": i, "escenario": "laboratorio", "jugadores": 1} for i in range(1, 10)]
    Servidor(monkeypatch, partidas=muchas)

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.al_mostrar()
        await terminar(pantalla)
        return pantalla

    pantalla = asyncio.run(escenario())
    assert len(pantalla.botones_unirse) == buscar_partida.MAX_FILAS
    pantalla.draw(pygame.display.get_surface())  # no debe fallar


def test_dibuja_en_todos_los_estados(monkeypatch):
    Servidor(monkeypatch)
    superficie = pygame.display.get_surface()

    async def escenario():
        pantalla = pantalla_buscar()
        pantalla.draw(superficie)  # vacía
        pantalla.al_mostrar()
        await terminar(pantalla)
        pantalla.draw(superficie)  # con la lista
        pantalla.handle_event(clic(pantalla.botones_unirse[0]))
        await terminar(pantalla)
        pantalla.draw(superficie)  # ya unido

    asyncio.run(escenario())


#  lobby 


def lobby_con(monkeypatch, resultado):
    llamadas = []

    async def crear(creador_id, escenario=None):
        llamadas.append(creador_id)
        await asyncio.sleep(0.02)
        if isinstance(resultado, Exception):
            raise resultado
        return resultado

    monkeypatch.setattr(lobby, "crear_partida", crear)
    pantalla = LobbyScreen(ANCHO)
    pantalla.panel = PanelFalso()
    return pantalla, llamadas


def test_lobby_crear_partida_muestra_el_resultado_y_abre_el_canal(monkeypatch):
    pantalla, llamadas = lobby_con(monkeypatch, {"id": 5, "escenario": "laboratorio"})

    async def escenario():
        pantalla.handle_event(clic(pantalla.boton_crear))
        await terminar(pantalla)

    asyncio.run(escenario())
    assert llamadas == [JUGADOR_ID]
    assert pantalla.mensaje == "Partida #5 creada - escenario: laboratorio"
    assert pantalla.panel.abierto == (5, sesion.token())


def test_lobby_con_error_no_abre_el_canal(monkeypatch):
    error = ApiError("El jugador 1 ya está en una partida activa")
    pantalla, _ = lobby_con(monkeypatch, error)

    async def escenario():
        pantalla.handle_event(clic(pantalla.boton_crear))
        await terminar(pantalla)

    asyncio.run(escenario())
    assert pantalla.mensaje_es_error and pantalla.panel.abierto is None


def test_lobby_no_duplica_la_peticion_con_dos_clics_seguidos(monkeypatch):
    pantalla, llamadas = lobby_con(monkeypatch, {"id": 5, "escenario": "laboratorio"})

    async def escenario():
        pantalla.handle_event(clic(pantalla.boton_crear))
        pantalla.handle_event(clic(pantalla.boton_crear))
        await terminar(pantalla)

    asyncio.run(escenario())
    assert len(llamadas) == 1


def test_lobby_boton_buscar_pide_la_pantalla_de_busqueda(monkeypatch):
    pantalla, _ = lobby_con(monkeypatch, {})
    pantalla.handle_event(clic(pantalla.boton_buscar))
    assert pantalla.siguiente_pantalla == "buscar"


def test_lobby_dibuja_con_y_sin_mensaje(monkeypatch):
    pantalla, _ = lobby_con(monkeypatch, {})
    superficie = pygame.display.get_surface()
    pantalla.draw(superficie)
    pantalla.mensaje = "algo"
    pantalla.draw(superficie)


#  panel del canal

class CanalFalso:
    mensajes: list = []

    def __init__(self, partida_id, jugador_id):
        self.args = (partida_id, jugador_id)
        self.estado = "abierta"
        self.cerrado = False
        self.pendientes = list(self.mensajes)

    async def conectar(self):
        pass

    def leer_mensajes(self):
        pendientes, self.pendientes = self.pendientes, []
        return pendientes

    def cerrar(self):
        self.cerrado = True


def test_el_panel_actualiza_los_conectados_con_los_mensajes(monkeypatch):
    CanalFalso.mensajes = [
        {"tipo": "jugador_conectado", "jugador_id": 2, "conectados": [1, 2]},
        {"tipo": "otro_mensaje"},
    ]
    monkeypatch.setattr(panel_canal, "CanalPartida", CanalFalso)
    panel = PanelCanal()

    asyncio.run(panel.abrir(3, 2))
    assert panel.canal.args == (3, 2) and panel.conectados == []
    panel.update()
    assert panel.conectados == [1, 2]


def test_abrir_un_canal_nuevo_cierra_el_anterior(monkeypatch):
    CanalFalso.mensajes = []
    monkeypatch.setattr(panel_canal, "CanalPartida", CanalFalso)
    panel = PanelCanal()

    async def escenario():
        await panel.abrir(1, 1)
        primero = panel.canal
        await panel.abrir(2, 1)
        return primero

    primero = asyncio.run(escenario())
    assert primero.cerrado and panel.canal is not primero


def test_el_panel_cerrar_cierra_el_canal(monkeypatch):
    CanalFalso.mensajes = []
    monkeypatch.setattr(panel_canal, "CanalPartida", CanalFalso)
    panel = PanelCanal()
    asyncio.run(panel.abrir(1, 1))
    canal = panel.canal
    panel.cerrar()
    assert canal.cerrado and panel.canal is None
    panel.update()  # sin canal no debe fallar


@pytest.mark.parametrize(
    ("estado", "texto"),
    [
        ("abierta", "conectado"),
        ("conectando", "conectando..."),
        ("cerrada", "desconectado"),
        ("error: InvalidStatus", "sin conexión"),
    ],
)
def test_el_panel_traduce_el_estado_del_canal(monkeypatch, estado, texto):
    CanalFalso.mensajes = []
    monkeypatch.setattr(panel_canal, "CanalPartida", CanalFalso)
    panel = PanelCanal()
    asyncio.run(panel.abrir(1, 1))
    panel.canal.estado = estado
    assert panel._texto_estado() == texto
    panel.draw(pygame.display.get_surface(), ANCHO // 2, 460)  # no debe fallar