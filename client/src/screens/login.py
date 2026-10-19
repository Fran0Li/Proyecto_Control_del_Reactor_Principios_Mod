"""Pantalla de inicio de sesión (US-03). Es la primera que se ve al abrir el juego."""

import pygame

from src import sesion
from src.api_client import ApiError, iniciar_sesion
from src.screens.componentes import Boton, boton_secundario
from src.screens.formulario import ANCHO_CAMPO, PantallaFormulario


class LoginScreen(PantallaFormulario):
    titulo = "CONTROL DEL REACTOR"
    y_mensaje = 470

    def __init__(self, width: int) -> None:
        super().__init__(width)
        self.usuario = self.campo(200, "Usuario o correo")
        self.contrasena = self.campo(280, "Contraseña", oculto=True)
        self.boton_entrar = Boton(self.rect_boton(340), "Entrar")
        self.boton_registro = boton_secundario(
            pygame.Rect(self.x_campos, 510, ANCHO_CAMPO, 40), "Crear cuenta"
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.boton_entrar.fue_presionado(event) or self.es_enter(event):
            self.lanzar(self._entrar)
        elif self.boton_registro.fue_presionado(event):
            self.siguiente_pantalla = "registro"
        else:
            self.manejar_campos(event)

    async def _entrar(self) -> None:
        if not self.usuario.texto.strip() or not self.contrasena.texto:
            self.mostrar("Escribí tu usuario y tu contraseña", es_error=True)
            return

        self.mostrar("Entrando...")
        try:
            datos = await iniciar_sesion(self.usuario.texto.strip(), self.contrasena.texto)
        except ApiError as error:
            self.mostrar(str(error), es_error=True)
            return

        sesion.iniciar(datos["access_token"], datos["usuario"])
        self.contrasena.texto = ""
        self.mostrar("")
        self.siguiente_pantalla = "lobby"

    def draw(self, screen: pygame.Surface) -> None:
        self.dibujar_base(screen)
        subtitulo = self.fuente_texto.render("Iniciar sesión", True, (150, 160, 190))
        screen.blit(subtitulo, subtitulo.get_rect(center=(self.centro_x, 120)))
        self.boton_entrar.draw(screen)
        self.boton_registro.draw(screen)
