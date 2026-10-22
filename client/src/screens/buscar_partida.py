"""Pantalla para buscar partidas en espera y unirse a una (US-08)."""

import asyncio

import pygame

from src import sesion
from src.api_client import ApiError, listar_partidas_disponibles, unirse_a_partida
from src.screens.componentes import Boton
from src.screens.panel_canal import PanelCanal

COLOR_FONDO = (12, 16, 32)
COLOR_TITULO = (80, 200, 255)
COLOR_FILA = (24, 32, 56)
COLOR_TEXTO = (230, 230, 240)
COLOR_OK = (90, 220, 130)
COLOR_ERROR = (240, 100, 100)

MAX_FILAS = 6
ANCHO_FILA = 660
ALTO_FILA = 46
SEPARACION = 54
Y_PRIMERA_FILA = 130


class BuscarPartidaScreen:
    def __init__(self, width: int) -> None:
        self.centro_x = width // 2
        self.boton_actualizar = Boton(pygame.Rect(self.centro_x - 215, 540, 200, 44), "Actualizar")
        self.boton_volver = Boton(
            pygame.Rect(self.centro_x + 15, 540, 200, 44),
            "Volver",
            color=(40, 50, 80),
            color_hover=(60, 75, 115),
        )
        self.fuente_titulo = pygame.font.Font(None, 56)
        self.fuente_texto = pygame.font.Font(None, 30)
        self.partidas: list[dict] = []
        self.botones_unirse: list[Boton] = []
        self.mensaje = ""
        self.mensaje_es_error = False
        self.unido_a: int | None = None
        self.siguiente_pantalla: str | None = None
        self.panel = PanelCanal()
        self._tarea: asyncio.Task | None = None

    # ciclo de vida 

    def al_mostrar(self) -> None:
        """La llama el ciclo principal cada vez que se entra a esta pantalla."""
        if not self.ocupada():
            self._tarea = asyncio.create_task(self._cargar())

    def ocupada(self) -> bool:
        return self._tarea is not None and not self._tarea.done()

    def update(self) -> None:
        self.panel.update()

    def cerrar(self) -> None:
        self.panel.cerrar()

    # eventos

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.boton_volver.fue_presionado(event):
            self.siguiente_pantalla = "lobby"
            return
        if self.unido_a is not None or self.ocupada():
            return  # ya está en una partida (solo puede volver) o hay una petición en curso
        if self.boton_actualizar.fue_presionado(event):
            self._tarea = asyncio.create_task(self._cargar())
            return
        for partida, boton in zip(self.partidas[:MAX_FILAS], self.botones_unirse, strict=False):
            if boton.fue_presionado(event):
                self._tarea = asyncio.create_task(self._unirse(partida["id"]))
                return

    # peticiones al servidor

    def _mostrar(self, mensaje: str, es_error: bool) -> None:
        self.mensaje = mensaje
        self.mensaje_es_error = es_error

    async def _cargar(self) -> None:
        self._mostrar("Buscando partidas...", es_error=False)
        try:
            self.partidas = await listar_partidas_disponibles()
        except ApiError as error:
            self.partidas = []
            self.botones_unirse = []
            self._mostrar(str(error), es_error=True)
            return
        self._crear_botones()
        sin_partidas = "No hay partidas esperando jugadores. Crea una desde el lobby."
        self._mostrar("" if self.partidas else sin_partidas, es_error=False)

    async def _unirse(self, partida_id: int) -> None:
        self._mostrar("Uniéndose...", es_error=False)
        try:
            partida = await unirse_a_partida(partida_id, sesion.jugador_id())
        except ApiError as error:
            self._mostrar(str(error), es_error=True)
            return
        self.unido_a = partida["id"]
        self.boton_volver.rect.centerx = self.centro_x  # sin "Actualizar", queda al centro
        self._mostrar(f"Te uniste a la partida #{partida['id']}", es_error=False)
        await self.panel.abrir(partida["id"], sesion.token())

    # dibujo

    def _x_fila(self) -> int:
        return self.centro_x - ANCHO_FILA // 2

    def _y_fila(self, indice: int) -> int:
        return Y_PRIMERA_FILA + indice * SEPARACION

    def _crear_botones(self) -> None:
        self.botones_unirse = [
            Boton(
                pygame.Rect(self._x_fila() + ANCHO_FILA - 130, self._y_fila(i) + 5, 120, 36),
                "Unirse",
            )
            for i in range(min(len(self.partidas), MAX_FILAS))
        ]

    @staticmethod
    def _describir(partida: dict) -> str:
        jugadores = partida["jugadores"]
        plural = "jugador" if jugadores == 1 else "jugadores"
        escenario = str(partida["escenario"]).replace("_", " ")
        return f"Partida #{partida['id']}   {escenario}   {jugadores} {plural}"

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_FONDO)
        titulo = self.fuente_titulo.render("PARTIDAS DISPONIBLES", True, COLOR_TITULO)
        screen.blit(titulo, titulo.get_rect(center=(self.centro_x, 70)))

        if self.unido_a is None:
            self._dibujar_filas(screen)
        else:
            self.panel.draw(screen, self.centro_x, 300)

        if self.mensaje:
            color = COLOR_ERROR if self.mensaje_es_error else COLOR_OK
            texto = self.fuente_texto.render(self.mensaje, True, color)
            y = 250 if self.unido_a is not None else 500
            screen.blit(texto, texto.get_rect(center=(self.centro_x, y)))

        if self.unido_a is None:
            self.boton_actualizar.draw(screen)
        self.boton_volver.draw(screen)

    def _dibujar_filas(self, screen: pygame.Surface) -> None:
        visibles = self.partidas[:MAX_FILAS]
        for i, (partida, boton) in enumerate(zip(visibles, self.botones_unirse, strict=False)):
            rect = pygame.Rect(self._x_fila(), self._y_fila(i), ANCHO_FILA, ALTO_FILA)
            pygame.draw.rect(screen, COLOR_FILA, rect, border_radius=8)
            texto = self.fuente_texto.render(self._describir(partida), True, COLOR_TEXTO)
            screen.blit(texto, texto.get_rect(midleft=(rect.x + 14, rect.centery)))
            boton.draw(screen)
        if len(self.partidas) > MAX_FILAS:
            resto = len(self.partidas) - MAX_FILAS
            aviso = self.fuente_texto.render(f"... y {resto} más", True, COLOR_TEXTO)
            screen.blit(aviso, aviso.get_rect(center=(self.centro_x, self._y_fila(MAX_FILAS) + 8)))