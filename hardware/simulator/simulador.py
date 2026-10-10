"""Simulador del control físico de Control del Reactor.

Abre una ventana con los 5 botones y envía por un socket local EXACTAMENTE las mismas líneas que
el Arduino envía por USB (docs/contrato-api-hardware.md, capa 1). Así se prueba todo lo que está
después del puerto serial sin tener el hardware.

Uso:
    python simulador.py                 # escucha en localhost:7777
    python simulador.py --puerto 7800

En el juego, usar como puerto del control:  socket://localhost:7777

Controles (con la ventana del simulador seleccionada):
    flechas o WASD = direcciones, espacio = acción, clic en los botones también funciona
    H = pausar o reanudar los latidos (para probar la desconexión a los 3 s)
"""

import argparse
import socket
import time

import pygame

ID_SIMULADOR = "CR-SIM-01"
VERSION = "1.0"
LATIDO_S = 1.0
ANCHO, ALTO = 800, 400

NOMBRE_SERIAL = {
    "arriba": "UP",
    "abajo": "DOWN",
    "izquierda": "LEFT",
    "derecha": "RIGHT",
    "accion": "ACTION",
}
TECLAS = {
    pygame.K_UP: "arriba", pygame.K_w: "arriba",
    pygame.K_DOWN: "abajo", pygame.K_s: "abajo",
    pygame.K_LEFT: "izquierda", pygame.K_a: "izquierda",
    pygame.K_RIGHT: "derecha", pygame.K_d: "derecha",
    pygame.K_SPACE: "accion",
}  # fmt: skip


class Enlace:
    """Servidor TCP de una sola conexión que se comporta como el puerto serial del Arduino."""

    def __init__(self, puerto: int) -> None:
        self.servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.servidor.bind(("127.0.0.1", puerto))
        self.servidor.listen(1)
        self.servidor.setblocking(False)
        self.cliente: socket.socket | None = None
        self.enviadas: list[str] = []

    @property
    def conectado(self) -> bool:
        return self.cliente is not None

    def revisar(self) -> bool:
        """Acepta una conexión nueva o detecta que se cerró. True si se acaba de conectar."""
        if self.cliente is None:
            try:
                self.cliente, _ = self.servidor.accept()
            except BlockingIOError:
                return False
            self.cliente.setblocking(False)
            return True
        try:
            if self.cliente.recv(1024) == b"":
                self._cerrar()
        except BlockingIOError:
            pass
        except OSError:
            self._cerrar()
        return False

    def enviar(self, linea: str) -> None:
        self.enviadas = (self.enviadas + [linea])[-8:]
        if self.cliente is None:
            return
        try:
            self.cliente.sendall((linea + "\r\n").encode("ascii"))  # igual que Serial.println
        except OSError:
            self._cerrar()

    def _cerrar(self) -> None:
        if self.cliente is not None:
            self.cliente.close()
        self.cliente = None


def crear_botones() -> dict[str, pygame.Rect]:
    t = 80
    cx, cy = 170, 250
    return {
        "arriba": pygame.Rect(cx - t // 2, cy - int(t * 1.5), t, t),
        "abajo": pygame.Rect(cx - t // 2, cy + t // 2, t, t),
        "izquierda": pygame.Rect(cx - int(t * 1.5), cy - t // 2, t, t),
        "derecha": pygame.Rect(cx + t // 2, cy - t // 2, t, t),
        "accion": pygame.Rect(440, cy - 55, 110, 110),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador del control físico")
    parser.add_argument("--puerto", type=int, default=7777)
    args = parser.parse_args()

    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Simulador del control - Control del Reactor")
    letra = pygame.font.Font(None, 26)
    reloj = pygame.time.Clock()
    botones = crear_botones()

    enlace = Enlace(args.puerto)
    teclas: set[str] = set()
    boton_mouse: str | None = None
    enviados: set[str] = set()  # controles que el juego cree presionados
    latidos = True
    ultimo_latido = 0.0

    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                return
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_h:
                latidos = not latidos
            elif evento.type in (pygame.KEYDOWN, pygame.KEYUP) and evento.key in TECLAS:
                accion = teclas.add if evento.type == pygame.KEYDOWN else teclas.discard
                accion(TECLAS[evento.key])
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                boton_mouse = next(
                    (c for c, r in botones.items() if r.collidepoint(evento.pos)), None
                )
            elif evento.type == pygame.MOUSEBUTTONUP:
                boton_mouse = None

        if enlace.revisar():  # se acaba de conectar el juego: como un Arduino recién encendido
            enviados = set()
            enlace.enviar(f"HELLO {ID_SIMULADOR} {VERSION}")

        presionados = teclas | ({boton_mouse} if boton_mouse else set())
        for control in sorted(presionados - enviados):
            enlace.enviar(f"BTN {NOMBRE_SERIAL[control]} PRESS")
        for control in sorted(enviados - presionados):
            enlace.enviar(f"BTN {NOMBRE_SERIAL[control]} RELEASE")
        enviados = presionados

        ahora = time.monotonic()
        if latidos and ahora - ultimo_latido >= LATIDO_S:
            ultimo_latido = ahora
            if enlace.conectado:
                enlace.enviar("HB")

        pantalla.fill((14, 18, 34))
        for control, rect in botones.items():
            color = (90, 200, 255) if control in presionados else (70, 76, 92)
            if control == "accion":
                pygame.draw.ellipse(pantalla, color, rect)
            else:
                pygame.draw.rect(pantalla, color, rect, border_radius=12)
        estado = "conectado al juego" if enlace.conectado else "esperando al juego"
        lineas = [
            f"socket://localhost:{args.puerto}  -  {estado}",
            f"Latidos: {'activos' if latidos else 'PAUSADOS (H para reanudar)'}",
        ]
        for i, texto in enumerate(lineas):
            pantalla.blit(letra.render(texto, True, (210, 210, 210)), (20, 16 + i * 24))
        for i, texto in enumerate(enlace.enviadas):
            pantalla.blit(letra.render(texto, True, (120, 150, 190)), (590, 90 + i * 22))
        pygame.display.flip()
        reloj.tick(60)


if __name__ == "__main__":
    main()
