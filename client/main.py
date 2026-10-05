"""Cliente pygame de Control del Reactor (esqueleto).

Por ahora solo abre la ventana y muestra si el backend responde.
"""

import pygame
import requests

from src.config import FPS, SERVER_URL, WINDOW_SIZE


def server_status() -> str:
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=2)
        return "Servidor: conectado" if response.ok else "Servidor: error"
    except requests.RequestException:
        return "Servidor: sin conexión"


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Control del Reactor")
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 64)
    text_font = pygame.font.Font(None, 32)
    status = server_status()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                status = server_status()  # R para volver a probar la conexión

        screen.fill((12, 16, 32))
        title = title_font.render("CONTROL DEL REACTOR", True, (80, 200, 255))
        info = text_font.render(f"{status}  (R para reintentar)", True, (200, 200, 200))
        screen.blit(title, title.get_rect(center=(WINDOW_SIZE[0] // 2, 260)))
        screen.blit(info, info.get_rect(center=(WINDOW_SIZE[0] // 2, 340)))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
