"""Pantalla de lobby: crear una partida (US-07) o ir a buscar una (US-08)."""

import asyncio

import pygame

from src import sesion
from src.api_client import ApiError, crear_partida
from src.screens.componentes import Boton, boton_secundario
from src.screens.panel_canal import PanelCanal

COLOR_FONDO = (12, 16, 32)
COLOR_TITULO = (80, 200, 255)
COLOR_OK = (90, 220, 130)
COLOR_ERROR = (240, 100, 100)


class LobbyScreen:
    def __init__(self, width: int) -> None:
        self.centro_x = width // 2
        self.boton_crear = Boton(pygame.Rect(self.centro_x - 140, 230, 280, 56), "Crear partida")
        self.boton_buscar = Boton(
            pygame.Rect(self.centro_x - 140, 305, 280, 56),
            "Buscar partidas",
            color=(40, 50, 80),
            color_hover=(60, 75, 115),
        )
        self.boton_salir = boton_secundario(pygame.Rect(width - 190, 20, 170, 40), "Cerrar sesión")
        self.fuente_titulo = pygame.font.Font(None, 64)
        self.fuente_texto = pygame.font.Font(None, 32)
        self.mensaje = ""
        self.mensaje_es_error = False
        self.siguiente_pantalla: str | None = None
        self.panel = PanelCanal()
        self._tarea: asyncio.Task | None = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.boton_buscar.fue_presionado(event):
            self.siguiente_pantalla = "buscar"
            return
        if self.boton_salir.fue_presionado(event):
            sesion.cerrar()
            self.mensaje = ""
            self.siguiente_pantalla = "login"
            return
        if self.boton_crear.fue_presionado(event) and not self.ocupada():
            self._tarea = asyncio.create_task(self._crear_partida())

    def ocupada(self) -> bool:
        return self._tarea is not None and not self._tarea.done()

    async def _crear_partida(self) -> None:
        try:
            partida = await crear_partida(sesion.jugador_id())
        except ApiError as error:
            self.mensaje = str(error)
            self.mensaje_es_error = True
            return
        self.mensaje = f"Partida #{partida['id']} creada - escenario: {partida['escenario']}"
        self.mensaje_es_error = False
        await self.panel.abrir(partida["id"], sesion.jugador_id())

    def update(self) -> None:
        self.panel.update()

    def cerrar(self) -> None:
        self.panel.cerrar()

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_FONDO)

        titulo = self.fuente_titulo.render("LOBBY", True, COLOR_TITULO)
        screen.blit(titulo, titulo.get_rect(center=(self.centro_x, 140)))

        self.boton_crear.draw(screen)
        self.boton_buscar.draw(screen)
        self.boton_salir.draw(screen)
        actual = sesion.actual()
        if actual:
            nombre = self.fuente_texto.render(actual.nombre_usuario, True, (150, 160, 190))
            screen.blit(nombre, (20, 28))

        if self.mensaje:
            color = COLOR_ERROR if self.mensaje_es_error else COLOR_OK
            texto = self.fuente_texto.render(self.mensaje, True, color)
            screen.blit(texto, texto.get_rect(center=(self.centro_x, 410)))

        self.panel.draw(screen, self.centro_x, 460)