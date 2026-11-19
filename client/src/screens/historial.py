"""Historial y estadísticas del jugador conectado (US-20)."""

import pygame

from src import sesion
from src.api_client import ApiError, obtener_historial, obtener_logros
from src.screens.componentes import boton_secundario
from src.screens.formulario import PantallaFormulario

COLOR_CAJA = (24, 32, 56)
COLOR_TEXTO = (230, 230, 240)
COLOR_SUAVE = (150, 160, 190)
COLOR_GANO = (90, 220, 130)
COLOR_LOGRO = (255, 215, 80)
MAX_PARTIDAS = 8
ESTADISTICAS = (
    ("partidas_jugadas", "Partidas"),
    ("victorias", "Victorias"),
    ("puntos_totales", "Puntos"),
    ("mejor_puntaje", "Mejor puntaje"),
    ("logros", "Logros"),
)


def describir_partida(partida: dict) -> str:
    fecha = (partida["fecha"] or "")[:10]  # viene como "2026-11-19T21:30:00"
    puesto = partida["posicion"] or "-"
    escenario = str(partida["escenario"] or "").replace("_", " ")
    return (
        f"{fecha}   Partida #{partida['partida_id']}   {escenario}   "
        f"puesto {puesto} de {partida['jugadores']}   {partida['puntaje']} pts"
    )


class HistorialScreen(PantallaFormulario):
    titulo = "MI HISTORIAL"
    y_mensaje = 300

    def __init__(self, width: int) -> None:
        super().__init__(width)
        self.boton_volver = boton_secundario(pygame.Rect(20, 20, 120, 40), "Volver")
        self.historial: dict | None = None
        self.logros: list[str] = []  # nombres de los logros desbloqueados (US-27)

    def al_mostrar(self) -> None:
        self.historial = None
        self.logros = []
        self.mostrar("Cargando...")
        self.lanzar(self._cargar)

    async def _cargar(self) -> None:
        try:
            self.historial = await obtener_historial(sesion.token())
            logros = await obtener_logros(sesion.token())
        except ApiError as error:
            self.mostrar(str(error), es_error=True)
            return
        self.logros = [logro["nombre"] for logro in logros if logro["obtenido"]]
        vacio = "Todavía no terminaste ninguna partida."
        self.mostrar("" if self.historial["partidas"] else vacio)

    def handle_event(self, event: pygame.event.Event) -> None:
        escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if escape or self.boton_volver.fue_presionado(event):
            self.siguiente_pantalla = "lobby"

    def draw(self, screen: pygame.Surface) -> None:
        self.dibujar_base(screen)
        self.boton_volver.draw(screen)
        if self.historial is None:
            return
        self._dibujar_resumen(screen, self.historial["resumen"])
        if self.logros:
            texto = "Logros: " + ", ".join(self.logros)
            imagen = self.fuente_texto.render(texto, True, COLOR_LOGRO)
            screen.blit(imagen, imagen.get_rect(center=(self.centro_x, 215)))
        y = 250
        for partida in self.historial["partidas"][:MAX_PARTIDAS]:
            color = COLOR_GANO if partida["gano"] else COLOR_TEXTO
            imagen = self.fuente_texto.render(describir_partida(partida), True, color)
            screen.blit(imagen, imagen.get_rect(center=(self.centro_x, y)))
            y += 34

    def _dibujar_resumen(self, screen: pygame.Surface, resumen: dict) -> None:
        ancho = 150
        x = self.centro_x - ancho * len(ESTADISTICAS) // 2
        for clave, etiqueta in ESTADISTICAS:
            rect = pygame.Rect(x + 6, 120, ancho - 12, 70)
            pygame.draw.rect(screen, COLOR_CAJA, rect, border_radius=10)
            valor = self.fuente_titulo.render(str(resumen[clave]), True, COLOR_TEXTO)
            screen.blit(valor, valor.get_rect(center=(rect.centerx, rect.y + 26)))
            nombre = self.fuente_texto.render(etiqueta, True, COLOR_SUAVE)
            screen.blit(nombre, nombre.get_rect(center=(rect.centerx, rect.y + 56)))
            x += ancho
