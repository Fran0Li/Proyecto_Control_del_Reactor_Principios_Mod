"""Cliente pygame de Control del Reactor.

Abre la ventana en la pantalla de registro (US-01), desde donde se pasa al lobby.
Abajo muestra si el backend responde.

El ciclo principal es async (ADR 0002): así el mismo código corre en escritorio
(`python main.py`) y en el navegador del celular (`pygbag .`).
"""

import asyncio

import pygame

from src.api_client import estado_servidor
from src.config import FPS, WINDOW_SIZE
from src.screens.lobby import LobbyScreen
from src.screens.registro import RegistroScreen


async def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Control del Reactor")
    clock = pygame.time.Clock()
    text_font = pygame.font.Font(None, 32)
    registro = RegistroScreen(WINDOW_SIZE[0])
    lobby = LobbyScreen(WINDOW_SIZE[0])
    pantalla = registro

    status = "Servidor: comprobando..."

    async def comprobar_servidor() -> None:
        nonlocal status
        status = await estado_servidor()

    tarea_estado = asyncio.create_task(comprobar_servidor())

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                if tarea_estado.done():  # F5 para volver a probar la conexión
                    status = "Servidor: comprobando..."
                    tarea_estado = asyncio.create_task(comprobar_servidor())
            pantalla.handle_event(event)

        if pantalla is registro and registro.siguiente_pantalla == "lobby":
            pantalla = lobby

        pantalla.draw(screen)
        info = text_font.render(f"{status}  (F5 para reintentar)", True, (200, 200, 200))
        screen.blit(info, info.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 40)))
        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(0)  # obligatorio en pygbag: le devuelve el control al navegador

    pygame.quit()


asyncio.run(main())
