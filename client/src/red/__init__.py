"""Comunicación del cliente con el backend, compatible con escritorio y navegador (ADR 0002)."""

from .http import EN_NAVEGADOR, ErrorDeRed, Respuesta, solicitar
from .websocket import Conexion, crear_conexion

__all__ = [
    "EN_NAVEGADOR",
    "Conexion",
    "ErrorDeRed",
    "Respuesta",
    "crear_conexion",
    "solicitar",
]