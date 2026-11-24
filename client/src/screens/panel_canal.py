"""Panel que muestra el canal en tiempo real de la partida y quién está en línea.

También tiene el botón para que el creador inicie la partida (US-17): sale en gris con
"Esperando jugadores (1/2)" hasta que haya suficientes conectados. Cuando el servidor avisa que
empezó, el panel pide ir a la arena, y cuando termina guarda las posiciones finales.
"""

import asyncio

import pygame

from src.api_client import ApiError, iniciar_partida
from src.config import MINIMO_JUGADORES
from src.realtime_client import CanalPartida
from src.screens.componentes import Boton

COLOR_TEXTO = (255, 255, 255)
COLOR_ERROR = (240, 100, 100)
GRIS_BOTON = (70, 75, 90)
GRIS_TEXTO = (170, 175, 190)

ESTADOS = {
    "conectando": "conectando...",
    "abierta": "conectado",
    "cerrada": "desconectado",
}


class PanelCanal:
    def __init__(self) -> None:
        self.fuente = pygame.font.Font(None, 32)
        self.canal: CanalPartida | None = None
        self.partida_id: int | None = None
        self.token = ""
        self.es_creador = False
        self.conectados: list[int] = []
        self.estado: dict | None = None  # último estado de la arena que mandó el servidor
        self.resultado: dict | None = None  # el aviso de partida_finalizada
        self.error = ""
        self.quiere_arena = False
        self.boton_arena = Boton(pygame.Rect(0, 0, 260, 44), "Entrar a la arena")
        self.boton_iniciar = Boton(pygame.Rect(0, 0, 260, 44), "Iniciar partida")
        # el mismo lugar que el de iniciar, pero en gris y sin acción mientras faltan jugadores
        self.boton_esperando = Boton(
            pygame.Rect(0, 0, 320, 44),
            "",
            color=GRIS_BOTON,
            color_hover=GRIS_BOTON,
            color_texto=GRIS_TEXTO,
        )
        self._tarea: asyncio.Task | None = None
        # Último seq de entrada enviado por este canal (el servidor los cuenta por conexión)
        self.seq_enviada = 0

    async def abrir(self, partida_id: int, token: str, es_creador: bool = False) -> None:
        self.cerrar()
        self.partida_id = partida_id
        self.token = token
        self.es_creador = es_creador
        self.conectados = []
        self.seq_enviada = 0  # conexión nueva: el servidor empieza a contar de cero
        self.resultado = None
        self.error = ""
        self.canal = CanalPartida(partida_id, token)
        await self.canal.conectar()

    def update(self) -> None:
        """Lee lo que llegó por el canal desde el cuadro anterior."""
        if self.canal is None:
            return
        for evento in self.canal.leer_mensajes():
            tipo = evento.get("tipo")
            if "conectados" in evento:
                self.conectados = evento["conectados"]
            elif tipo == "estado":
                self.estado = evento
            elif tipo == "partida_iniciada":
                self.resultado = None
                self.quiere_arena = True  # todos pasan a la arena al mismo tiempo
            elif tipo == "partida_finalizada":
                self.resultado = evento

    def cerrar(self) -> None:
        if self.canal is not None:
            self.canal.cerrar()
            self.canal = None
        self.estado = None

    # estado de la partida

    def estado_partida(self) -> str:
        """ "esperando", "en_curso" o "finalizada", según el último estado del servidor."""
        if self.estado is None:
            return "esperando"
        return self.estado.get("partida", {}).get("estado", "esperando")

    def puede_iniciar(self) -> bool:
        return self.canal is not None and self.es_creador and self.estado_partida() == "esperando"

    def cantidad_conectados(self) -> int:
        return len(set(self.conectados))

    def hay_jugadores_suficientes(self) -> bool:
        return self.cantidad_conectados() >= MINIMO_JUGADORES

    def ocupado(self) -> bool:
        return self._tarea is not None and not self._tarea.done()

    async def _iniciar(self) -> None:
        self.error = ""
        try:
            await iniciar_partida(self.partida_id, self.token)
        except ApiError as error:
            self.error = str(error)

    # eventos y dibujo

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.canal is None:
            return
        if self.boton_arena.fue_presionado(event):
            self.quiere_arena = True
        elif (
            self.puede_iniciar()
            and self.hay_jugadores_suficientes()
            and not self.ocupado()
            and self.boton_iniciar.fue_presionado(event)
        ):
            self._tarea = asyncio.create_task(self._iniciar())

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
        if not con_boton:
            return
        self.boton_arena.rect.center = (centro_x, y + 50)
        self.boton_arena.draw(screen)
        if self.puede_iniciar():
            if self.hay_jugadores_suficientes():
                self.boton_iniciar.rect.center = (centro_x, y + 105)
                self.boton_iniciar.draw(screen)
            else:
                conectados = min(self.cantidad_conectados(), MINIMO_JUGADORES)
                self.boton_esperando.texto = (
                    f"Esperando jugadores ({conectados}/{MINIMO_JUGADORES})"
                )
                self.boton_esperando.rect.center = (centro_x, y + 105)
                self.boton_esperando.draw(screen)
        if self.error:
            aviso = self.fuente.render(self.error, True, COLOR_ERROR)
            screen.blit(aviso, aviso.get_rect(center=(centro_x, y + 150)))
