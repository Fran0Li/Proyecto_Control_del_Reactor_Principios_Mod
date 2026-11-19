"""Ranking global: los 10 mejores y el puesto propio (US-19)."""

import pygame

from src import sesion
from src.api_client import ApiError, obtener_ranking
from src.screens.componentes import boton_secundario
from src.screens.formulario import PantallaFormulario

COLOR_FILA = (24, 32, 56)
COLOR_PROPIA = (60, 70, 30)
COLOR_TEXTO = (230, 230, 240)
COLOR_SUAVE = (150, 160, 190)
MEDALLAS = {1: (230, 180, 40), 2: (180, 185, 200), 3: (190, 120, 60)}
ANCHO_FILA = 620
Y_PRIMERA_FILA = 135
ALTO_FILA = 36


class RankingScreen(PantallaFormulario):
    titulo = "RANKING GLOBAL"
    y_mensaje = 300

    def __init__(self, width: int) -> None:
        super().__init__(width)
        self.boton_volver = boton_secundario(pygame.Rect(20, 20, 120, 40), "Volver")
        self.ranking: dict | None = None

    def al_mostrar(self) -> None:
        self.ranking = None
        self.mostrar("Cargando...")
        self.lanzar(self._cargar)

    async def _cargar(self) -> None:
        try:
            self.ranking = await obtener_ranking(sesion.token())
        except ApiError as error:
            self.mostrar(str(error), es_error=True)
            return
        vacio = "Todavía nadie terminó una partida."
        self.mostrar("" if self.ranking["top"] else vacio)

    def handle_event(self, event: pygame.event.Event) -> None:
        escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if escape or self.boton_volver.fue_presionado(event):
            self.siguiente_pantalla = "lobby"

    def draw(self, screen: pygame.Surface) -> None:
        self.dibujar_base(screen)
        self.boton_volver.draw(screen)
        if self.ranking is None:
            return
        y = Y_PRIMERA_FILA
        self._columnas(screen, ("Jugador", "Puntos", "Victorias"), y - 18, COLOR_SUAVE)
        mi_id = sesion.jugador_id()
        for fila in self.ranking["top"]:
            self._fila(screen, fila, y, propia=fila["jugador_id"] == mi_id)
            y += ALTO_FILA + 6
        yo = self.ranking["yo"]
        if yo is not None and all(f["jugador_id"] != yo["jugador_id"] for f in self.ranking["top"]):
            texto = f"Tu puesto: {yo['posicion']}  -  {yo['puntos_totales']} puntos"
            imagen = self.fuente_texto.render(texto, True, COLOR_TEXTO)
            screen.blit(imagen, imagen.get_rect(center=(self.centro_x, y + 20)))

    def _fila(self, screen: pygame.Surface, fila: dict, y: int, propia: bool) -> None:
        x = self.centro_x - ANCHO_FILA // 2
        rect = pygame.Rect(x, y, ANCHO_FILA, ALTO_FILA)
        pygame.draw.rect(screen, COLOR_PROPIA if propia else COLOR_FILA, rect, border_radius=8)
        puesto = fila["posicion"]
        if puesto in MEDALLAS:
            pygame.draw.circle(screen, MEDALLAS[puesto], (x + 24, rect.centery), 13)
        numero = self.fuente_texto.render(str(puesto), True, COLOR_TEXTO)
        screen.blit(numero, numero.get_rect(center=(x + 24, rect.centery)))
        valores = (fila["nombre"] or "?", fila["puntos_totales"], fila["victorias"])
        self._columnas(screen, valores, rect.centery, COLOR_TEXTO)

    def _columnas(self, screen: pygame.Surface, valores: tuple, y: int, color: tuple) -> None:
        """Nombre a la izquierda; puntos y victorias alineados a la derecha de su columna."""
        x = self.centro_x - ANCHO_FILA // 2
        nombre, puntos, victorias = (self.fuente_texto.render(str(v), True, color) for v in valores)
        screen.blit(nombre, nombre.get_rect(midleft=(x + 60, y)))
        screen.blit(puntos, puntos.get_rect(midright=(x + 420, y)))
        screen.blit(victorias, victorias.get_rect(midright=(x + 580, y)))
