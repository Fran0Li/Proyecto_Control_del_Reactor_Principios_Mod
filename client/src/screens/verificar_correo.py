"""Pantalla que pide verificar el correo y permite reenviar el enlace (US-02)."""

import pygame

from src.api_client import ApiError, reenviar_verificacion
from src.screens.componentes import Boton, boton_secundario
from src.screens.formulario import PantallaFormulario
from src.validaciones import PATRON_CORREO

TEXTO = [
    "Te mandamos un enlace para activar tu cuenta.",
    "Abrilo desde tu correo y después iniciá sesión.",
    "Si no te llegó, revisá la carpeta de spam o pedí otro:",
]


class VerificarCorreoScreen(PantallaFormulario):
    titulo = "VERIFICÁ TU CORREO"
    y_mensaje = 440

    def __init__(self, width: int) -> None:
        super().__init__(width)
        self.correo = self.campo(300, "Correo electrónico")
        self.boton_reenviar = Boton(self.rect_boton(360), "Reenviar correo")
        self.boton_login = boton_secundario(
            pygame.Rect(self.centro_x - 120, 510, 240, 40), "Iniciar sesión"
        )

    def preparar(self, correo: str) -> None:
        self.correo.texto = correo
        self.mostrar("")

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.boton_reenviar.fue_presionado(event) or self.es_enter(event):
            self.lanzar(self._reenviar)
        elif self.boton_login.fue_presionado(event):
            self.siguiente_pantalla = "login"
        else:
            self.manejar_campos(event)

    async def _reenviar(self) -> None:
        correo = self.correo.texto.strip()
        if not PATRON_CORREO.match(correo):
            self.mostrar("Escribí el correo con el que te registraste", es_error=True)
            return

        self.mostrar("Enviando...")
        try:
            await reenviar_verificacion(correo)
        except ApiError as error:
            self.mostrar(str(error), es_error=True)
            return
        self.mostrar("Listo, revisá tu correo")

    def draw(self, screen: pygame.Surface) -> None:
        self.dibujar_base(screen)
        for i, linea in enumerate(TEXTO):
            texto = self.fuente_texto.render(linea, True, (200, 200, 215))
            screen.blit(texto, texto.get_rect(center=(self.centro_x, 150 + i * 34)))
        self.boton_reenviar.draw(screen)
        self.boton_login.draw(screen)
