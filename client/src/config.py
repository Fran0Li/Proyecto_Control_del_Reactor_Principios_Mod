"""Configuración del cliente."""

import os
import sys

PUERTO_BACKEND = 8000


def _servidor_por_defecto() -> str:
    """En el navegador, el backend está en la misma máquina desde la que se cargó la página."""
    if sys.platform == "emscripten":
        import platform

        ubicacion = platform.window.location
        return f"{ubicacion.protocol}//{ubicacion.hostname}:{PUERTO_BACKEND}"
    return f"http://localhost:{PUERTO_BACKEND}"


SERVER_URL = os.getenv("SERVER_URL") or _servidor_por_defecto()
WINDOW_SIZE = (960, 640)
FPS = 60
