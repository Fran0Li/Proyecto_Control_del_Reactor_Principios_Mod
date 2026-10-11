"""Pantalla de lobby: crear una partida (US-07)."""

import asyncio
import os

import pygame

from src.api_client import ApiError, crear_partida

# Temporal: mientras no exista el login (US-03), el jugador viene del entorno.
JUGADOR_ID = int(os.getenv("JUGADOR_ID", "1"))

COLOR_FONDO = (12, 16, 32)
COLOR_TITULO = (80, 200, 255)
COLOR_BOTON = (40, 120, 200)
COLOR_BOTON_HOVER = (70, 160, 240)
COLOR_TEXTO_BOTON = (255, 255, 255)
COLOR_OK = (90, 220, 130)
COLOR_ERROR = (240, 100, 100)


class LobbyScreen:
    def __init__(self, width: int) -> None:
        self.centro_x = width // 2
        self.boton = pygame.Rect(0, 0, 280, 56)
        self.boton.center = (self.centro_x, 340)
        self.fuente_titulo = pygame.font.Font(None, 64)
        self.fuente_texto = pygame.font.Font(None, 32)
        self.mensaje = ""
        self.mensaje_es_error = False
        self._tarea: asyncio.Task | None = None  # petición en curso (no congela la ventana)

    def handle_event(self, event: pygame.event.Event) -> None:
        clic_izquierdo = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        if clic_izquierdo and self.boton.collidepoint(event.pos):
            self._iniciar_creacion()

    def _iniciar_creacion(self) -> None:
        if self._tarea is not None and not self._tarea.done():
            return  # ya hay una en curso
        self._tarea = asyncio.create_task(self._crear_partida())

    async def _crear_partida(self) -> None:
        self.mensaje = "Creando partida..."
        self.mensaje_es_error = False
        try:
            partida = await crear_partida(JUGADOR_ID)
        except ApiError as error:
            self.mensaje = str(error)
            self.mensaje_es_error = True
            return
        self.mensaje = f"Partida #{partida['id']} creada - escenario: {partida['escenario']}"
        self.mensaje_es_error = False

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_FONDO)

        titulo = self.fuente_titulo.render("LOBBY", True, COLOR_TITULO)
        screen.blit(titulo, titulo.get_rect(center=(self.centro_x, 200)))

        hover = self.boton.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(
            screen,
            COLOR_BOTON_HOVER if hover else COLOR_BOTON,
            self.boton,
            border_radius=10,
        )
        etiqueta = self.fuente_texto.render("Crear partida", True, COLOR_TEXTO_BOTON)
        screen.blit(etiqueta, etiqueta.get_rect(center=self.boton.center))

        if self.mensaje:
            color = COLOR_ERROR if self.mensaje_es_error else COLOR_OK
            texto = self.fuente_texto.render(self.mensaje, True, color)
            screen.blit(texto, texto.get_rect(center=(self.centro_x, 430)))