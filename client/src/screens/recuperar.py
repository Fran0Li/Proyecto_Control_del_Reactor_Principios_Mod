"""Recuperar la contraseña con un código que llega al correo (US-05).

Paso 1: escribir el correo y pedir el código.
Paso 2: escribir el código y la contraseña nueva.
"""

import pygame

from src.api_client import ApiError, restablecer_contrasena, solicitar_recuperacion
from src.screens.componentes import Boton, boton_secundario
from src.screens.formulario import PantallaFormulario
from src.validaciones import PATRON_CORREO, validar_contrasena


class RecuperarScreen(PantallaFormulario):
    titulo = "RECUPERAR CONTRASEÑA"
    y_mensaje = 560

    def __init__(self, width: int) -> None:
        super().__init__(width)
        self.correo = self.campo(160, "Correo de tu cuenta")
        self.codigo = self.campo(300, "Código que te llegó")
        self.nueva = self.campo(370, "Contraseña nueva", oculto=True)
        self.confirmacion = self.campo(440, "Confirmar contraseña", oculto=True)
        self._paso_2 = [self.codigo, self.nueva, self.confirmacion]

        self.boton_pedir = Boton(self.rect_boton(215, 44), "Enviar código")
        self.boton_cambiar = Boton(self.rect_boton(495, 44), "Cambiar contraseña")
        self.boton_volver = boton_secundario(pygame.Rect(20, 20, 120, 40), "Volver")
        self.al_mostrar()

    def al_mostrar(self) -> None:
        for campo in [self.correo, *self._paso_2]:
            campo.texto = ""
            campo.activo = False
        self.correo.activo = True
        self.campos = [self.correo]  # el paso 2 aparece cuando se manda el código
        self.mostrar("")

    @property
    def codigo_enviado(self) -> bool:
        return len(self.campos) > 1

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.boton_volver.fue_presionado(event):
            self.siguiente_pantalla = "login"
        elif self.boton_pedir.fue_presionado(event):
            self.lanzar(self._pedir_codigo)
        elif self.codigo_enviado and self.boton_cambiar.fue_presionado(event):
            self.lanzar(self._cambiar)
        elif self.es_enter(event):
            self.lanzar(self._cambiar if self.codigo_enviado else self._pedir_codigo)
        else:
            self.manejar_campos(event)

    async def _pedir_codigo(self) -> None:
        correo = self.correo.texto.strip()
        if not PATRON_CORREO.match(correo):
            self.mostrar("Escribí el correo de tu cuenta", es_error=True)
            return

        self.mostrar("Enviando...")
        try:
            await solicitar_recuperacion(correo)
        except ApiError as error:
            self.mostrar(str(error), es_error=True)
            return

        self.campos = [self.correo, *self._paso_2]
        self.correo.activo = False
        self.codigo.activo = True
        self.mostrar("Si el correo está registrado, te llegó un código")

    async def _cambiar(self) -> None:
        error = validar_contrasena(self.nueva.texto)
        if not self.codigo.texto.strip():
            error = "Escribí el código que te llegó al correo"
        elif error is None and self.nueva.texto != self.confirmacion.texto:
            error = "Las contraseñas no coinciden"
        if error:
            self.mostrar(error, es_error=True)
            return

        self.mostrar("Cambiando...")
        try:
            await restablecer_contrasena(
                self.correo.texto.strip(), self.codigo.texto.strip(), self.nueva.texto
            )
        except ApiError as error_api:
            self.mostrar(str(error_api), es_error=True)
            return

        self.al_mostrar()
        self.mostrar("Contraseña cambiada. Ya podés iniciar sesión")

    def draw(self, screen: pygame.Surface) -> None:
        self.dibujar_base(screen)
        self.boton_volver.draw(screen)
        self.boton_pedir.draw(screen)
        if self.codigo_enviado:
            self.boton_cambiar.draw(screen)
