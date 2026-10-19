"""Pantalla de inicio de sesión (US-03). Es la primera que se ve al abrir el juego."""

import asyncio
import secrets

import pygame

from src import sesion
from src.api_client import (
    ApiError,
    iniciar_sesion,
    resultado_login_google,
    url_login_google,
)
from src.navegador import abrir_url
from src.screens.componentes import Boton, boton_secundario
from src.screens.formulario import PantallaFormulario

ESPERA_GOOGLE_S = 1.0  # cada cuánto se pregunta si ya terminó el login con Google
INTENTOS_GOOGLE = 180  # unos 3 minutos


class LoginScreen(PantallaFormulario):
    titulo = "CONTROL DEL REACTOR"
    y_mensaje = 470

    def __init__(self, width: int) -> None:
        super().__init__(width)
        self.correo_pendiente = ""  # lo usa la pantalla de verificar correo
        self.usuario = self.campo(200, "Usuario o correo")
        self.contrasena = self.campo(280, "Contraseña", oculto=True)
        self.boton_entrar = Boton(self.rect_boton(340), "Entrar")
        self.boton_google = Boton(
            self.rect_boton(400, 44),
            "Entrar con Google",
            color=(230, 230, 240),
            color_hover=(255, 255, 255),
            color_texto=(40, 40, 50),
        )
        self.boton_registro = boton_secundario(
            pygame.Rect(self.centro_x - 255, 510, 250, 40), "Crear cuenta"
        )
        self.boton_recuperar = boton_secundario(
            pygame.Rect(self.centro_x + 5, 510, 250, 40), "Olvidé mi clave"
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.boton_entrar.fue_presionado(event) or self.es_enter(event):
            self.lanzar(self._entrar)
        elif self.boton_google.fue_presionado(event):
            self.lanzar(self._entrar_con_google)
        elif self.boton_registro.fue_presionado(event):
            self.siguiente_pantalla = "registro"
        elif self.boton_recuperar.fue_presionado(event):
            self.siguiente_pantalla = "recuperar"
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
            if error.estado == 403:  # correo sin verificar
                texto = self.usuario.texto.strip()
                self.correo_pendiente = texto if "@" in texto else ""
                self.mostrar("")
                self.siguiente_pantalla = "verificar"
                return
            self.mostrar(str(error), es_error=True)
            return

        self._sesion_iniciada(datos)

    async def _entrar_con_google(self) -> None:
        sesion_id = secrets.token_urlsafe(16)
        abrir_url(url_login_google(sesion_id))
        self.mostrar("Terminá el login en el navegador...")
        for _ in range(INTENTOS_GOOGLE):
            await asyncio.sleep(ESPERA_GOOGLE_S)
            try:
                datos = await resultado_login_google(sesion_id)
            except ApiError as error:
                self.mostrar(str(error), es_error=True)
                return
            if datos is not None:
                self._sesion_iniciada(datos)
                return
        self.mostrar("Se acabó el tiempo. Probá de nuevo", es_error=True)

    def _sesion_iniciada(self, datos: dict) -> None:
        sesion.iniciar(datos["access_token"], datos["usuario"])
        self.contrasena.texto = ""
        self.mostrar("")
        self.siguiente_pantalla = "lobby"

    def draw(self, screen: pygame.Surface) -> None:
        self.dibujar_base(screen)
        subtitulo = self.fuente_texto.render("Iniciar sesión", True, (150, 160, 190))
        screen.blit(subtitulo, subtitulo.get_rect(center=(self.centro_x, 120)))
        self.boton_entrar.draw(screen)
        self.boton_google.draw(screen)
        self.boton_registro.draw(screen)
        self.boton_recuperar.draw(screen)
