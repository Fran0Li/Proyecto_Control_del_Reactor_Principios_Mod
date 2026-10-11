"""Pantalla de registro de usuario (US-01)."""

import asyncio

import pygame

from src.api_client import ApiError, registrar_usuario
from src.screens.componentes import Boton, CampoTexto
from src.validaciones import validar_registro

COLOR_FONDO = (12, 16, 32)
COLOR_TITULO = (80, 200, 255)
COLOR_OK = (90, 220, 130)
COLOR_ERROR = (240, 100, 100)

ANCHO_CAMPO = 360
ALTO_CAMPO = 42


class RegistroScreen:
    def __init__(self, width: int) -> None:
        self.centro_x = width // 2
        x = self.centro_x - ANCHO_CAMPO // 2

        def campo(y: int, etiqueta: str, oculto: bool = False) -> CampoTexto:
            return CampoTexto(pygame.Rect(x, y, ANCHO_CAMPO, ALTO_CAMPO), etiqueta, oculto)

        self.usuario = campo(150, "Nombre de usuario")
        self.correo = campo(225, "Correo electrónico")
        self.contrasena = campo(300, "Contraseña", oculto=True)
        self.confirmacion = campo(375, "Confirmar contraseña", oculto=True)
        self.campos = [self.usuario, self.correo, self.contrasena, self.confirmacion]
        self.usuario.activo = True

        self.boton_crear = Boton(pygame.Rect(x, 430, ANCHO_CAMPO, 50), "Crear cuenta")
        self.boton_lobby = Boton(
            pygame.Rect(self.centro_x - 90, 530, 180, 40),
            "Ir al lobby",
            color=(40, 50, 80),
            color_hover=(60, 75, 115),
        )
        self.fuente_titulo = pygame.font.Font(None, 56)
        self.fuente_texto = pygame.font.Font(None, 28)
        self.mensaje = ""
        self.mensaje_es_error = False
        self.siguiente_pantalla: str | None = None
        self._tarea: asyncio.Task | None = None  # registro en curso (no congela la ventana)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.boton_crear.fue_presionado(event):
            self._iniciar_registro()
            return
        if self.boton_lobby.fue_presionado(event):
            self.siguiente_pantalla = "lobby"
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self._siguiente_campo()
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._iniciar_registro()
            return
        for campo in self.campos:
            campo.handle_event(event)

    def _siguiente_campo(self) -> None:
        indice = next((i for i, c in enumerate(self.campos) if c.activo), -1)
        for campo in self.campos:
            campo.activo = False
        self.campos[(indice + 1) % len(self.campos)].activo = True

    def _mostrar(self, mensaje: str, es_error: bool) -> None:
        self.mensaje = mensaje
        self.mensaje_es_error = es_error

    def _iniciar_registro(self) -> None:
        if self._tarea is not None and not self._tarea.done():
            return  # ya hay uno en curso: evita registrar dos veces
        self._tarea = asyncio.create_task(self._registrar())

    async def _registrar(self) -> None:
        error = validar_registro(self.usuario.texto, self.correo.texto, self.contrasena.texto)
        if error is None and self.contrasena.texto != self.confirmacion.texto:
            error = "Las contraseñas no coinciden"
        if error:
            self._mostrar(error, es_error=True)
            return

        self._mostrar("Creando cuenta...", es_error=False)
        try:
            await registrar_usuario(
                self.usuario.texto.strip(), self.correo.texto.strip(), self.contrasena.texto
            )
        except ApiError as error_api:
            self._mostrar(str(error_api), es_error=True)
            return

        self._mostrar("Cuenta creada. Revisá tu correo para verificarla.", es_error=False)
        self.contrasena.texto = ""
        self.confirmacion.texto = ""

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_FONDO)

        titulo = self.fuente_titulo.render("CREAR CUENTA", True, COLOR_TITULO)
        screen.blit(titulo, titulo.get_rect(center=(self.centro_x, 70)))

        for campo in self.campos:
            campo.draw(screen)
        self.boton_crear.draw(screen)
        self.boton_lobby.draw(screen)

        if self.mensaje:
            color = COLOR_ERROR if self.mensaje_es_error else COLOR_OK
            texto = self.fuente_texto.render(self.mensaje, True, color)
            screen.blit(texto, texto.get_rect(center=(self.centro_x, 505)))
