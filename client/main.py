"""Cliente pygame de Control del Reactor.

Abre en el login (US-03); desde ahí se crea una cuenta (US-01) o se entra al lobby. Del lobby
se crea una partida (US-07) o se va a buscar una para unirse (US-08).
Cuando el creador inicia la partida (US-17) todos pasan solos a la arena, y al terminar se ve la
ceremonia con el podio (US-18).
Abajo muestra si el backend responde.

El ciclo principal es async (ADR 0002): así el mismo código corre en escritorio
(`python main.py`) y en el navegador del celular (`pygbag .`).
"""

import asyncio

import pygame

from src import navegador, sesion
from src.api_client import estado_servidor
from src.config import FPS, WINDOW_SIZE
from src.screens.arena import ArenaScreen
from src.screens.buscar_partida import BuscarPartidaScreen
from src.screens.ceremonia import CeremoniaScreen
from src.screens.historial import HistorialScreen
from src.screens.lobby import LobbyScreen
from src.screens.login import LoginScreen
from src.screens.perfil import PerfilScreen
from src.screens.ranking import RankingScreen
from src.screens.recuperar import RecuperarScreen
from src.screens.registro import RegistroScreen
from src.screens.verificar_correo import VerificarCorreoScreen


async def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Control del Reactor")
    clock = pygame.time.Clock()
    text_font = pygame.font.Font(None, 32)
    lobby = LobbyScreen(WINDOW_SIZE[0])
    buscar = BuscarPartidaScreen(WINDOW_SIZE[0])
    arena = ArenaScreen(*WINDOW_SIZE)
    ceremonia = CeremoniaScreen(*WINDOW_SIZE)
    # cada pantalla pide cambiar poniendo su `siguiente_pantalla` con una de estas claves
    pantallas = {
        "login": LoginScreen(WINDOW_SIZE[0]),
        "registro": RegistroScreen(WINDOW_SIZE[0]),
        "verificar": VerificarCorreoScreen(WINDOW_SIZE[0]),
        "recuperar": RecuperarScreen(WINDOW_SIZE[0]),
        "perfil": PerfilScreen(WINDOW_SIZE[0]),
        "ranking": RankingScreen(WINDOW_SIZE[0]),
        "historial": HistorialScreen(WINDOW_SIZE[0]),
        "lobby": lobby,
        "buscar": buscar,
        "arena": arena,
        "ceremonia": ceremonia,
    }
    pantalla = pantallas["login"]

    status = "Servidor: comprobando..."

    async def comprobar_servidor() -> None:
        nonlocal status
        status = await estado_servidor()

    tarea_estado = asyncio.create_task(comprobar_servidor())

    dt = 0.0
    running = True
    while running:
        for event in pygame.event.get():
            navegador.al_tocar(event)  # en el celular, el primer toque pone pantalla completa
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                if tarea_estado.done():  # F5 para volver a probar la conexión
                    status = "Servidor: comprobando..."
                    tarea_estado = asyncio.create_task(comprobar_servidor())
            pantalla.handle_event(event)
            panel = getattr(pantalla, "panel", None)  # botones de la arena y de iniciar
            if panel is not None and pantalla is not arena:
                panel.handle_event(event)

        panel = getattr(pantalla, "panel", None)
        if panel is not None and panel.quiere_arena and pantalla is not arena:
            panel.quiere_arena = False
            arena.preparar(panel, volver_a="lobby" if pantalla is lobby else "buscar")
            pantalla.siguiente_pantalla = "arena"
        destino = pantalla.siguiente_pantalla
        if destino:
            pantalla.siguiente_pantalla = None
            if destino == "verificar":  # el registro o el login le pasan el correo
                pantallas["verificar"].preparar(pantalla.correo_pendiente)
            elif destino == "ceremonia":  # la arena terminó: se usa el aviso de fin del canal
                panel = arena.panel
                ceremonia.preparar(panel.resultado, panel.partida_id, sesion.token())
                panel.cerrar()  # la partida ya terminó
            pantalla = pantallas[destino]
            if hasattr(pantalla, "al_mostrar"):
                pantalla.al_mostrar()
        lobby.update()
        buscar.update()
        if pantalla is arena and arena.panel is not None:
            arena.panel.quiere_arena = False  # ya está en la arena: el aviso de inicio no aplica
        arena.update()
        if pantalla is ceremonia:
            ceremonia.update(dt)
        pantalla.draw(screen)
        info = text_font.render(f"{status}  (F5 para reintentar)", True, (200, 200, 200))
        screen.blit(info, info.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 40)))
        pygame.display.flip()
        dt = clock.tick(FPS) / 1000
        await asyncio.sleep(0)  # obligatorio en pygbag: le devuelve el control al navegador
    lobby.cerrar()
    buscar.cerrar()
    arena.cerrar()
    pygame.quit()


asyncio.run(main())