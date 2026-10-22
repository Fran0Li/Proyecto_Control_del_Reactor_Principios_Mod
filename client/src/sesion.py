"""Sesión del jugador en el cliente (US-03). Vive en memoria mientras el juego está abierto."""

from dataclasses import dataclass

from src.config import JUGADOR_ID


@dataclass(frozen=True)
class Sesion:
    token: str
    usuario_id: int
    nombre_usuario: str


_actual: Sesion | None = None


def iniciar(token: str, usuario: dict) -> Sesion:
    global _actual
    _actual = Sesion(token, usuario["id"], usuario["nombre_usuario"])
    return _actual


def cerrar() -> None:
    global _actual
    _actual = None


def actual() -> Sesion | None:
    return _actual


def token() -> str:
    """Token de la sesión, o vacío si no hay (el servidor lo rechaza)."""
    return _actual.token if _actual else ""


def jugador_id() -> int:
    # sin sesión (por ejemplo en las pruebas) se usa el JUGADOR_ID del entorno
    return _actual.usuario_id if _actual else JUGADOR_ID
