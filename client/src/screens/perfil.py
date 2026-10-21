"""Pantalla del perfil del jugador conectado (US-06)."""

import pygame

from src import sesion
from src.api_client import ApiError, editar_perfil, obtener_perfil
from src.screens.componentes import Boton, boton_secundario
from src.screens.formulario import PantallaFormulario

AVATARES = {
    "azul": (40, 120, 200),
    "verde": (60, 180, 100),
    "naranja": (235, 140, 40),
    "morado": (140, 80, 200),
    "rojo": (210, 60, 60),
}


class PerfilScreen(PantallaFormulario):
    titulo = "MI PERFIL"

    def __init__(self, width: int) -> None:
        super().__init__(width)
        self.nombre = self.campo(225, "Nombre de usuario")
        self.descripcion = self.campo(300, "Descripción")
        self.descripcion.largo_maximo = 200
        self.avatar = "azul"
        self.perfil: dict | None = None

        self.boton_avatar = boton_secundario(
            pygame.Rect(self.x_campos + 160, 355, 200, 40), "Cambiar avatar"
        )
        self.boton_guardar = Boton(self.rect_boton(425), "Guardar cambios")
        self.boton_volver = boton_secundario(pygame.Rect(20, 20, 120, 40), "Volver")

    def al_mostrar(self) -> None:
        self.perfil = None
        self.mostrar("Cargando...")
        self.lanzar(self._cargar)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.boton_volver.fue_presionado(event):
            self.siguiente_pantalla = "lobby"
        elif self.perfil is None:
            return  # hasta que cargue no se puede editar
        elif self.boton_avatar.fue_presionado(event):
            nombres = list(AVATARES)
            self.avatar = nombres[(nombres.index(self.avatar) + 1) % len(nombres)]
        elif self.boton_guardar.fue_presionado(event) or self.es_enter(event):
            self.lanzar(self._guardar)
        else:
            self.manejar_campos(event)

    async def _cargar(self) -> None:
        actual = sesion.actual()
        if actual is None:
            self.siguiente_pantalla = "login"
            return
        try:
            perfil = await obtener_perfil(actual.token)
        except ApiError as error:
            self._error(error)
            return
        self._mostrar_perfil(perfil)
        self.mostrar("")

    async def _guardar(self) -> None:
        actual = sesion.actual()
        if actual is None:
            self.siguiente_pantalla = "login"
            return
        cambios = {
            "nombre_usuario": self.nombre.texto.strip(),
            "descripcion": self.descripcion.texto.strip(),
            "avatar": self.avatar,
        }
        self.mostrar("Guardando...")
        try:
            perfil = await editar_perfil(actual.token, cambios)
        except ApiError as error:
            self._error(error)
            return
        self._mostrar_perfil(perfil)
        # el lobby muestra el nombre de la sesión, así que se actualiza
        sesion.iniciar(actual.token, perfil)
        self.mostrar("Cambios guardados")

    def _mostrar_perfil(self, perfil: dict) -> None:
        self.perfil = perfil
        self.nombre.texto = perfil["nombre_usuario"]
        self.descripcion.texto = perfil["descripcion"]
        self.avatar = perfil["avatar"] if perfil["avatar"] in AVATARES else "azul"

    def _error(self, error: ApiError) -> None:
        if error.estado == 401:  # la sesión venció o se cerró desde otro lado
            sesion.cerrar()
            self.siguiente_pantalla = "login"
            return
        self.mostrar(str(error), es_error=True)

    def draw(self, screen: pygame.Surface) -> None:
        self.dibujar_base(screen)
        self.boton_volver.draw(screen)
        if self.perfil is None:
            return

        p = self.perfil
        resumen = (
            f"Partidas: {p['partidas_jugadas']}    Victorias: {p['victorias']}    "
            f"Puntos: {p['puntos_totales']}"
        )
        for texto, y in ((resumen, 130), (p["correo"], 165)):
            linea = self.fuente_texto.render(texto, True, (200, 200, 215))
            screen.blit(linea, linea.get_rect(center=(self.centro_x, y)))

        pygame.draw.circle(screen, AVATARES[self.avatar], (self.x_campos + 22, 375), 20)
        nombre = self.fuente_texto.render(self.avatar, True, (200, 200, 215))
        screen.blit(nombre, (self.x_campos + 52, 366))
        self.boton_avatar.draw(screen)
        self.boton_guardar.draw(screen)
