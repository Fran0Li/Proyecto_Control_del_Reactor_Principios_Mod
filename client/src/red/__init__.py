"""Comunicación del cliente con el backend, compatible con escritorio y navegador (ADR 0002)."""

from .http import EN_NAVEGADOR, ErrorDeRed, Respuesta, solicitar

__all__ = ["EN_NAVEGADOR", "ErrorDeRed", "Respuesta", "solicitar"]
