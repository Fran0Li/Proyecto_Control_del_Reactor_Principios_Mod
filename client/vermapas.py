"""Visor de mapas: muestra cada escenario sin servidor, sin Docker y sin iniciar sesión.

Usa el mismo motor del servidor (solo Python, sin base de datos) y la misma pantalla de arena del
cliente, así que lo que se ve es lo que se vería jugando: fondo, obstáculos, barreras móviles,
guardianes, celdas, reactor y jugadores.

Uso, desde la carpeta client:
    python ver_mapas.py                      abre el visor con el laboratorio
    python ver_mapas.py --mapa complejo_militar
    python ver_mapas.py --capturas           guarda una imagen de cada mapa en capturas/ y sale

Teclas en el visor:
    1 a 5            cambia de mapa
    flechas o WASD   mueve al jugador 1
    espacio          acción (extraer energía junto al reactor)
    J                agrega otro jugador quieto (hasta 4), para ver sus colores y números
    R                reinicia el mapa
    C                guarda una imagen del mapa en client/capturas
    ESC              sale
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

CLIENTE = Path(__file__).resolve().parent
sys.path.insert(0, str(CLIENTE.parent / "server"))  # el motor del servidor: solo Python

import pygame  # noqa: E402
from app.realtime.escenarios import NOMBRES_ESCENARIOS, crear_escenario  # noqa: E402
from app.realtime.motor_partida import CICLO_S, MotorPartida  # noqa: E402

from src.config import WINDOW_SIZE  # noqa: E402
from src.screens.arena import ArenaScreen  # noqa: E402

CARPETA_CAPTURAS = CLIENTE / "capturas"
MAX_JUGADORES = 4
TECLAS = {
    pygame.K_UP: "arriba",
    pygame.K_w: "arriba",
    pygame.K_DOWN: "abajo",
    pygame.K_s: "abajo",
    pygame.K_LEFT: "izquierda",
    pygame.K_a: "izquierda",
    pygame.K_RIGHT: "derecha",
    pygame.K_d: "derecha",
    pygame.K_SPACE: "accion",
}
TECLAS_DE_MAPA = {pygame.K_1 + i: nombre for i, nombre in enumerate(NOMBRES_ESCENARIOS)}


class PanelDeMapa:
    """Lo mínimo del panel del canal que usa la arena: el estado y nada de red."""

    canal = None
    resultado = None

    def __init__(self) -> None:
        self.estado: dict | None = None


class Visor:
    def __init__(self, pantalla: pygame.Surface, escenario: str) -> None:
        self.pantalla = pantalla
        self.ciclo = asyncio.new_event_loop()
        self.panel = PanelDeMapa()
        self.arena = ArenaScreen(*WINDOW_SIZE)
        self.fuente = pygame.font.Font(None, 24)
        self.jugadores = 1
        self.acumulado = 0.0
        self.escenario = escenario
        self.motor: MotorPartida
        self.cambiar_mapa(escenario)

    def cambiar_mapa(self, escenario: str) -> None:
        self.escenario = escenario
        arena, guardianes = crear_escenario(escenario)
        self.motor = MotorPartida(1, arena=arena, guardianes=guardianes, escenario=escenario)
        for jugador_id in range(1, self.jugadores + 1):
            self.motor.agregar_jugador(jugador_id, f"Jugador {jugador_id}")
        self.arena.preparar(self.panel, "lobby")
        self.actualizar_estado()

    def agregar_jugador(self) -> None:
        if self.jugadores < MAX_JUGADORES:
            self.jugadores += 1
            self.motor.agregar_jugador(self.jugadores, f"Jugador {self.jugadores}")

    def actualizar_estado(self) -> None:
        self.panel.estado = self.motor.estado()

    def avanzar(self, segundos: float) -> None:
        """Corre el motor en pasos de 50 ms, como el servidor."""
        self.acumulado += segundos
        while self.acumulado >= CICLO_S:
            self.ciclo.run_until_complete(self.motor.tick())
            self.acumulado -= CICLO_S
        self.actualizar_estado()
        self.arena.update()

    def dibujar(self) -> None:
        self.arena.draw(self.pantalla)
        ayuda = f"{self.escenario}   1-5 mapa, flechas mover, espacio acción, J jugador, C captura"
        imagen = self.fuente.render(ayuda, True, (40, 40, 40))
        self.pantalla.blit(imagen, (12, WINDOW_SIZE[1] - 30))

    def guardar_captura(self) -> Path:
        CARPETA_CAPTURAS.mkdir(exist_ok=True)
        ruta = CARPETA_CAPTURAS / f"{self.escenario}.png"
        pygame.image.save(self.pantalla, str(ruta))
        return ruta

    def entrada(self, evento: pygame.event.Event) -> bool:
        """Procesa una tecla. Devuelve False si hay que salir."""
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                return False
            if evento.key in TECLAS_DE_MAPA:
                self.cambiar_mapa(TECLAS_DE_MAPA[evento.key])
            elif evento.key == pygame.K_j:
                self.agregar_jugador()
            elif evento.key == pygame.K_r:
                self.cambiar_mapa(self.escenario)
            elif evento.key == pygame.K_c:
                print("Captura guardada en", self.guardar_captura())
        if evento.type in (pygame.KEYDOWN, pygame.KEYUP) and evento.key in TECLAS:
            estado = "presionado" if evento.type == pygame.KEYDOWN else "liberado"
            self.motor.aplicar_entrada(1, TECLAS[evento.key], estado)
        return True


def guardar_todas_las_capturas(pantalla: pygame.Surface, segundos: float = 3.0) -> None:
    """Una imagen por mapa, después de unos segundos de partida para que todo esté en movimiento."""
    for escenario in NOMBRES_ESCENARIOS:
        visor = Visor(pantalla, escenario)
        for _ in range(MAX_JUGADORES - 1):
            visor.agregar_jugador()
        visor.cambiar_mapa(escenario)
        for _ in range(int(segundos / CICLO_S)):
            visor.avanzar(CICLO_S)
        visor.dibujar()
        print("Captura guardada en", visor.guardar_captura())


def main() -> None:
    parser = argparse.ArgumentParser(description="Visor de mapas de Control del Reactor")
    parser.add_argument("--mapa", choices=NOMBRES_ESCENARIOS, default=NOMBRES_ESCENARIOS[0])
    parser.add_argument("--capturas", action="store_true", help="guarda una imagen de cada mapa")
    argumentos = parser.parse_args()

    if argumentos.capturas:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # no hace falta abrir la ventana
    pygame.init()
    pantalla = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Visor de mapas - Control del Reactor")
    if argumentos.capturas:
        guardar_todas_las_capturas(pantalla)
        return

    visor = Visor(pantalla, argumentos.mapa)
    reloj = pygame.time.Clock()
    ejecutando = True
    while ejecutando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT or not visor.entrada(evento):
                ejecutando = False
        visor.avanzar(reloj.tick(60) / 1000)
        visor.dibujar()
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()