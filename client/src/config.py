"""Configuración del cliente."""

import os

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
WINDOW_SIZE = (960, 640)
FPS = 60
