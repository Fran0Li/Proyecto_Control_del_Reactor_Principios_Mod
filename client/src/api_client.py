"""Llamadas del cliente al backend (REST).

Todas las funciones son `async`: se usan con `await` desde una tarea (ver las pantallas), así la
ventana no se congela mientras responde el servidor y el mismo código corre en el navegador.
"""
from typing import Any

from src.config import SERVER_URL
from src.red import ErrorDeRed, Respuesta, solicitar


class ApiError(Exception):
    """El servidor respondió con un error o no se pudo contactar."""

    def __init__(self, mensaje: str, estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.estado = estado  # código HTTP, o None si no hubo respuesta


def _mensaje_de_error(respuesta: Respuesta) -> str:
    datos = respuesta.datos
    detalle = datos.get("detail") if isinstance(datos, dict) else None
    if isinstance(detalle, str):
        return detalle
    # los 422 de FastAPI vienen como lista
    if isinstance(detalle, list) and detalle and isinstance(detalle[0], dict):
        mensaje = str(detalle[0].get("msg", ""))
        return mensaje.removeprefix("Value error, ") or f"Error {respuesta.estado}"
    return f"Error {respuesta.estado}"


async def _enviar(
    metodo: str, ruta: str, cuerpo: dict | None = None, token: str | None = None
) -> Any:
    extra = {"headers": {"Authorization": f"Bearer {token}"}} if token else {}
    try:
        respuesta = await solicitar(metodo, f"{SERVER_URL}{ruta}", cuerpo, **extra)
    except ErrorDeRed as error:
        raise ApiError("Sin conexión con el servidor") from error
    if not respuesta.ok:
        raise ApiError(_mensaje_de_error(respuesta), respuesta.estado)
    return respuesta.datos


async def registrar_usuario(nombre_usuario: str, correo: str, contrasena: str) -> dict:
    return await _enviar(
        "POST",
        "/auth/registro",
        {"nombre_usuario": nombre_usuario, "correo": correo, "contrasena": contrasena},
    )


async def iniciar_sesion(usuario: str, contrasena: str) -> dict:
    """Devuelve {"access_token": ..., "usuario": {...}}."""
    return await _enviar("POST", "/auth/login", {"usuario": usuario, "contrasena": contrasena})


async def reenviar_verificacion(correo: str) -> dict:
    return await _enviar("POST", "/auth/reenviar-verificacion", {"correo": correo})


async def solicitar_recuperacion(correo: str) -> dict:
    return await _enviar("POST", "/auth/recuperar", {"correo": correo})


async def restablecer_contrasena(correo: str, codigo: str, contrasena: str) -> dict:
    return await _enviar(
        "POST",
        "/auth/restablecer",
        {"correo": correo, "codigo": codigo, "contrasena": contrasena},
    )


async def crear_partida(creador_id: int, escenario: str | None = None) -> dict:
    return await _enviar("POST", "/partidas", {"creador_id": creador_id, "escenario": escenario})

async def listar_partidas_disponibles() -> list[dict]:
    datos = await _enviar("GET", "/partidas")
    return datos if isinstance(datos, list) else []


async def unirse_a_partida(partida_id: int, jugador_id: int) -> dict:
    return await _enviar("POST", f"/partidas/{partida_id}/unirse", {"jugador_id": jugador_id})

async def estado_servidor() -> str:
    """Texto para mostrar en pantalla según responda /health."""
    try:
        respuesta = await solicitar("GET", f"{SERVER_URL}/health", timeout=2)
    except ErrorDeRed:
        return "Servidor: sin conexión"
    return "Servidor: conectado" if respuesta.ok else "Servidor: error"
