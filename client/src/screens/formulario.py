"""Lo que comparten las pantallas con campos de texto: título, campos, Tab y mensaje."""

import asyncio
from collections.abc import Awaitable, Callable

import pygame

from src.screens.componentes import CampoTexto

COLOR_FONDO = (12, 16, 32)
COLOR_TITULO = (80, 200, 255)
COLOR_OK = (90, 220, 130)
COLOR_ERROR = (240, 100, 100)

ANCHO_CAMPO = 360
ALTO_CAMPO = 42


class PantallaFormulario:
    titulo = ""
    y_titulo = 70
    y_mensaje = 505

    def __init__(self, width: int) -> None:
        self.centro_x = width // 2
        self.x_campos = self.centro_x - ANCHO_CAMPO // 2
        self.campos: list[CampoTexto] = []
        self.fuente_titulo = pygame.font.Font(None, 56)
        self.fuente_texto = pygame.font.Font(None, 28)
        self.mensaje = ""
        self.mensaje_es_error = False
        self.siguiente_pantalla: str | None = None
        self._tarea: asyncio.Task | None = None

    def campo(self, y: int, etiqueta: str, oculto: bool = False) -> CampoTexto:
        nuevo = CampoTexto(pygame.Rect(self.x_campos, y, ANCHO_CAMPO, ALTO_CAMPO), etiqueta, oculto)
        nuevo.activo = not self.campos  # el primero arranca seleccionado
        self.campos.append(nuevo)
        return nuevo

    def rect_boton(self, y: int, alto: int = 50) -> pygame.Rect:
        return pygame.Rect(self.x_campos, y, ANCHO_CAMPO, alto)

    def ocupada(self) -> bool:
        return self._tarea is not None and not self._tarea.done()

    def lanzar(self, accion: Callable[[], Awaitable[None]]) -> None:
        """Corre una llamada al servidor sin congelar la ventana (y sin repetirla si ya va una)."""
        if not self.ocupada():
            self._tarea = asyncio.create_task(accion())

    def mostrar(self, mensaje: str, es_error: bool = False) -> None:
        self.mensaje = mensaje
        self.mensaje_es_error = es_error

    def manejar_campos(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self._siguiente_campo()
            return
        for campo in self.campos:
            campo.handle_event(event)

    def es_enter(self, event: pygame.event.Event) -> bool:
        return event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)

    def _siguiente_campo(self) -> None:
        indice = next((i for i, c in enumerate(self.campos) if c.activo), -1)
        for campo in self.campos:
            campo.activo = False
        self.campos[(indice + 1) % len(self.campos)].activo = True

    def dibujar_base(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_FONDO)
        titulo = self.fuente_titulo.render(self.titulo, True, COLOR_TITULO)
        screen.blit(titulo, titulo.get_rect(center=(self.centro_x, self.y_titulo)))
        for campo in self.campos:
            campo.draw(screen)
        if self.mensaje:
            color = COLOR_ERROR if self.mensaje_es_error else COLOR_OK
            texto = self.fuente_texto.render(self.mensaje, True, color)
            screen.blit(texto, texto.get_rect(center=(self.centro_x, self.y_mensaje)))
