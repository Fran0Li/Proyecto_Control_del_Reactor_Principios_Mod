"""Pantalla de registro de usuario (US-01)."""

import pygame

from src.api_client import ApiError, registrar_usuario
from src.screens.componentes import Boton, boton_secundario
from src.screens.formulario import PantallaFormulario
from src.validaciones import validar_registro


class RegistroScreen(PantallaFormulario):
    titulo = "CREAR CUENTA"

    def __init__(self, width: int) -> None:
        super().__init__(width)
        self.correo_pendiente = ""  # lo usa la pantalla de verificar correo
        self.usuario = self.campo(150, "Nombre de usuario")
        self.correo = self.campo(225, "Correo electrónico")
        self.contrasena = self.campo(300, "Contraseña", oculto=True)
        self.confirmacion = self.campo(375, "Confirmar contraseña", oculto=True)

        self.boton_crear = Boton(self.rect_boton(430), "Crear cuenta")
        self.boton_login = boton_secundario(
            pygame.Rect(self.centro_x - 110, 530, 220, 40), "Ya tengo cuenta"
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.boton_crear.fue_presionado(event) or self.es_enter(event):
            self.lanzar(self._registrar)
        elif self.boton_login.fue_presionado(event):
            self.siguiente_pantalla = "login"
        else:
            self.manejar_campos(event)

    async def _registrar(self) -> None:
        error = validar_registro(self.usuario.texto, self.correo.texto, self.contrasena.texto)
        if error is None and self.contrasena.texto != self.confirmacion.texto:
            error = "Las contraseñas no coinciden"
        if error:
            self.mostrar(error, es_error=True)
            return

        self.mostrar("Creando cuenta...")
        try:
            await registrar_usuario(
                self.usuario.texto.strip(), self.correo.texto.strip(), self.contrasena.texto
            )
        except ApiError as error_api:
            self.mostrar(str(error_api), es_error=True)
            return

        self.correo_pendiente = self.correo.texto.strip()
        for campo in self.campos:
            campo.texto = ""
        self.mostrar("")
        self.siguiente_pantalla = "verificar"

    def draw(self, screen: pygame.Surface) -> None:
        self.dibujar_base(screen)
        self.boton_crear.draw(screen)
        self.boton_login.draw(screen)
