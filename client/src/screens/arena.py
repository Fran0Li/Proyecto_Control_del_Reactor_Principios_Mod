"""Pantalla de la arena (versión mínima): un círculo rojo por jugador sobre fondo blanco."""

import pygame

from src.config import CONTROL_PUERTO
from src.entrada import ControlesJugador, crear_fuentes
from src.screens.panel_canal import PanelCanal

BLANCO = (255, 255, 255)
ROJO = (220, 30, 30)
SUAVIZADO = 0.35  # cuánto se acerca al punto nuevo en cada cuadro (el servidor manda ~20 por s)
CONTROLES = ("arriba", "abajo", "izquierda", "derecha", "accion")


class ArenaScreen:
    def __init__(self, ancho: int, alto: int) -> None:
        self.ancho, self.alto = ancho, alto
        self.siguiente_pantalla: str | None = None
        self.activa = False
        self.panel: PanelCanal | None = None
        self.volver_a = "lobby"
        self.controles: ControlesJugador | None = None
        self.visuales: dict[int, list[float]] = {}  # posición dibujada (suavizada)

    # ciclo de vida

    def preparar(self, panel: PanelCanal, volver_a: str) -> None:
        """La llama el ciclo principal justo antes de mostrar la arena."""
        self.cerrar()
        self.panel = panel
        self.volver_a = volver_a
        self.siguiente_pantalla = None
        if panel.canal is not None:
            fuentes = crear_fuentes(self.ancho, self.alto, CONTROL_PUERTO)
            self.controles = ControlesJugador(fuentes, panel.canal.enviar)
        self.activa = True

    def cerrar(self) -> None:
        if self.controles is not None:
            self.controles.cerrar()
            self.controles = None
        self.activa = False
        self.visuales = {}

    def _salir(self) -> None:
        self._soltar_todo()
        self.siguiente_pantalla = self.volver_a
        self.cerrar()

    def _soltar_todo(self) -> None:
        """Al salir, el servidor no debe seguir moviendo al jugador con una tecla apretada."""
        if self.panel is None or self.panel.canal is None:
            return
        for control in CONTROLES:
            self.panel.canal.enviar(
                {"tipo": "entrada", "control": control, "estado": "liberado", "origen": "teclado"}
            )

    # eventos y actualización 

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._salir()
        elif self.controles is not None:
            self.controles.procesar(event)

    def update(self) -> None:
        if not self.activa or self.panel is None:
            return
        if self.controles is not None:
            self.controles.actualizar()
        if self.panel.estado is not None:
            self._acercar(self.panel.estado["jugadores"])

    def _acercar(self, jugadores: list[dict]) -> None:
        """Mueve lo dibujado hacia lo que dice el servidor, para que no avance a saltos."""
        presentes = set()
        for jugador in jugadores:
            jugador_id = jugador["jugador_id"]
            presentes.add(jugador_id)
            actual = self.visuales.get(jugador_id)
            if actual is None:
                self.visuales[jugador_id] = [float(jugador["x"]), float(jugador["y"])]
            else:
                actual[0] += (jugador["x"] - actual[0]) * SUAVIZADO
                actual[1] += (jugador["y"] - actual[1]) * SUAVIZADO
        for jugador_id in list(self.visuales):
            if jugador_id not in presentes:
                del self.visuales[jugador_id]

    # dibujo 

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BLANCO)
        estado = self.panel.estado if self.panel is not None else None
        if estado is not None:
            # la arena del servidor mide 960 x 540 y la ventana tiene 960 de ancho: se dibuja 1 a 1
            for jugador in estado["jugadores"]:
                x, y = self.visuales.get(jugador["jugador_id"], [jugador["x"], jugador["y"]])
                pygame.draw.circle(screen, ROJO, (int(x), int(y)), estado["arena"]["radio"])
        if self.controles is not None:
            self.controles.dibujar(screen)  # botones táctiles, solo en el navegador