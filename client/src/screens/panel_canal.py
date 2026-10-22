"""Panel que muestra el canal en tiempo real de la partida y quién está en línea."""

import pygame

from src.realtime_client import CanalPartida

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

    async def abrir(self, partida_id: int, token: str) -> None:
        self.cerrar()
        self.conectados = []
        self.canal = CanalPartida(partida_id, token)
        await self.canal.conectar()

    def update(self) -> None:
        """Lee lo que llegó por el canal desde el cuadro anterior."""
        if self.canal is None:
            return
        for evento in self.canal.leer_mensajes():
            if "conectados" in evento:
                self.conectados = evento["conectados"]

    def cerrar(self) -> None:
        if self.canal is not None:
            self.canal.cerrar()
            self.canal = None

    def _texto_estado(self) -> str:
        estado = self.canal.estado if self.canal is not None else "desconectada"
        if estado.startswith("error"):
            return "sin conexión"
        return ESTADOS.get(estado, estado)

    def draw(self, screen: pygame.Surface, centro_x: int, y: int) -> None:
        if self.canal is None:
            return
        linea = f"Canal: {self._texto_estado()} - jugadores en línea: {self.conectados}"
        texto = self.fuente.render(linea, True, COLOR_TEXTO)
        screen.blit(texto, texto.get_rect(center=(centro_x, y)))