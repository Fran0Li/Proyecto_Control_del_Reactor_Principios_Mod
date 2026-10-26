"""Panel que muestra el canal en tiempo real de la partida y quién está en línea."""

import pygame

from src.realtime_client import CanalPartida
from src.screens.componentes import Boton

COLOR_TEXTO = (255, 255, 255)

ESTADOS = {
    "conectando": "conectando...",
    "abierta": "conectado",
    "cerrada": "desconectado",
}


class PanelCanal:
    def __init__(self) -> None:
        self.fuente = pygame.font.Font(None, 32)
        self.canal: CanalPartida | None = None
        self.conectados: list[int] = []
        self.estado: dict | None = None  # último estado de la arena que mandó el servidor
        self.quiere_arena = False
        self.boton_arena = Boton(pygame.Rect(0, 0, 260, 44), "Entrar a la arena")

    async def abrir(self, partida_id: int, jugador_id: int) -> None:
        self.cerrar()
        self.conectados = []
        self.estado = None
        self.canal = CanalPartida(partida_id, jugador_id)
        await self.canal.conectar()

    def update(self) -> None:
        """Lee lo que llegó por el canal desde el cuadro anterior."""
        if self.canal is None:
            return
        for evento in self.canal.leer_mensajes():
            if "conectados" in evento:
                self.conectados = evento["conectados"]
            elif evento.get("tipo") == "estado":
                self.estado = evento

    def cerrar(self) -> None:
        if self.canal is not None:
            self.canal.cerrar()
            self.canal = None
        self.estado = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.canal is not None and self.boton_arena.fue_presionado(event):
            self.quiere_arena = True

    def _texto_estado(self) -> str:
        estado = self.canal.estado if self.canal is not None else "desconectada"
        if estado.startswith("error"):
            return "sin conexión"
        return ESTADOS.get(estado, estado)

    def draw(self, screen: pygame.Surface, centro_x: int, y: int, con_boton: bool = True) -> None:
        if self.canal is None:
            return
        linea = f"Canal: {self._texto_estado()} - jugadores en línea: {self.conectados}"
        texto = self.fuente.render(linea, True, COLOR_TEXTO)
        screen.blit(texto, texto.get_rect(center=(centro_x, y)))
        if con_boton:
            self.boton_arena.rect.center = (centro_x, y + 50)
            self.boton_arena.draw(screen)