"""Configuración del cliente."""

import os
import sys

PUERTO_BACKEND = 8000


def url_backend_web(protocolo: str, host: str, hostname: str) -> str:
    """URL del backend vista desde la página web del cliente.

    - Con https (nube): Caddy sirve la página y manda `/api/*` al backend, así que se usa el mismo
      origen. El puerto 8000 no está abierto en la nube.
    - Con http (servidor de pruebas de pygbag en la red local): backend en la misma IP, puerto 8000.
    """
    if protocolo == "https:":
        return f"https://{host}/api"
    return f"{protocolo}//{hostname}:{PUERTO_BACKEND}"


def _servidor_por_defecto() -> str:
    """En el navegador, el backend está en la misma máquina desde la que se cargó la página."""
    if sys.platform == "emscripten":
        import platform

        ubicacion = platform.window.location
        return url_backend_web(
            str(ubicacion.protocol), str(ubicacion.host), str(ubicacion.hostname)
        )
    return f"http://localhost:{PUERTO_BACKEND}"


SERVER_URL = os.getenv("SERVER_URL") or _servidor_por_defecto()
WINDOW_SIZE = (960, 640)
FPS = 60
# Control físico en escritorio: puerto del Arduino (COM3, /dev/ttyUSB0) o del simulador
# (socket://localhost:7777). Sin definir, se juega solo con el teclado.
CONTROL_PUERTO = os.getenv("CONTROL_PUERTO") or None
# Jugador a usar cuando no hay sesión iniciada (pruebas). Con login se usa el de la sesión.
JUGADOR_ID = int(os.getenv("JUGADOR_ID", "1"))